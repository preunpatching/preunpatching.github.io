try:
    from tkinter import filedialog
    tkinter_available = True
except ImportError:
    tkinter_available = False
try:
    from requests import Session
    requests_available = True
except ImportError:
    requests_available = False
import sys, argparse, threading
from collections import deque
from time import time, sleep
from random import random
from os.path import exists

# --- ROM Data ---
# Wozmon ($FF00 - $FFF9)
WOZMON_DATA = b"\xd8X\xa0\x7f\x8c\x12\xd0\xa9\xa7\x8d\x11\xd0\x8d\x13\xd0\xc9\xdf\xf0\x13\xc9\x9b\xf0\x03\xc8\x10\x0f\xa9\xdc \xef\xff\xa9\x8d \xef\xff\xa0\x01\x880\xf6\xad\x11\xd0\x10\xfb\xad\x10\xd0\x99\x00\x02 \xef\xff\xc9\x8d\xd0\xd4\xa0\xff\xa9\x00\xaa\n\x85+\xc8\xb9\x00\x02\xc9\x8d\xf0\xd4\xc9\xae\x90\xf4\xf0\xf0\xc9\xba\xf0\xeb\xc9\xd2\xf0;\x86(\x86)\x84*\xb9\x00\x02I\xb0\xc9\n\x90\x06i\x88\xc9\xfa\x90\x11\n\n\n\n\xa2\x04\n&(&)\xca\xd0\xf8\xc8\xd0\xe0\xc4*\xf0\x97$+P\x10\xa5(\x81&\xe6&\xd0\xb5\xe6'LD\xffl$\x000+\xa2\x02\xb5'\x95%\x95#\xca\xd0\xf7\xd0\x14\xa9\x8d \xef\xff\xa5% \xdc\xff\xa5$ \xdc\xff\xa9\xba \xef\xff\xa9\xa0 \xef\xff\xa1$ \xdc\xff\x86+\xa5$\xc5(\xa5%\xe5)\xb0\xc1\xe6$\xd0\x02\xe6%\xa5$)\x07\x10\xc8HJJJJ \xe5\xffh)\x0f\t\xb0\xc9\xba\x90\x02i\x06,\x12\xd00\xfb\x8d\x12\xd0`\x00\x00"

# Modified Apple Cassette Interface ($C100 - $C17B)
# Reads or writes a cassette port once, then returns.
ACI_DATA = b"\xa9\xaa \xef\xff\xa9\x8d \xef\xff\xa0\xff\xc8\xad\x11\xd0\x10\xfb\xad\x10\xd0\x99\x00\x02 \xef\xff\xc9\x9b\xf0\xe1\xc9\x8d\xd0\xe9\xa2\xff\xa9\x00\x85$\x85%\x85&\x85'\xe8\xbd\x00\x02\xc9\xd2\xf09\xc9\xd7\xf0;\xc9\xae\xf0'\xc9\x8d\xf0 \xc9\xa0\xf0\xe8I\xb0\xc9\n\x90\x06i\x88\xc9\xfa\x90\xad\n\n\n\n\xa0\x04\n&$&%\x88\xd0\xf8\xf0\xccL\x1a\xff\xa5$\x85&\xa5%\x85'\xb0\xbf\xad\x81\xc0L\x1a\xff\x8d(\xc0L\x1a\xff"

# Network Interface ($C100 - $C1B1)
NET_DATA = b" ^\xc1\xa2\x00\xad\x11\xd0\x10\xfb\xad\x10\xd0\xc9\xdf\xf0\x0e\xc9\x8d\xf0\x15\xe0\xc8\xf0\xec \xef\xff)\x7f\x950\xe8\xd0\xe2\xe0\x00\xf0\xde\xca \xef\xffL\x05\xc1 \xef\xff\xa9\x00\x950\xa2\x00\xb50\xf0\x06\x8d\x16\xd0\xe8\xd0\xf6\xa9\x7f\x8d\x16\xd0\xad\x15\xd0\x10\xfb\xad\x14\xd0\xc9\x03\xf0\xb2\xc9\x7f\xf0\x17\t\x80 \xef\xffLF\xc1\xa9\x8d \xef\xff\xa9\xbe \xef\xff\xa9\xa0L\xef\xff \xa9\xc1\x85\x00 \xa9\xc1\x85\x01\xaa \xa9\xc1\x85\x02 \xa9\xc1\x85\x03\xa0\x00\xa5\x02\x05\x03\xf0\x1a \xa9\xc1\x91\x00\xc8\xd0\x02\xe6\x01\xc6\x02\xa5\x02\xc9\xff\xd0\x02\xc6\x03\xa5\x02\x05\x03\xd0\xe6\x86\x01l\x00\x00\xad\x15\xd0\x10\xfb\xad\x14\xd0`"
"""
$c100  20 5e c1  JSR $c15e
$c103  a2 00     LDX #$00
$c105  ad 11 d0  LDA $d011
$c108  10 fb     BPL $c105
$c10a  ad 10 d0  LDA $d010
$c10d  c9 df     CMP #$df
$c10f  f0 0e     BEQ $c11f
$c111  c9 8d     CMP #$8d
$c113  f0 15     BEQ $c12a
$c115  e0 c8     CPX #$c8
$c117  f0 ec     BEQ $c105
$c119  20 ef ff  JSR $ffef
$c11c  29 7f     AND #$7f
$c11e  95 30     STA $30,X
$c120  e8        INX
$c121  d0 e2     BNE $c105
$c123  e0 00     CPX #$00
$c125  f0 de     BEQ $c105
$c127  ca        DEX
$c128  20 ef ff  JSR $ffef
$c12b  4c 05 c1  JMP $c105
$c12e  20 ef ff  JSR $ffef
$c131  a9 00     LDA #$00
$c133  95 30     STA $30,X
$c135  a2 00     LDX #$00
$c137  b5 30     LDA $30,X
$c139  f0 06     BEQ $c141
$c13b  8d 16 d0  STA $d016
$c13e  e8        INX
$c13f  d0 f6     BNE $c137
$c141  a9 7f     LDA #$7f
$c143  8d 16 d0  STA $d016
$c146  ad 15 d0  LDA $d015
$c149  10 fb     BPL $c146
$c14b  ad 14 d0  LDA $d014
$c14e  c9 03     CMP #$03
$c150  f0 b2     BEQ $c104
$c152  c9 7f     CMP #$7f
$c154  f0 17     BEQ $c16d
$c156  09 80     ORA #$80
$c158  20 ef ff  JSR $ffef
$c15b  4c 46 c1  JMP $c146
$c15e  a9 8d     LDA #$8d
$c160  20 ef ff  JSR $ffef
$c163  a9 be     LDA #$be
$c165  20 ef ff  JSR $ffef
$c168  a9 a0     LDA #$a0
$c16a  4c ef ff  JMP $ffef
$c16d  20 a9 c1  JSR $c1a9
$c170  85 00     STA $00
$c172  20 a9 c1  JSR $c1a9
$c175  85 01     STA $01
$c177  aa        TAX
$c178  20 a9 c1  JSR $c1a9
$c17b  85 02     STA $02
$c17d  20 a9 c1  JSR $c1a9
$c180  85 03     STA $03
$c182  a0 00     LDY #$00
$c184  a5 02     LDA $02
$c186  05 03     ORA $03
$c188  f0 1a     BEQ $c1a4
$c18a  20 a9 c1  JSR $c1a9
$c18d  91 00     STA ($00),Y
$c18f  c8        INY
$c190  d0 02     BNE $c194
$c192  e6 01     INC $01
$c194  c6 02     DEC $02
$c196  a5 02     LDA $02
$c198  c9 ff     CMP #$ff
$c19a  d0 02     BNE $c19e
$c19c  c6 03     DEC $03
$c19e  a5 02     LDA $02
$c1a0  05 03     ORA $03
$c1a2  d0 e6     BNE $c18a
$c1a4  86 01     STX $01
$c1a6  6c 00 00  JMP ($0000)
$c1a9  ad 15 d0  LDA $d015
$c1ac  10 fb     BPL $c1a9
$c1ae  ad 14 d0  LDA $d014
$c1b1  60        RTS
"""

# --- 6502 Microprocessor Unit (Derived from Py65 emulator) ---

class MPU6502:
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
            memory = 0x10000 * [0x00]
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

class MPU65C02(MPU6502):
    def __init__(self, *args, **kwargs):
        MPU6502.__init__(self, *args, **kwargs)
        self.name = '65C02'
        self.waiting = False

    def step(self):
        if self.waiting:
            self.processorCycles += 1
        else:
            MPU6502.step(self)
        return self

    # Make copies of the lists
    instruct = MPU6502.instruct[:]
    cycletime = MPU6502.cycletime[:]
    extracycles = MPU6502.extracycles[:]
    disassemble = MPU6502.disassemble[:]

    instruction = MPU6502.make_instruction_decorator(instruct, disassemble,
                                             cycletime, extracycles)

    # addressing modes

    def ZeroPageIndirectAddr(self):
        return self.WordAt(255 & (self.ByteAt(self.pc)))

    def IndirectAbsXAddr(self):
        return (self.WordAt(self.pc) + self.x) & self.addrMask

    # operations

    def opRMB(self, x, mask):
        address = x()
        self.memory[address] &= mask

    def opSMB(self, x, mask):
        address = x()
        self.memory[address] |= mask

    def opSTZ(self, x):
        self.memory[x()] = 0x00

    def opTSB(self, x):
        address = x()
        m = self.memory[address]
        self.p &= ~self.ZERO
        z = m & self.a
        if z == 0:
            self.p |= self.ZERO
        self.memory[address] = m | self.a

    def opTRB(self, x):
        address = x()
        m = self.memory[address]
        self.p &= ~self.ZERO
        z = m & self.a
        if z == 0:
            self.p |= self.ZERO
        self.memory[address] = m & ~self.a

    # instructions

    @instruction(name="BRK", mode="imp", cycles=7)
    def inst_0x00(self):
        # pc has already been increased one
        pc = (self.pc + 1) & self.addrMask
        self.stPushWord(pc)

        self.p |= self.BREAK
        self.stPush(self.p | self.BREAK | self.UNUSED)

        self.p |= self.INTERRUPT
        self.pc = self.WordAt(self.IRQ)

        # 65C02 clears decimal flag, NMOS 6502 does not
        self.p &= ~self.DECIMAL

    @instruction(name="TSB", mode="zpg", cycles=5)
    def inst_0x04(self):
        self.opTSB(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="RMB0", mode="zpg", cycles=5)
    def inst_0x07(self):
        self.opRMB(self.ZeroPageAddr, 0xFE)
        self.pc += 1

    @instruction(name="TSB", mode="abs", cycles=6)
    def inst_0x0c(self):
        self.opTSB(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="ORA", mode="zpi", cycles=5)
    def inst_0x12(self):
        self.opORA(self.ZeroPageIndirectAddr)
        self.pc += 1

    @instruction(name="TRB", mode="zpg", cycles=5)
    def inst_0x14(self):
        self.opTRB(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="RMB1", mode="zpg", cycles=5)
    def inst_0x17(self):
        self.opRMB(self.ZeroPageAddr, 0xFD)
        self.pc += 1

    @instruction(name="INC", mode="acc", cycles=2)
    def inst_0x1a(self):
        self.opINCR(None)

    @instruction(name="TRB", mode="abs", cycles=6)
    def inst_0x1c(self):
        self.opTRB(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="RMB2", mode="zpg", cycles=5)
    def inst_0x27(self):
        self.opRMB(self.ZeroPageAddr, 0xFB)
        self.pc += 1

    @instruction(name="AND", mode="zpi", cycles=5)
    def inst_0x32(self):
        self.opAND(self.ZeroPageIndirectAddr)
        self.pc += 1

    @instruction(name="BIT", mode="zpx", cycles=4)
    def inst_0x34(self):
        self.opBIT(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="RMB3", mode="zpg", cycles=5)
    def inst_0x37(self):
        self.opRMB(self.ZeroPageAddr, 0xF7)
        self.pc += 1

    @instruction(name="DEC", mode="acc", cycles=2)
    def inst_0x3a(self):
        self.opDECR(None)

    @instruction(name="BIT", mode="abx", cycles=4)
    def inst_0x3c(self):
        self.opBIT(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="RMB4", mode="zpg", cycles=5)
    def inst_0x47(self):
        self.opRMB(self.ZeroPageAddr, 0xEF)
        self.pc += 1

    @instruction(name="EOR", mode="zpi", cycles=5)
    def inst_0x52(self):
        self.opEOR(self.ZeroPageIndirectAddr)
        self.pc += 1

    @instruction(name="RMB5", mode="zpg", cycles=5)
    def inst_0x57(self):
        self.opRMB(self.ZeroPageAddr, 0xDF)
        self.pc += 1

    @instruction(name="PHY", mode="imp", cycles=3)
    def inst_0x5a(self):
        self.stPush(self.y)

    @instruction(name="STZ", mode="zpg", cycles=3)
    def inst_0x64(self):
        self.opSTZ(self.ZeroPageAddr)
        self.pc += 1

    @instruction(name="RMB6", mode="zpg", cycles=5)
    def inst_0x67(self):
        self.opRMB(self.ZeroPageAddr, 0xBF)
        self.pc += 1

    @instruction(name="JMP", mode="ind", cycles=6)
    def inst_0x6c(self):
        ta = self.WordAt(self.pc)
        self.pc = self.WordAt(ta)

    @instruction(name="ADC", mode="zpi", cycles=5)
    def inst_0x72(self):
        self.opADC(self.ZeroPageIndirectAddr)
        self.pc += 1

    @instruction(name="STZ", mode="zpx", cycles=4)
    def inst_0x74(self):
        self.opSTZ(self.ZeroPageXAddr)
        self.pc += 1

    @instruction(name="RMB7", mode="zpg", cycles=5)
    def inst_0x77(self):
        self.opRMB(self.ZeroPageAddr, 0x7F)
        self.pc += 1

    @instruction(name="PLY", mode="imp", cycles=4)
    def inst_0x7a(self):
        self.y = self.stPop()
        self.FlagsNZ(self.y)

    @instruction(name="JMP", mode="iax", cycles=6)
    def inst_0x7c(self):
        self.pc = self.WordAt(self.IndirectAbsXAddr())

    @instruction(name="BRA", mode="rel", cycles=1, extracycles=1)
    def inst_0x80(self):
        self.BranchRelAddr()

    @instruction(name="SMB0", mode="zpg", cycles=5)
    def inst_0x87(self):
        self.opSMB(self.ZeroPageAddr, 0x01)
        self.pc += 1

    @instruction(name="BIT", mode="imm", cycles=2)
    def inst_0x89(self):
        # This instruction (BIT #$12) does not use opBIT because in the
        # immediate mode, BIT only affects the Z flag.
        tbyte = self.ImmediateByte()
        self.p &= ~(self.ZERO)
        if (self.a & tbyte) == 0:
            self.p |= self.ZERO
        self.pc += 1

    @instruction(name="STA", mode="zpi", cycles=5)
    def inst_0x92(self):
        self.opSTA(self.ZeroPageIndirectAddr)
        self.pc += 1

    @instruction(name="SMB1", mode="zpg", cycles=5)
    def inst_0x97(self):
        self.opSMB(self.ZeroPageAddr, 0x02)
        self.pc += 1

    @instruction(name="STZ", mode="abs", cycles=4)
    def inst_0x9c(self):
        self.opSTZ(self.AbsoluteAddr)
        self.pc += 2

    @instruction(name="STZ", mode="abx", cycles=5)
    def inst_0x9e(self):
        self.opSTZ(self.AbsoluteXAddr)
        self.pc += 2

    @instruction(name="SMB2", mode="zpg", cycles=5)
    def inst_0xa7(self):
        self.opSMB(self.ZeroPageAddr, 0x04)
        self.pc += 1

    @instruction(name="LDA", mode="zpi", cycles=5)
    def inst_0xb2(self):
        self.opLDA(self.ZeroPageIndirectAddr)
        self.pc += 1

    @instruction(name="SMB3", mode="zpg", cycles=5)
    def inst_0xb7(self):
        self.opSMB(self.ZeroPageAddr, 0x08)
        self.pc += 1

    @instruction(name="SMB4", mode="zpg", cycles=5)
    def inst_0xc7(self):
        self.opSMB(self.ZeroPageAddr, 0x10)
        self.pc += 1

    @instruction(name="WAI", mode='imp', cycles=3)
    def inst_0xcb(self):
        self.waiting = True

    @instruction(name="CMP", mode='zpi', cycles=5)
    def inst_0xd2(self):
        self.opCMPR(self.ZeroPageIndirectAddr, self.a)
        self.pc += 1

    @instruction(name="SMB5", mode="zpg", cycles=5)
    def inst_0xd7(self):
        self.opSMB(self.ZeroPageAddr, 0x20)
        self.pc += 1

    @instruction(name="PHX", mode="imp", cycles=3)
    def inst_0xda(self):
        self.stPush(self.x)

    @instruction(name="SMB6", mode="zpg", cycles=5)
    def inst_0xe7(self):
        self.opSMB(self.ZeroPageAddr, 0x40)
        self.pc += 1

    @instruction(name="SBC", mode="zpi", cycles=5)
    def inst_0xf2(self):
        self.opSBC(self.ZeroPageIndirectAddr)
        self.pc += 1

    @instruction(name="SMB7", mode="zpg", cycles=5)
    def inst_0xf7(self):
        self.opSMB(self.ZeroPageAddr, 0x80)
        self.pc += 1

    @instruction(name="PLX", mode="imp", cycles=4)
    def inst_0xfa(self):
        self.x = self.stPop()
        self.FlagsNZ(self.x)

# --- Memory Bus Adapter ---

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

# --- Apple-1 System Emulator ---

class Apple1System:
    def __init__(self, mpu, display_callback, raw_display, no_aci, network, fast_display, alt_display, bench):
        self.memory = bytearray(65536)

        # Hardware
        self.cpu = mpu
        self.mem_bus = MemoryBus(self)

        # ROM
        self.wozmon = None
        self.exp = None

        # Variables
        self.display_callback = display_callback
        self.raw_display = raw_display
        self.alt_display = alt_display
        self.no_aci = no_aci
        self.network = network
        self.fast_display = fast_display
        self.char_in_line = 0
        self.init_terminal, self.reset_terminal = setup_console(self)
        self.bench = bench
        self.terminated = False
        self.dsp_mem = bytearray()

        # PIA
        self.kbd = 0x00
        self.kbdcr = 0x00 # Bit 7 set when key ready
        self.dsp = 0x00
        self.dspcr = False # True when display ready (set to True when $7F received)
        self.dsp_clock = 0
        self.dsp_buffer = deque()

        if self.network:
            # Networking State
            self.net_session = Session()
            self.net_url_buffer = []
            self.net_response_queue = deque()
            self.net_busy = False

        self.load_roms()
        self.cpu = self.cpu(memory=self.mem_bus)

    def _network_fetch(self, url):
        """Internal helper to fetch data in a separate thread."""
        try:
            # Fetch the content
            self.net_response_queue = deque()
            response = self.net_session.get(url, stream=True)

            for char in response.iter_content():
                self.net_response_queue.append(ord(char)) 
        except:
            pass
        finally:
            self.net_response_queue.append(0x03)
            self.net_busy = False

    def load_roms(self):
        # Load Wozmon
        self.wozmon = WOZMON_DATA
        self.memory[self.cpu.RESET], self.memory[self.cpu.RESET+1] = 0x00, 0xff
        self.memory[self.cpu.NMI], self.memory[self.cpu.NMI+1] = 0x00, 0x0f
        self.memory[self.cpu.IRQ], self.memory[self.cpu.IRQ+1] = 0x00, 0x00

        if not self.no_aci:
            # Load ACI
            self.exp = ACI_DATA

        if self.network:
            # Load Network Interface
            self.exp = NET_DATA

    def read(self, addr):
        # PIA Keyboard
        if addr == 0xD010:
            val = self.kbd
            self.kbd &= 0x7F # Clear strobe bit in register after read
            self.kbdcr = 0x00 # Clear ready flag
            return val
        elif addr == 0xD011:
            return self.kbdcr # Bit 7 is status

        # PIA Display
        elif addr == 0xD012:
            if self.fast_display or self.alt_display:
                return 0x00
            else:
                if self.dsp: self.dsp = 0x80 if time() < self.dsp_clock else 0x00
                return self.dsp
        elif addr == 0xD013:
            return 0x00 # Not intended to be read

        # PIA Network
        elif addr == 0xD014 and self.network:
            return self.net_response_queue.popleft() if self.net_response_queue else 0x00
        elif addr == 0xD015 and self.network:
            return 0x80 if self.net_response_queue else 0x00
        elif addr == 0xD016 and self.network:
            return 0x80 if self.net_busy else 0x00

        # ACI Load Trigger
        elif addr == 0xC081 and not self.no_aci:
            # Wozmon stores destination address at $24,$25
            dest_addr = self.memory[0x24] | (self.memory[0x25] << 8)

            if tkinter_available:
                file_path = filedialog.askopenfilename(filetypes=[("Binary file", "*.bin"), ("All files", "*.*")])
            else:
                self.reset_terminal()
                file_path = input('Input a binary file to load: ')
                self.init_terminal()
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

        elif addr >= 0xC100 and addr <= 0xC1FF and self.exp:
            return self.exp[addr - 0xC100]

        elif addr >= 0xFF00 and addr <= 0xFFF9 and self.wozmon:
            return self.wozmon[addr - 0xFF00]

        return self.memory[addr]

    def write(self, addr, value):
        # PIA Display
        if addr == 0xD012:
            if self.dspcr and not self.dsp:
                if self.alt_display:
                    self.dsp_buffer.append(value)
                else:
                    self.display_callback(self, value, self.raw_display)
                    if not self.fast_display:
                        self.dsp = 0x80
                        self.dsp_clock = time() + 1 / 60.05
            return

        if addr == 0xD013:
            self.dspcr = True
            return

        # PIA Network
        elif addr == 0xD016 and self.network:
            if not self.net_busy:
                if value == 0x7F:
                    url = "".join(self.net_url_buffer).lower()
                    self.net_url_buffer = [] # Clear buffer for next time
                    self.net_busy = True
                    # Start fetch in a background thread
                    threading.Thread(target=self._network_fetch, args=(url,), daemon=True).start()
                else:
                    # Build the URL string
                    self.net_url_buffer.append(chr(value))
            return

        # ACI Save Trigger
        elif addr == 0xC028 and not self.no_aci:
            start_addr = self.memory[0x26] | (self.memory[0x27] << 8)
            end_addr = self.memory[0x24] | (self.memory[0x25] << 8)

            # Ensure the end is after the start
            if end_addr >= start_addr:
                if tkinter_available:
                    file_path = filedialog.asksaveasfilename(filetypes=[("Binary file", "*.bin"), ("All files", "*.*")])
                else:
                    self.reset_terminal()
                    file_path = input('Input a binary file to save: ')
                    self.init_terminal()
                if file_path:
                    try:
                        with open(file_path, "wb") as f: f.write(self.memory[start_addr:end_addr + 1])
                        print(f"Saved {end_addr - start_addr + 1} bytes to {file_path}")
                    except Exception as e:
                        print(f"Save failed: {e}")
            return

        # RAM
        else:
            self.memory[addr] = value
            return

    def save_state(self):
        state = b''
        if self.cpu.pc < 256:
            state += bytes([0x00, self.cpu.pc])
        else:
            state += bytes([self.cpu.pc // 256, self.cpu.pc % 256])
        state += bytes([self.cpu.a, self.cpu.x, self.cpu.y, self.cpu.sp, self.cpu.p])
        state += bytes(self.memory)
        self.dsp_mem = self.dsp_mem.replace(b'\n', b'')
        state += bytes(bytes(1000 - len(self.dsp_mem)) + self.dsp_mem)
        with open(f'save_state_{int(time())}.bin', 'wb') as f:
            f.write(state)

    def load_state(self, filename):
        with open(filename, 'rb') as f:
            self.cpu.pc = int(f.read(2).hex(), 16)
            self.cpu.a = int(f.read(1).hex(), 16)
            self.cpu.x = int(f.read(1).hex(), 16)
            self.cpu.y = int(f.read(1).hex(), 16)
            self.cpu.sp = int(f.read(1).hex(), 16)
            self.cpu.p = int(f.read(1).hex(), 16)
            self.memory = bytearray(f.read(65536))
            dsp_mem = bytearray(f.read(1000))
            for value in dsp_mem:
                self.display_callback(self, value, self.raw_display)
            self.dspcr = True

    def key_pressed(self, key, bench):
        if key:
            ascii_val = ord(key)
            if (ascii_val > 31 and ascii_val < 96) or ascii_val == 13 or ascii_val == 27:
                if not bench:
                    self.kbd = ascii_val | 0x80
                    self.kbdcr = 0x80
            elif ascii_val == 3: # EOF (Break)
                raise KeyboardInterrupt
            elif ascii_val == 8 or ascii_val == 127: # Backspace
                if not bench:
                    self.kbd = 0x5F | 0x80
                    self.kbdcr = 0x80
            elif ascii_val == 9: # Tab
                if not bench:
                    self.reset()
                    self.dspcr = 0x00
            elif ascii_val == 10: # Ctrl+Enter
                if not bench:
                    self.save_state()

    def terminate(self):
        self.terminated = True

    # Passthroughs (use these instead of direct MPU functions)
    def step(self):
        if self.terminated: raise KeyboardInterrupt
        self.cpu.step()

    def reset(self):
        if self.terminated: raise KeyboardInterrupt
        self.cpu.reset()
        self.net_url_buffer = []
        self.net_response_queue = deque()
        self.net_busy = False

def setup_console(system):
    """Sets up the console for raw input depending on the OS."""
    if sys.platform == "win32":
        import msvcrt
        def get_key():
            try:
                while True:
                    if msvcrt.kbhit():
                        # Get the char and convert to Apple 1 expected format
                        char = msvcrt.getch()
                        if char == b'\xe0':
                            msvcrt.getch()
                        try:
                            system.key_pressed(char.decode().upper(), system.bench)
                        except: pass
                    sleep(0.0000000001)
            except KeyboardInterrupt:
                system.terminate()
        # Not needed on Windows
        def init_terminal():
            pass
        def reset_terminal():
            pass
        threading.Thread(target=get_key, daemon=True).start()
        return init_terminal, reset_terminal
    else:
        import tty, termios, select
        old_settings = termios.tcgetattr(sys.stdin.fileno())
        def get_key():
            try:
                while True:
                    if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                        char = sys.stdin.read(1).upper()
                        system.key_pressed(char, system.bench)
                    sleep(0.0000000001)
            except KeyboardInterrupt:
                system.terminate()
        def init_terminal():
            # Set terminal to raw mode
            tty.setraw(sys.stdin.fileno())
        def reset_terminal():
            # Restore terminal settings on exit
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, old_settings)
        init_terminal()
        threading.Thread(target=get_key, daemon=True).start()
        return init_terminal, reset_terminal

def console_display(self, char, raw_display):
    """Translates Apple 1 character codes to the system console."""
    char = char & 0x7F
    if char == 0x0D:
        sys.stdout.write("\r\n")
        sys.stdout.flush()
        self.char_in_line = 0
        self.dsp_mem.append(char)
        while self.dsp_mem.count(0x0D) + self.dsp_mem.count(0x0A) > 25:
            self.dsp_mem.pop(0)
    elif char > 0x1F:
        # Signetics 2513 character set
        charset = "                                 !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_"
        sys.stdout.write(charset[char])
        sys.stdout.flush()
        self.char_in_line += 1
        self.dsp_mem.append(char)
        if self.char_in_line >= 40:
            if not raw_display:
                sys.stdout.write("\r\n")
                sys.stdout.flush()
            self.dsp_mem.append(0x0A)
            self.char_in_line = 0
            while self.dsp_mem.count(0x0D) + self.dsp_mem.count(0x0A) > 25:
                self.dsp_mem.pop(0)

def null_display(self, char, raw_display):
    """A null display."""
    pass

def apple1_emulator(args):
    """Main program."""
    # Arguments
    mpu, turbo, bench, raw_display, no_aci, network, fast_display, alt_display, load_state = (MPU65C02 if args.turbo else MPU6502), args.turbo, args.bench, args.raw_display, args.no_aci, args.network, args.fast_display, args.alt_display, args.load_state

    # System
    system = Apple1System(mpu, null_display, raw_display, no_aci, network, fast_display, alt_display, bench) if bench else Apple1System(mpu, console_display, raw_display, no_aci, network, fast_display, alt_display, bench)


    # Initialize CPU
    system.reset()

    if load_state: system.load_state(load_state)

    if bench:
        start = time()
        count = 0

    try:
        while True:
            # Execute one instruction (2-7 cycles)
            system.step()

            if system.alt_display and system.dsp_buffer and time() >= system.dsp_clock:
                system.display_callback(system, system.dsp_buffer.popleft(), system.raw_display)
                system.dsp_clock = time() + 1 / 60.05

            # Non-turbo mode (will limit maximum speed, usually to a few KHz, which is normally enough for most Apple-1 software)
            if not turbo: sleep(0.0000000001)

            if bench:
                if time() - start >= 1:
                    print((system.cpu.processorCycles - count) / 1000, end='\r\n')
                    start = time()
                    count = system.cpu.processorCycles

    except KeyboardInterrupt:
        system.reset_terminal()
        pass
    except Exception:
        system.reset_terminal()
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="An Apple-1 emulator based on the MOS 6502 microprocessor unit.")
    parser.add_argument('-t', '--turbo', action='store_true', help='run CPU at full speed')
    parser.add_argument('-b', '--bench', action='store_true', help='test maximum CPU speed')
    parser.add_argument('-r', '--raw-display', action='store_true', help='do not simulate a 40-column display')
    parser.add_argument('-a', '--no-aci', action='store_true', help='disable Apple Cassette Interface')
    parser.add_argument('-n', '--network', action='store_true', help='enable networking interface')
    parser.add_argument('-f', '--fast-display', action='store_true', help='unlocks display from 60 cps limit')
    parser.add_argument('--alt-display', action='store_true', help='use alternate non-blocking 60 cps display')
    parser.add_argument('--65c02', action='store_true', help='use WDC 65C02 instead of NMOS 6502 (may cause compatibility issues)')
    parser.add_argument('-l', '--load-state', action='store', help='load save state from disk')
    args = parser.parse_args()
    if not requests_available and args.network: raise ModuleNotFoundError('Requests module not found. Install it with: pip install requests')
    if not args.no_aci and args.network: args.no_aci = True
    apple1_emulator(args)