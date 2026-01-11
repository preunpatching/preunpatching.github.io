from tkinter import filedialog
from time import time, sleep
import sys
from random import randrange
import argparse

# --- ROM DATA ---
# Wozmon ($FF00 - $FFFF)
WOZMON_DATA = b"\xd8X\xa0\x7f\x8c\x12\xd0\xa9\xa7\x8d\x11\xd0\x8d\x13\xd0\xc9\xdf\xf0\x13\xc9\x9b\xf0\x03\xc8\x10\x0f\xa9\xdc \xef\xff\xa9\x8d \xef\xff\xa0\x01\x880\xf6\xad\x11\xd0\x10\xfb\xad\x10\xd0\x99\x00\x02 \xef\xff\xc9\x8d\xd0\xd4\xa0\xff\xa9\x00\xaa\n\x85+\xc8\xb9\x00\x02\xc9\x8d\xf0\xd4\xc9\xae\x90\xf4\xf0\xf0\xc9\xba\xf0\xeb\xc9\xd2\xf0;\x86(\x86)\x84*\xb9\x00\x02I\xb0\xc9\n\x90\x06i\x88\xc9\xfa\x90\x11\n\n\n\n\xa2\x04\n&(&)\xca\xd0\xf8\xc8\xd0\xe0\xc4*\xf0\x97$+P\x10\xa5(\x81&\xe6&\xd0\xb5\xe6'LD\xffl$\x000+\xa2\x02\xb5'\x95%\x95#\xca\xd0\xf7\xd0\x14\xa9\x8d \xef\xff\xa5% \xdc\xff\xa5$ \xdc\xff\xa9\xba \xef\xff\xa9\xa0 \xef\xff\xa1$ \xdc\xff\x86+\xa5$\xc5(\xa5%\xe5)\xb0\xc1\xe6$\xd0\x02\xe6%\xa5$)\x07\x10\xc8HJJJJ \xe5\xffh)\x0f\t\xb0\xc9\xba\x90\x02i\x06,\x12\xd00\xfb\x8d\x12\xd0`\x00\x00\x00\x0f\x00\xff\x00\x00"

# Modified Apple Cassette Interface ($C100 - $C17B)
# Reads or writes a cassette port once, then returns.
ACI_DATA = b"\xa9\xaa \xef\xff\xa9\x8d \xef\xff\xa0\xff\xc8\xad\x11\xd0\x10\xfb\xad\x10\xd0\x99\x00\x02 \xef\xff\xc9\x9b\xf0\xe1\xc9\x8d\xd0\xe9\xa2\xff\xa9\x00\x85$\x85%\x85&\x85'\xe8\xbd\x00\x02\xc9\xd2\xf09\xc9\xd7\xf0;\xc9\xae\xf0'\xc9\x8d\xf0 \xc9\xa0\xf0\xe8I\xb0\xc9\n\x90\x06i\x88\xc9\xfa\x90\xad\n\n\n\n\xa0\x04\n&$&%\x88\xd0\xf8\xf0\xccL\x1a\xff\xa5$\x85&\xa5%\x85'\xb0\xbf\xad\x81\xc0L\x1a\xff\x8d(\xc0L\x1a\xff"

# --- 6502 CPU CORE (MPU derived from Py65 emulator) ---

class MPU:
    # vectors
    RESET = 0xfffc
    NMI = 0xfffa
    IRQ = 0xfffe

    # processor flags
    NEGATIVE = 128
    OVERFLOW = 64
    UNUSED = 32
    BREAK = 16
    DECIMAL = 8
    INTERRUPT = 4
    ZERO = 2
    CARRY = 1

    BYTE_WIDTH = 8
    BYTE_FORMAT = "%02x"
    ADDR_WIDTH = 16
    ADDR_FORMAT = "%04x"

    def __init__(self, memory=None, pc=None):
        # config
        self.name = '6502'
        self.byteMask = ((1 << self.BYTE_WIDTH) - 1)
        self.addrMask = ((1 << self.ADDR_WIDTH) - 1)
        self.addrHighMask = (self.byteMask << self.BYTE_WIDTH)
        self.spBase = 1 << self.BYTE_WIDTH

        # vm status
        self.excycles = 0
        self.addcycles = False
        self.processorCycles = 0

        if memory is None:
            memory = bytearray(65536)
        self.memory = memory
        self.start_pc = pc # if None, reset vector is used

        # init
        self.reset()

    def reprformat(self):
        return ("%s PC  AC XR YR SP NV-BDIZC\n"
                "%s: %04x %02x %02x %02x %02x %s")

    def __repr__(self):
        flags = '{0:b}'.format(self.p).rjust(self.BYTE_WIDTH, '0')
        indent = ' ' * (len(self.name) + 2)

        return self.reprformat() % (indent, self.name, self.pc, self.a,
                                    self.x, self.y, self.sp, flags)

    def step(self):
        instructCode = self.memory[self.pc]
        self.pc = (self.pc + 1) & self.addrMask
        self.excycles = 0
        self.addcycles = self.extracycles[instructCode]
        self.instruct[instructCode](self)
        self.pc &= self.addrMask
        self.processorCycles += self.cycletime[instructCode] + self.excycles
        return self

    def reset(self):
        self.pc = self.start_pc
        if self.pc is None:
            self.pc = self.WordAt(self.RESET)
        self.sp = self.byteMask
        self.a = 0
        self.x = 0
        self.y = 0
        self.p = self.BREAK | self.UNUSED
        self.processorCycles = 0

    def irq(self):
        # triggers a normal IRQ
        # this is very similar to the BRK instruction
        if self.p & self.INTERRUPT:
            return
        self.stPushWord(self.pc)
        self.p &= ~self.BREAK
        self.stPush(self.p | self.UNUSED)
        self.p |= self.INTERRUPT
        self.pc = self.WordAt(self.IRQ)
        self.processorCycles += 7

    def nmi(self):
        # triggers a NMI IRQ in the processor
        # this is very similar to the BRK instruction
        self.stPushWord(self.pc)
        self.p &= ~self.BREAK
        self.stPush(self.p | self.UNUSED)
        self.p |= self.INTERRUPT
        self.pc = self.WordAt(self.NMI)
        self.processorCycles += 7

    # Helpers for addressing modes

    def ByteAt(self, addr):
        return self.memory[addr]

    def WordAt(self, addr):
        return self.ByteAt(addr) + (self.ByteAt(addr + 1) << self.BYTE_WIDTH)

    def WrapAt(self, addr):
        wrap = lambda x: (x & self.addrHighMask) + ((x + 1) & self.byteMask)
        return self.ByteAt(addr) + (self.ByteAt(wrap(addr)) << self.BYTE_WIDTH)

    def ProgramCounter(self):
        return self.pc

    # Addressing modes

    def ImmediateByte(self):
        return self.ByteAt(self.pc)

    def ZeroPageAddr(self):
        return self.ByteAt(self.pc)

    def ZeroPageXAddr(self):
        return self.byteMask & (self.x + self.ByteAt(self.pc))

    def ZeroPageYAddr(self):
        return self.byteMask & (self.y + self.ByteAt(self.pc))

    def IndirectXAddr(self):
        return self.WrapAt(self.byteMask & (self.ByteAt(self.pc) + self.x))

    def IndirectYAddr(self):
        if self.addcycles:
            a1 = self.WrapAt(self.ByteAt(self.pc))
            a2 = (a1 + self.y) & self.addrMask
            if (a1 & self.addrHighMask) != (a2 & self.addrHighMask):
                self.excycles += 1
            return a2
        else:
            return (self.WrapAt(self.ByteAt(self.pc)) + self.y) & self.addrMask

    def AbsoluteAddr(self):
        return self.WordAt(self.pc)

    def AbsoluteXAddr(self):
        if self.addcycles:
            a1 = self.WordAt(self.pc)
            a2 = (a1 + self.x) & self.addrMask
            if (a1 & self.addrHighMask) != (a2 & self.addrHighMask):
                self.excycles += 1
            return a2
        else:
            return (self.WordAt(self.pc) + self.x) & self.addrMask

    def AbsoluteYAddr(self):
        if self.addcycles:
            a1 = self.WordAt(self.pc)
            a2 = (a1 + self.y) & self.addrMask
            if (a1 & self.addrHighMask) != (a2 & self.addrHighMask):
                self.excycles += 1
            return a2
        else:
            return (self.WordAt(self.pc) + self.y) & self.addrMask

    def BranchRelAddr(self):
        self.excycles += 1
        addr = self.ImmediateByte()
        self.pc += 1

        if addr & self.NEGATIVE:
            addr = self.pc - (addr ^ self.byteMask) - 1
        else:
            addr = self.pc + addr

        if (self.pc & self.addrHighMask) != (addr & self.addrHighMask):
            self.excycles += 1

        self.pc = addr & self.addrMask

    # stack

    def stPush(self, z):
        self.memory[self.sp + self.spBase] = z & self.byteMask
        self.sp -= 1
        self.sp &= self.byteMask

    def stPop(self):
        self.sp += 1
        self.sp &= self.byteMask
        return self.ByteAt(self.sp + self.spBase)

    def stPushWord(self, z):
        self.stPush((z >> self.BYTE_WIDTH) & self.byteMask)
        self.stPush(z & self.byteMask)

    def stPopWord(self):
        z = self.stPop()
        z += self.stPop() << self.BYTE_WIDTH
        return z

    def FlagsNZ(self, value):
        self.p &= ~(self.ZERO | self.NEGATIVE)
        if value == 0:
            self.p |= self.ZERO
        else:
            self.p |= value & self.NEGATIVE

    # operations

    def opORA(self, x):
        self.a |= self.ByteAt(x())
        self.FlagsNZ(self.a)

    def opASL(self, x):
        if x is None:
            tbyte = self.a
        else:
            addr = x()
            tbyte = self.ByteAt(addr)

        self.p &= ~(self.CARRY | self.NEGATIVE | self.ZERO)

        if tbyte & self.NEGATIVE:
            self.p |= self.CARRY
        tbyte = (tbyte << 1) & self.byteMask

        if tbyte:
            self.p |= tbyte & self.NEGATIVE
        else:
            self.p |= self.ZERO

        if x is None:
            self.a = tbyte
        else:
            self.memory[addr] = tbyte

    def opLSR(self, x):
        if x is None:
            tbyte = self.a
        else:
            addr = x()
            tbyte = self.ByteAt(addr)

        self.p &= ~(self.CARRY | self.NEGATIVE | self.ZERO)
        self.p |= tbyte & 1

        tbyte = tbyte >> 1
        if tbyte:
            pass
        else:
            self.p |= self.ZERO

        if x is None:
            self.a = tbyte
        else:
            self.memory[addr] = tbyte

    def opBCL(self, x):
        if self.p & x:
            self.pc += 1
        else:
            self.BranchRelAddr()

    def opBST(self, x):
        if self.p & x:
            self.BranchRelAddr()
        else:
            self.pc += 1

    def opCLR(self, x):
        self.p &= ~x

    def opSET(self, x):
        self.p |= x

    def opAND(self, x):
        self.a &= self.ByteAt(x())
        self.FlagsNZ(self.a)

    def opBIT(self, x):
        tbyte = self.ByteAt(x())
        self.p &= ~(self.ZERO | self.NEGATIVE | self.OVERFLOW)
        if (self.a & tbyte) == 0:
            self.p |= self.ZERO
        self.p |= tbyte & (self.NEGATIVE | self.OVERFLOW)

    def opROL(self, x):
        if x is None:
            tbyte = self.a
        else:
            addr = x()
            tbyte = self.ByteAt(addr)

        if self.p & self.CARRY:
            if tbyte & self.NEGATIVE:
                pass
            else:
                self.p &= ~self.CARRY
            tbyte = (tbyte << 1) | 1
        else:
            if tbyte & self.NEGATIVE:
                self.p |= self.CARRY
            tbyte = tbyte << 1
        tbyte &= self.byteMask
        self.FlagsNZ(tbyte)

        if x is None:
            self.a = tbyte
        else:
            self.memory[addr] = tbyte

    def opEOR(self, x):
        self.a ^= self.ByteAt(x())
        self.FlagsNZ(self.a)

    def opADC(self, x):
        data = self.ByteAt(x())

        if self.p & self.DECIMAL:
            halfcarry = 0
            decimalcarry = 0
            adjust0 = 0
            adjust1 = 0
            nibble0 = (data & 0xf) + (self.a & 0xf) + (self.p & self.CARRY)
            if nibble0 > 9:
                adjust0 = 6
                halfcarry = 1
            nibble1 = ((data >> 4) & 0xf) + ((self.a >> 4) & 0xf) + halfcarry
            if nibble1 > 9:
                adjust1 = 6
                decimalcarry = 1

            # the ALU outputs are not decimally adjusted
            nibble0 = nibble0 & 0xf
            nibble1 = nibble1 & 0xf
            aluresult = (nibble1 << 4) + nibble0

            # the final A contents will be decimally adjusted
            nibble0 = (nibble0 + adjust0) & 0xf
            nibble1 = (nibble1 + adjust1) & 0xf
            self.p &= ~(self.CARRY | self.OVERFLOW | self.NEGATIVE | self.ZERO)
            if aluresult == 0:
                self.p |= self.ZERO
            else:
                self.p |= aluresult & self.NEGATIVE
            if decimalcarry == 1:
                self.p |= self.CARRY
            if (~(self.a ^ data) & (self.a ^ aluresult)) & self.NEGATIVE:
                self.p |= self.OVERFLOW
            self.a = (nibble1 << 4) + nibble0
        else:
            if self.p & self.CARRY:
                tmp = 1
            else:
                tmp = 0
            result = data + self.a + tmp
            self.p &= ~(self.CARRY | self.OVERFLOW | self.NEGATIVE | self.ZERO)
            if (~(self.a ^ data) & (self.a ^ result)) & self.NEGATIVE:
                self.p |= self.OVERFLOW
            data = result
            if data > self.byteMask:
                self.p |= self.CARRY
                data &= self.byteMask
            if data == 0:
                self.p |= self.ZERO
            else:
                self.p |= data & self.NEGATIVE
            self.a = data

    def opROR(self, x):
        if x is None:
            tbyte = self.a
        else:
            addr = x()
            tbyte = self.ByteAt(addr)

        if self.p & self.CARRY:
            if tbyte & 1:
                pass
            else:
                self.p &= ~self.CARRY
            tbyte = (tbyte >> 1) | self.NEGATIVE
        else:
            if tbyte & 1:
                self.p |= self.CARRY
            tbyte = tbyte >> 1
        self.FlagsNZ(tbyte)

        if x is None:
            self.a = tbyte
        else:
            self.memory[addr] = tbyte

    def opSTA(self, x):
        self.memory[x()] = self.a

    def opSTY(self, x):
        self.memory[x()] = self.y

    def opSTX(self, y):
        self.memory[y()] = self.x

    def opCMPR(self, get_address, register_value):
        tbyte = self.ByteAt(get_address())
        self.p &= ~(self.CARRY | self.ZERO | self.NEGATIVE)
        if register_value == tbyte:
            self.p |= self.CARRY | self.ZERO
        elif register_value > tbyte:
            self.p |= self.CARRY
        self.p |= (register_value - tbyte) & self.NEGATIVE

    def opSBC(self, x):
        data = self.ByteAt(x())

        if self.p & self.DECIMAL:
            halfcarry = 1
            decimalcarry = 0
            adjust0 = 0
            adjust1 = 0

            nibble0 = (self.a & 0xf) + (~data & 0xf) + (self.p & self.CARRY)
            if nibble0 <= 0xf:
                halfcarry = 0
                adjust0 = 10
            nibble1 = ((self.a >> 4) & 0xf) + ((~data >> 4) & 0xf) + halfcarry
            if nibble1 <= 0xf:
                adjust1 = 10 << 4

            # the ALU outputs are not decimally adjusted
            aluresult = self.a + (~data & self.byteMask) + \
                (self.p & self.CARRY)

            if aluresult > self.byteMask:
                decimalcarry = 1
            aluresult &= self.byteMask

            # but the final result will be adjusted
            nibble0 = (aluresult + adjust0) & 0xf
            nibble1 = ((aluresult + adjust1) >> 4) & 0xf

            self.p &= ~(self.CARRY | self.ZERO | self.NEGATIVE | self.OVERFLOW)
            if aluresult == 0:
                self.p |= self.ZERO
            else:
                self.p |= aluresult & self.NEGATIVE
            if decimalcarry == 1:
                self.p |= self.CARRY
            if ((self.a ^ data) & (self.a ^ aluresult)) & self.NEGATIVE:
                self.p |= self.OVERFLOW
            self.a = (nibble1 << 4) + nibble0
        else:
            result = self.a + (~data & self.byteMask) + (self.p & self.CARRY)
            self.p &= ~(self.CARRY | self.ZERO | self.OVERFLOW | self.NEGATIVE)
            if ((self.a ^ data) & (self.a ^ result)) & self.NEGATIVE:
                self.p |= self.OVERFLOW
            data = result & self.byteMask
            if data == 0:
                self.p |= self.ZERO
            if result > self.byteMask:
                self.p |= self.CARRY
            self.p |= data & self.NEGATIVE
            self.a = data

    def opDECR(self, x):
        if x is None:
            tbyte = self.a
        else:
            addr = x()
            tbyte = self.ByteAt(addr)

        self.p &= ~(self.ZERO | self.NEGATIVE)
        tbyte = (tbyte - 1) & self.byteMask
        if tbyte:
            self.p |= tbyte & self.NEGATIVE
        else:
            self.p |= self.ZERO

        if x is None:
            self.a = tbyte
        else:
            self.memory[addr] = tbyte

    def opINCR(self, x):
        if x is None:
            tbyte = self.a
        else:
            addr = x()
            tbyte = self.ByteAt(addr)

        self.p &= ~(self.ZERO | self.NEGATIVE)
        tbyte = (tbyte + 1) & self.byteMask
        if tbyte:
            self.p |= tbyte & self.NEGATIVE
        else:
            self.p |= self.ZERO

        if x is None:
            self.a = tbyte
        else:
            self.memory[addr] = tbyte

    def opLDA(self, x):
        self.a = self.ByteAt(x())
        self.FlagsNZ(self.a)

    def opLDY(self, x):
        self.y = self.ByteAt(x())
        self.FlagsNZ(self.y)

    def opLDX(self, y):
        self.x = self.ByteAt(y())
        self.FlagsNZ(self.x)

    # instructions

    def make_instruction_decorator(instruct, disasm, allcycles, allextras):
        def instruction(name, mode, cycles, extracycles=0):
            def decorate(f):
                opcode = int(f.__name__.split('_')[-1], 16)
                instruct[opcode] = f
                disasm[opcode] = (name, mode)
                allcycles[opcode] = cycles
                allextras[opcode] = extracycles
                return f  # Return the original function
            return decorate
        return instruction

    def inst_not_implemented(self):
        self.pc += 1

    instruct = [inst_not_implemented] * 256
    cycletime = [0] * 256
    extracycles = [0] * 256
    disassemble = [('???', 'imp')] * 256

    instruction = make_instruction_decorator(instruct, disassemble,
                                             cycletime, extracycles)

    @instruction(name="BRK", mode="imp", cycles=7)
    def inst_0x00(self):
        # pc has already been increased one
        pc = (self.pc + 1) & self.addrMask
        self.stPushWord(pc)

        self.p |= self.BREAK
        self.stPush(self.p | self.BREAK | self.UNUSED)

        self.p |= self.INTERRUPT
        self.pc = self.WordAt(self.IRQ)

    @instruction(name="ORA", mode="inx", cycles=6)
    def inst_0x01(self):
        self.opORA(self.IndirectXAddr)
        self.pc += 1

    @instruction(name="ORA", mode="zpg", cycles=3)
    def inst_0x05(self):
        self.opORA(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="ASL", mode="zpg", cycles=5)
    def inst_0x06(self):
        self.opASL(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="PHP", mode="imp", cycles=3)
    def inst_0x08(self):
        self.stPush(self.p | self.BREAK | self.UNUSED)

    @instruction(name="ORA", mode="imm", cycles=2)
    def inst_0x09(self):
        self.opORA(self.ProgramCounter)
        self.pc += 1

    @instruction(name="ASL", mode="acc", cycles=2)
    def inst_0x0a(self):
        self.opASL(None)

    @instruction(name="ORA", mode="abs", cycles=4)
    def inst_0x0d(self):
        self.opORA(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="ASL", mode="abs", cycles=6)
    def inst_0x0e(self):
        self.opASL(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="BPL", mode="rel", cycles=2, extracycles=2)
    def inst_0x10(self):
        self.opBCL(self.NEGATIVE)

    @instruction(name="ORA", mode="iny", cycles=5, extracycles=1)
    def inst_0x11(self):
        self.opORA(self.IndirectYAddr)
        self.pc += 1

    @instruction(name="ORA", mode="zpx", cycles=4)
    def inst_0x15(self):
        self.opORA(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="ASL", mode="zpx", cycles=6)
    def inst_0x16(self):
        self.opASL(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="CLC", mode="imp", cycles=2)
    def inst_0x18(self):
        self.opCLR(self.CARRY)

    @instruction(name="ORA", mode="aby", cycles=4, extracycles=1)
    def inst_0x19(self):
        self.opORA(self.AbsoluteYAddr)
        self.pc += 2

    @instruction(name="ORA", mode="abx", cycles=4, extracycles=1)
    def inst_0x1d(self):
        self.opORA(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="ASL", mode="abx", cycles=7)
    def inst_0x1e(self):
        self.opASL(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="JSR", mode="abs", cycles=6)
    def inst_0x20(self):
        self.stPushWord((self.pc + 1) & self.addrMask)
        self.pc = self.WordAt(self.pc)

    @instruction(name="AND", mode="inx", cycles=6)
    def inst_0x21(self):
        self.opAND(self.IndirectXAddr)
        self.pc += 1

    @instruction(name="BIT", mode="zpg", cycles=3)
    def inst_0x24(self):
        self.opBIT(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="AND", mode="zpg", cycles=3)
    def inst_0x25(self):
        self.opAND(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="ROL", mode="zpg", cycles=5)
    def inst_0x26(self):
        self.opROL(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="PLP", mode="imp", cycles=4)
    def inst_0x28(self):
        self.p = (self.stPop() | self.BREAK | self.UNUSED)

    @instruction(name="AND", mode="imm", cycles=2)
    def inst_0x29(self):
        self.opAND(self.ProgramCounter)
        self.pc += 1

    @instruction(name="ROL", mode="acc", cycles=2)
    def inst_0x2a(self):
        self.opROL(None)

    @instruction(name="BIT", mode="abs", cycles=4)
    def inst_0x2c(self):
        self.opBIT(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="AND", mode="abs", cycles=4)
    def inst_0x2d(self):
        self.opAND(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="ROL", mode="abs", cycles=6)
    def inst_0x2e(self):
        self.opROL(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="BMI", mode="rel", cycles=2, extracycles=2)
    def inst_0x30(self):
        self.opBST(self.NEGATIVE)

    @instruction(name="AND", mode="iny", cycles=5, extracycles=1)
    def inst_0x31(self):
        self.opAND(self.IndirectYAddr)
        self.pc += 1

    @instruction(name="AND", mode="zpx", cycles=4)
    def inst_0x35(self):
        self.opAND(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="ROL", mode="zpx", cycles=6)
    def inst_0x36(self):
        self.opROL(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="SEC", mode="imp", cycles=2)
    def inst_0x38(self):
        self.opSET(self.CARRY)

    @instruction(name="AND", mode="aby", cycles=4, extracycles=1)
    def inst_0x39(self):
        self.opAND(self.AbsoluteYAddr)
        self.pc += 2

    @instruction(name="AND", mode="abx", cycles=4, extracycles=1)
    def inst_0x3d(self):
        self.opAND(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="ROL", mode="abx", cycles=7)
    def inst_0x3e(self):
        self.opROL(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="RTI", mode="imp", cycles=6)
    def inst_0x40(self):
        self.p = (self.stPop() | self.BREAK | self.UNUSED)
        self.pc = self.stPopWord()

    @instruction(name="EOR", mode="inx", cycles=6)
    def inst_0x41(self):
        self.opEOR(self.IndirectXAddr)
        self.pc += 1

    @instruction(name="EOR", mode="zpg", cycles=3)
    def inst_0x45(self):
        self.opEOR(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="LSR", mode="zpg", cycles=5)
    def inst_0x46(self):
        self.opLSR(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="PHA", mode="imp", cycles=3)
    def inst_0x48(self):
        self.stPush(self.a)

    @instruction(name="EOR", mode="imm", cycles=2)
    def inst_0x49(self):
        self.opEOR(self.ProgramCounter)
        self.pc += 1

    @instruction(name="LSR", mode="acc", cycles=2)
    def inst_0x4a(self):
        self.opLSR(None)

    @instruction(name="JMP", mode="abs", cycles=3)
    def inst_0x4c(self):
        self.pc = self.WordAt(self.pc)

    @instruction(name="EOR", mode="abs", cycles=4)
    def inst_0x4d(self):
        self.opEOR(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="LSR", mode="abs", cycles=6)
    def inst_0x4e(self):
        self.opLSR(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="BVC", mode="rel", cycles=2, extracycles=2)
    def inst_0x50(self):
        self.opBCL(self.OVERFLOW)

    @instruction(name="EOR", mode="iny", cycles=5, extracycles=1)
    def inst_0x51(self):
        self.opEOR(self.IndirectYAddr)
        self.pc += 1

    @instruction(name="EOR", mode="zpx", cycles=4)
    def inst_0x55(self):
        self.opEOR(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="LSR", mode="zpx", cycles=6)
    def inst_0x56(self):
        self.opLSR(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="CLI", mode="imp", cycles=2)
    def inst_0x58(self):
        self.opCLR(self.INTERRUPT)

    @instruction(name="EOR", mode="aby", cycles=4, extracycles=1)
    def inst_0x59(self):
        self.opEOR(self.AbsoluteYAddr)
        self.pc += 2

    @instruction(name="EOR", mode="abx", cycles=4, extracycles=1)
    def inst_0x5d(self):
        self.opEOR(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="LSR", mode="abx", cycles=7)
    def inst_0x5e(self):
        self.opLSR(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="RTS", mode="imp", cycles=6)
    def inst_0x60(self):
        self.pc = self.stPopWord()
        self.pc += 1

    @instruction(name="ADC", mode="inx", cycles=6)
    def inst_0x61(self):
        self.opADC(self.IndirectXAddr)
        self.pc += 1

    @instruction(name="ADC", mode="zpg", cycles=3)
    def inst_0x65(self):
        self.opADC(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="ROR", mode="zpg", cycles=5)
    def inst_0x66(self):
        self.opROR(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="PLA", mode="imp", cycles=4)
    def inst_0x68(self):
        self.a = self.stPop()
        self.FlagsNZ(self.a)

    @instruction(name="ADC", mode="imm", cycles=2)
    def inst_0x69(self):
        self.opADC(self.ProgramCounter)
        self.pc += 1

    @instruction(name="ROR", mode="acc", cycles=2)
    def inst_0x6a(self):
        self.opROR(None)

    @instruction(name="JMP", mode="ind", cycles=5)
    def inst_0x6c(self):
        ta = self.WordAt(self.pc)
        self.pc = self.WrapAt(ta)

    @instruction(name="ADC", mode="abs", cycles=4)
    def inst_0x6d(self):
        self.opADC(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="ROR", mode="abs", cycles=6)
    def inst_0x6e(self):
        self.opROR(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="BVS", mode="rel", cycles=2, extracycles=2)
    def inst_0x70(self):
        self.opBST(self.OVERFLOW)

    @instruction(name="ADC", mode="iny", cycles=5, extracycles=1)
    def inst_0x71(self):
        self.opADC(self.IndirectYAddr)
        self.pc += 1

    @instruction(name="ADC", mode="zpx", cycles=4)
    def inst_0x75(self):
        self.opADC(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="ROR", mode="zpx", cycles=6)
    def inst_0x76(self):
        self.opROR(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="SEI", mode="imp", cycles=2)
    def inst_0x78(self):
        self.opSET(self.INTERRUPT)

    @instruction(name="ADC", mode="aby", cycles=4, extracycles=1)
    def inst_0x79(self):
        self.opADC(self.AbsoluteYAddr)
        self.pc += 2

    @instruction(name="ADC", mode="abx", cycles=4, extracycles=1)
    def inst_0x7d(self):
        self.opADC(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="ROR", mode="abx", cycles=7)
    def inst_0x7e(self):
        self.opROR(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="STA", mode="inx", cycles=6)
    def inst_0x81(self):
        self.opSTA(self.IndirectXAddr)
        self.pc += 1

    @instruction(name="STY", mode="zpg", cycles=3)
    def inst_0x84(self):
        self.opSTY(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="STA", mode="zpg", cycles=3)
    def inst_0x85(self):
        self.opSTA(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="STX", mode="zpg", cycles=3)
    def inst_0x86(self):
        self.opSTX(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="DEY", mode="imp", cycles=2)
    def inst_0x88(self):
        self.y -= 1
        self.y &= self.byteMask
        self.FlagsNZ(self.y)

    @instruction(name="TXA", mode="imp", cycles=2)
    def inst_0x8a(self):
        self.a = self.x
        self.FlagsNZ(self.a)

    @instruction(name="STY", mode="abs", cycles=4)
    def inst_0x8c(self):
        self.opSTY(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="STA", mode="abs", cycles=4)
    def inst_0x8d(self):
        self.opSTA(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="STX", mode="abs", cycles=4)
    def inst_0x8e(self):
        self.opSTX(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="BCC", mode="rel", cycles=2, extracycles=2)
    def inst_0x90(self):
        self.opBCL(self.CARRY)

    @instruction(name="STA", mode="iny", cycles=6)
    def inst_0x91(self):
        self.opSTA(self.IndirectYAddr)
        self.pc += 1

    @instruction(name="STY", mode="zpx", cycles=4)
    def inst_0x94(self):
        self.opSTY(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="STA", mode="zpx", cycles=4)
    def inst_0x95(self):
        self.opSTA(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="STX", mode="zpy", cycles=4)
    def inst_0x96(self):
        self.opSTX(self.ZeroPageYAddr)
        self.pc += 1

    @instruction(name="TYA", mode="imp", cycles=2)
    def inst_0x98(self):
        self.a = self.y
        self.FlagsNZ(self.a)

    @instruction(name="STA", mode="aby", cycles=5)
    def inst_0x99(self):
        self.opSTA(self.AbsoluteYAddr)
        self.pc += 2

    @instruction(name="TXS", mode="imp", cycles=2)
    def inst_0x9a(self):
        self.sp = self.x

    @instruction(name="STA", mode="abx", cycles=5)
    def inst_0x9d(self):
        self.opSTA(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="LDY", mode="imm", cycles=2)
    def inst_0xa0(self):
        self.opLDY(self.ProgramCounter)
        self.pc += 1

    @instruction(name="LDA", mode="inx", cycles=6)
    def inst_0xa1(self):
        self.opLDA(self.IndirectXAddr)
        self.pc += 1

    @instruction(name="LDX", mode="imm", cycles=2)
    def inst_0xa2(self):
        self.opLDX(self.ProgramCounter)
        self.pc += 1

    @instruction(name="LDY", mode="zpg", cycles=3)
    def inst_0xa4(self):
        self.opLDY(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="LDA", mode="zpg", cycles=3)
    def inst_0xa5(self):
        self.opLDA(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="LDX", mode="zpg", cycles=3)
    def inst_0xa6(self):
        self.opLDX(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="TAY", mode="imp", cycles=2)
    def inst_0xa8(self):
        self.y = self.a
        self.FlagsNZ(self.y)

    @instruction(name="LDA", mode="imm", cycles=2)
    def inst_0xa9(self):
        self.opLDA(self.ProgramCounter)
        self.pc += 1

    @instruction(name="TAX", mode="imp", cycles=2)
    def inst_0xaa(self):
        self.x = self.a
        self.FlagsNZ(self.x)

    @instruction(name="LDY", mode="abs", cycles=4)
    def inst_0xac(self):
        self.opLDY(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="LDA", mode="abs", cycles=4)
    def inst_0xad(self):
        self.opLDA(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="LDX", mode="abs", cycles=4)
    def inst_0xae(self):
        self.opLDX(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="BCS", mode="rel", cycles=2, extracycles=2)
    def inst_0xb0(self):
        self.opBST(self.CARRY)

    @instruction(name="LDA", mode="iny", cycles=5, extracycles=1)
    def inst_0xb1(self):
        self.opLDA(self.IndirectYAddr)
        self.pc += 1

    @instruction(name="LDY", mode="zpx", cycles=4)
    def inst_0xb4(self):
        self.opLDY(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="LDA", mode="zpx", cycles=4)
    def inst_0xb5(self):
        self.opLDA(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="LDX", mode="zpy", cycles=4)
    def inst_0xb6(self):
        self.opLDX(self.ZeroPageYAddr)
        self.pc += 1

    @instruction(name="CLV", mode="imp", cycles=2)
    def inst_0xb8(self):
        self.opCLR(self.OVERFLOW)

    @instruction(name="LDA", mode="aby", cycles=4, extracycles=1)
    def inst_0xb9(self):
        self.opLDA(self.AbsoluteYAddr)
        self.pc += 2

    @instruction(name="TSX", mode="imp", cycles=2)
    def inst_0xba(self):
        self.x = self.sp
        self.FlagsNZ(self.x)

    @instruction(name="LDY", mode="abx", cycles=4, extracycles=1)
    def inst_0xbc(self):
        self.opLDY(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="LDA", mode="abx", cycles=4, extracycles=1)
    def inst_0xbd(self):
        self.opLDA(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="LDX", mode="aby", cycles=4, extracycles=1)
    def inst_0xbe(self):
        self.opLDX(self.AbsoluteYAddr)
        self.pc += 2

    @instruction(name="CPY", mode="imm", cycles=2)
    def inst_0xc0(self):
        self.opCMPR(self.ProgramCounter, self.y)
        self.pc += 1

    @instruction(name="CMP", mode="inx", cycles=6)
    def inst_0xc1(self):
        self.opCMPR(self.IndirectXAddr, self.a)
        self.pc += 1

    @instruction(name="CPY", mode="zpg", cycles=3)
    def inst_0xc4(self):
        self.opCMPR(self.ZeroPageAddr, self.y)
        self.pc += 1

    @instruction(name="CMP", mode="zpg", cycles=3)
    def inst_0xc5(self):
        self.opCMPR(self.ZeroPageAddr, self.a)
        self.pc += 1

    @instruction(name="DEC", mode="zpg", cycles=5)
    def inst_0xc6(self):
        self.opDECR(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="INY", mode="imp", cycles=2)
    def inst_0xc8(self):
        self.y += 1
        self.y &= self.byteMask
        self.FlagsNZ(self.y)

    @instruction(name="CMP", mode="imm", cycles=2)
    def inst_0xc9(self):
        self.opCMPR(self.ProgramCounter, self.a)
        self.pc += 1

    @instruction(name="DEX", mode="imp", cycles=2)
    def inst_0xca(self):
        self.x -= 1
        self.x &= self.byteMask
        self.FlagsNZ(self.x)

    @instruction(name="CPY", mode="abs", cycles=4)
    def inst_0xcc(self):
        self.opCMPR(self.AbsoluteAddr, self.y)
        self.pc += 2

    @instruction(name="CMP", mode="abs", cycles=4)
    def inst_0xcd(self):
        self.opCMPR(self.AbsoluteAddr, self.a)
        self.pc += 2

    @instruction(name="DEC", mode="abs", cycles=3)
    def inst_0xce(self):
        self.opDECR(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="BNE", mode="rel", cycles=2, extracycles=2)
    def inst_0xd0(self):
        self.opBCL(self.ZERO)

    @instruction(name="CMP", mode="iny", cycles=5, extracycles=1)
    def inst_0xd1(self):
        self.opCMPR(self.IndirectYAddr, self.a)
        self.pc += 1

    @instruction(name="CMP", mode="zpx", cycles=4)
    def inst_0xd5(self):
        self.opCMPR(self.ZeroPageXAddr, self.a)
        self.pc += 1

    @instruction(name="DEC", mode="zpx", cycles=6)
    def inst_0xd6(self):
        self.opDECR(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="CLD", mode="imp", cycles=2)
    def inst_0xd8(self):
        self.opCLR(self.DECIMAL)

    @instruction(name="CMP", mode="aby", cycles=4, extracycles=1)
    def inst_0xd9(self):
        self.opCMPR(self.AbsoluteYAddr, self.a)
        self.pc += 2

    @instruction(name="CMP", mode="abx", cycles=4, extracycles=1)
    def inst_0xdd(self):
        self.opCMPR(self.AbsoluteXAddr, self.a)
        self.pc += 2

    @instruction(name="DEC", mode="abx", cycles=7)
    def inst_0xde(self):
        self.opDECR(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="CPX", mode="imm", cycles=2)
    def inst_0xe0(self):
        self.opCMPR(self.ProgramCounter, self.x)
        self.pc += 1

    @instruction(name="SBC", mode="inx", cycles=6)
    def inst_0xe1(self):
        self.opSBC(self.IndirectXAddr)
        self.pc += 1

    @instruction(name="CPX", mode="zpg", cycles=3)
    def inst_0xe4(self):
        self.opCMPR(self.ZeroPageAddr, self.x)
        self.pc += 1

    @instruction(name="SBC", mode="zpg", cycles=3)
    def inst_0xe5(self):
        self.opSBC(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="INC", mode="zpg", cycles=5)
    def inst_0xe6(self):
        self.opINCR(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="INX", mode="imp", cycles=2)
    def inst_0xe8(self):
        self.x += 1
        self.x &= self.byteMask
        self.FlagsNZ(self.x)

    @instruction(name="SBC", mode="imm", cycles=2)
    def inst_0xe9(self):
        self.opSBC(self.ProgramCounter)
        self.pc += 1

    @instruction(name="NOP", mode="imp", cycles=2)
    def inst_0xea(self):
        pass

    @instruction(name="CPX", mode="abs", cycles=4)
    def inst_0xec(self):
        self.opCMPR(self.AbsoluteAddr, self.x)
        self.pc += 2

    @instruction(name="SBC", mode="abs", cycles=4)
    def inst_0xed(self):
        self.opSBC(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="INC", mode="abs", cycles=6)
    def inst_0xee(self):
        self.opINCR(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="BEQ", mode="rel", cycles=2, extracycles=2)
    def inst_0xf0(self):
        self.opBST(self.ZERO)

    @instruction(name="SBC", mode="iny", cycles=5, extracycles=1)
    def inst_0xf1(self):
        self.opSBC(self.IndirectYAddr)
        self.pc += 1

    @instruction(name="SBC", mode="zpx", cycles=4)
    def inst_0xf5(self):
        self.opSBC(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="INC", mode="zpx", cycles=6)
    def inst_0xf6(self):
        self.opINCR(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="SED", mode="imp", cycles=2)
    def inst_0xf8(self):
        self.opSET(self.DECIMAL)

    @instruction(name="SBC", mode="aby", cycles=4, extracycles=1)
    def inst_0xf9(self):
        self.opSBC(self.AbsoluteYAddr)
        self.pc += 2

    @instruction(name="SBC", mode="abx", cycles=4, extracycles=1)
    def inst_0xfd(self):
        self.opSBC(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="INC", mode="abx", cycles=7)
    def inst_0xfe(self):
        self.opINCR(self.AbsoluteXAddr)
        self.pc += 2

# --- MEMORY BUS ADAPTER ---

class MemoryBus:
    """
    Acts as a bridge between the MPU (which expects a simple list-like memory)
    and the Apple1System (which has complex read/write MMIO logic).
    """
    def __init__(self, system):
        self.system = system
        
    def __getitem__(self, addr):
        # MPU expects byte at address
        return self.system.read(addr & 0xFFFF)
        
    def __setitem__(self, addr, value):
        # MPU writes byte to address
        self.system.write(addr & 0xFFFF, value)

    def __len__(self):
        return 65536

# --- SYSTEM EMULATOR ---

class Apple1System:
    def __init__(self, display_callback):
        self.memory = bytearray(65536)
        
        # Initialize Memory Wrapper for the new CPU
        self.mem_bus = MemoryBus(self)
        
        # Initialize the new MPU class with our wrapped memory.
        # pc=None tells it to look up the reset vector (FFFC) for start address.
        self.cpu = MPU(memory=self.mem_bus, pc=None)
        
        self.display_callback = display_callback
        
        # PIA State
        self.kbd = 0x00
        self.kbdcr = 0x00 # Bit 7 set when key ready
        self.dsp = 0x00
        self.dspcr = 0x00 # Bit 7 set when display ready (set to 1 when $7F received)
        
        self.load_roms()
        self.thread = None

    def load_roms(self):
        # Load Wozmon
        for i, b in enumerate(WOZMON_DATA):
            self.memory[0xFF00 + i] = b
            
        # Vectors
        self.memory[0xFFFA] = 0x00 # NMI
        self.memory[0xFFFB] = 0x00
        self.memory[0xFFFC] = 0x00 # Reset Lo
        self.memory[0xFFFD] = 0xFF # Reset Hi -> FF00
        self.memory[0xFFFE] = 0x00 # IRQ
        self.memory[0xFFFF] = 0x00

        # Load ACI
        for i, b in enumerate(ACI_DATA):
            self.memory[0xC100 + i] = b

    def read(self, addr):
        # PIA Keyboard
        if addr == 0xD010:
            val = self.kbd
            self.kbd &= 0x7F # Clear strobe bit in register after read?
            self.kbdcr = 0x00 # Clear ready flag
            return val
        elif addr == 0xD011:
            return self.kbdcr # Bit 7 is status
            
        # PIA Display
        elif addr == 0xD012:
            return randrange(256)
        elif addr == 0xD013:
            return self.dspcr # Bit 7 is ready status (always 1 here)
            
        # ACI Load Trigger
        elif addr == 0xC081:
            # Wozmon stores destination address at $24,$25
            dest_addr = self.memory[0x24] | (self.memory[0x25] << 8)
            
            # Note: filedialog will open a GUI window, which might pause execution
            file_path = filedialog.askopenfilename(filetypes=[("Binary file", "*.bin"), ("All files", "*.*")])
            if file_path:
                try:
                    with open(file_path, "rb") as f:
                        data = f.read()
                        # Write data into emulator memory
                        for i, byte in enumerate(data):
                            if dest_addr + i < 0x10000: self.memory[dest_addr + i] = byte
                        print(f"Loaded {len(data)} bytes from {file_path}")
                except Exception as e:
                    print(f"Load failed: {e}")
            return 0 # Return dummy value

        return self.memory[addr]

    def write(self, addr, value):
        # PIA Display
        if addr == 0xD012:
            if self.dspcr != 0x00:
                self.display_callback(value)
            if self.dspcr == 0x00 and value == 0x7f:
                self.dspcr = 0x80
            return
            
        if 0x0000 <= addr < 0x8000: # RAM (extended for convenience)
            self.memory[addr] = value
        
        # ACI Save Trigger
        elif addr == 0xC028:
            start_addr = self.memory[0x26] | (self.memory[0x27] << 8)
            end_addr = self.memory[0x24] | (self.memory[0x25] << 8)
            
            # Ensure the end is after the start
            if end_addr >= start_addr:
                file_path = filedialog.asksaveasfilename(filetypes=[("Binary file", "*.bin"), ("All files", "*.*")])
                if file_path:
                    try:
                        with open(file_path, "wb") as f: f.write(self.memory[start_addr:end_addr + 1])
                        print(f"Saved {end_addr - start_addr + 1} bytes to {file_path}")
                    except Exception as e:
                        print(f"Save failed: {e}")
            return

    def key_pressed(self, key_byte):
        self.kbd = key_byte | 0x80 # Set bit 7
        self.kbdcr = 0x80          # Set status ready

def setup_console():
    """Sets up the console for raw input depending on the OS."""
    if sys.platform == "win32":
        import msvcrt
        def get_key():
            if msvcrt.kbhit():
                # Get the char and convert to Apple 1 expected format
                char = msvcrt.getch()
                if char == b'\xe0':
                    msvcrt.getch()
                    return None
                try:
                    return char.decode().upper()
                except:
                    return None
            return None
        return get_key
    else:
        import tty, termios, select
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setraw(sys.stdin.fileno())
        def get_key():
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                return sys.stdin.read(1).upper()
            return None
        return get_key

def console_display(char):
    """Translates Apple 1 character codes to the system console."""
    char = char & 0x7F
    if char == 0x0D:
        sys.stdout.write("\n")
        sys.stdout.flush()
    elif char > 0x1F:
        # Signetics 2513 character set
        charset = "                                 !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_"
        sys.stdout.write(charset[char])  
        sys.stdout.flush()

def null_display(char):
    """A null display."""
    pass

def apple1_emulator(args):
    """Main program."""
    turbo = args.turbo # Turbo mode (will allow maximum speed, which is usually ~30-50 kinst/s, or ~60-350 KHz, depending on single-core performance)
    bench = args.bench # Benchmark mode (will disable display and keyboard, while displaying emulated CPU speed in kinst/s)
    system = Apple1System(null_display) if bench else Apple1System(console_display)
    get_key = setup_console()
    
    # Initialize CPU (Reset vector loaded automatically by MPU class via MemoryBus)
    system.cpu.reset()
    if bench:
        start = time()
        count = 0
    
    try:
        while True:
            # Read keyboard (quite a performance bottleneck, but improvements are yet to come)
            # If it weren't for this bottleneck, the speed would be about ~1 Minst/s, or ~2-7 MHz
            key = get_key()
            if key:
                ascii_val = int(ord(key).to_bytes().hex(), 16)
                if (ascii_val > 31 and ascii_val < 96) or ascii_val == 13 or ascii_val == 27:
                    if not bench: system.key_pressed(ascii_val)
                elif ascii_val == 8: # Backspace
                    if not bench: system.key_pressed(0x7F)
                elif ascii_val == 9: # Tab
                    if not bench:
                        system.cpu.reset()
                        system.dspcr = 0x00
            
            # Execute one instruction (2-7 cycles)
            system.cpu.step()
            
            # Non-turbo mode (will limit to 1/25th maximum speed)
            if not turbo: sleep(0.0000000001)

            if bench:
                count += 1
                if time() - start >= 1:
                    print(count / 1000)
                    start = time()
                    count = 0
            
    except KeyboardInterrupt:
        pass
    finally:
        if sys.platform != "win32":
            # Restore terminal settings on exit
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, termios.tcgetattr(sys.stdin.fileno()))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="An Apple-1 emulator based on the MOS 6502 microprocessor.")
    parser.add_argument('-t', '--turbo', action='store_true', help='run CPU at full speed')
    parser.add_argument('-b', '--bench', action='store_true', help='test maximum CPU speed')
    args = parser.parse_args()
    apple1_emulator(args)