@echo OFF
if "%1"=="/?" goto help
title Microsoft Windows Setup
cls
echo Microsoft Windows Setup
echo -----------------------
if "%1"=="/^|" goto force
if not exist X:\Windows\System32\wpeutil.exe (
echo This program cannot run in Windows OS.
echo Setup cannot continue.
exit /b 2
)
:force
echo Step 1/3 - Collecting information
goto setup1
:notWindowsInstallDisc
echo The selected drive does not appear to be a Windows install disc.
echo Please try again.
:setup1
echo lis vol>X:\temp.txt
diskpart /s X:\temp.txt
del X:\temp.txt
set /p src="Select your source drive letter (for example D): "
if not exist %src%:\sources goto notWindowsInstallDisc
for %%f in (%src%:\sources\install.*) do set img=%%f
if "%img%"=="" goto notWindowsInstallDisc
%src%:
cd %src%:\sources
dism /get-wiminfo /wimfile:%img%
set /p idx="Select your source image index (for example 6): "
goto setup2
:unspecifiedDrive
echo Please specify a drive number.
:setup2
echo lis dis>X:\temp.txt
diskpart /s X:\temp.txt
del X:\temp.txt
set /p drv="Select your target drive number (for example 0): "
if not defined drv goto unspecifiedDrive
goto setup3
:unspecifiedName
echo Please specify a user name.
:setup3
set /p name="Specify your user name: "
if not defined name goto unspecifiedName
set /p pass="Specify your user password (optional): "
goto setup4
:unspecifiedMSR
echo Please specify a choice.
:setup4
set /p choice="Do you need Microsoft Reserved partition [Y/N]? "
if /i "%choice%"=="y" goto setup5
if /i "%choice%"=="n" (
set nomsr=1
goto setup5
)
goto unspecifiedMSR
:unspecifiedWRE
echo Please specify a choice.
:setup5
set /p choice="Do you need Recovery partition [Y/N]? "
if /i "%choice%"=="y" goto ready
if /i "%choice%"=="n" (
set nowre=1
goto ready
)
goto unspecifiedWRE
:ready
echo WARNING: All data will be destroyed!
echo Terminate this script now to cancel or
pause
cls
echo Microsoft Windows Setup
echo -----------------------
echo Step 2/3 - Installing Windows
echo.
echo Windows is now being installed. Please wait.
echo DO NOT TERMINATE THIS SCRIPT NOW - THE SYSTEM WILL BE RENDERED UNBOOTABLE!
echo.
echo Partitioning disk...
echo sel dis %drv% >X:\temp.txt
echo cle >>X:\temp.txt
echo con gpt >>X:\temp.txt
echo cre par efi size=512 >>X:\temp.txt
echo for fs=fat32 quick >>X:\temp.txt
echo ass letter w >>X:\temp.txt
if "%nomsr%"=="" echo create partition msr size=16 >>X:\temp.txt
echo cre par pri >>X:\temp.txt
if "%nowre%"=="" echo shrink minimum=700 >>X:\temp.txt
echo for quick >>X:\temp.txt
echo ass letter z >>X:\temp.txt
if "%nowre%"=="" (
echo cre par pri >>X:\temp.txt
echo for fs=ntfs quick >>X:\temp.txt
echo ass letter r >>X:\temp.txt
echo set id="de94bba4-06d1-4d40-a16a-bfd50179d6ac" >>X:\temp.txt
echo gpt attributes=0x8000000000000001 >>X:\temp.txt
)
diskpart /s X:\temp.txt
del X:\temp.txt
echo Applying image...
dism /apply-image /imagefile:%img% /index:%idx% /applydir:Z:\
echo Writing boot files...
bcdboot Z:\Windows /s W:
echo Modifying registry...
reg load "HKLM\SYS" "Z:\Windows\System32\config\SYSTEM"
reg add "HKLM\SYS\Setup" /v "CmdLine" /d "cmd.exe /c OOBE\setup.bat" /f
reg unload "HKLM\SYS"
reg load "HKLM\SOFT" "Z:\Windows\System32\config\SOFTWARE"
reg add "HKLM\SOFT\Policies\Microsoft\Windows\OOBE" /f
reg add "HKLM\SOFT\Policies\Microsoft\Windows\OOBE" /v "DisablePrivacyExperience" /t REG_DWORD /d 1 /f
reg unload "HKLM\SOFT"
echo Creating setup script...
echo @echo OFF >Z:\Windows\System32\OOBE\setup.bat
echo title Microsoft Windows Setup >>Z:\Windows\System32\OOBE\setup.bat
echo echo Microsoft Windows Setup >>Z:\Windows\System32\OOBE\setup.bat
echo echo ----------------------- >>Z:\Windows\System32\OOBE\setup.bat
echo echo Step 3/3 - Configuring Windows >>Z:\Windows\System32\OOBE\setup.bat
echo echo. >>Z:\Windows\System32\OOBE\setup.bat
echo echo Windows is now being configured. Please wait. >>Z:\Windows\System32\OOBE\setup.bat
echo echo DO NOT TERMINATE THIS SCRIPT NOW - THE SYSTEM WILL BE RENDERED UNBOOTABLE! >>Z:\Windows\System32\OOBE\setup.bat
echo echo. >>Z:\Windows\System32\OOBE\setup.bat
echo echo Configuring Windows... >>Z:\Windows\System32\OOBE\setup.bat
echo oobe\windeploy >>Z:\Windows\System32\OOBE\setup.bat
echo echo Creating user... >>Z:\Windows\System32\OOBE\setup.bat
if "%pass%"=="" (
echo net user "%name%" /add >>Z:\Windows\System32\OOBE\setup.bat
) else (
echo net user "%name%" "%pass%" /add >>Z:\Windows\System32\OOBE\setup.bat
)
echo net localgroup Users "%name%" /add >>Z:\Windows\System32\OOBE\setup.bat
echo net localgroup Administrators "%name%" /add >>Z:\Windows\System32\OOBE\setup.bat
echo echo Finalizing setup... >>Z:\Windows\System32\OOBE\setup.bat
echo reg add "HKLM\SYSTEM\Setup" /v "OOBEInProgress" /t REG_DWORD /d 0 /f >>Z:\Windows\System32\OOBE\setup.bat
echo reg add "HKLM\SYSTEM\Setup" /v "SetupType" /t REG_DWORD /d 0 /f >>Z:\Windows\System32\OOBE\setup.bat
echo reg add "HKLM\SYSTEM\Setup" /v "SystemSetupInProgress" /t REG_DWORD /d 0 /f >>Z:\Windows\System32\OOBE\setup.bat
echo schtasks /create /tn DeleteSetupScript /tr "cmd.exe /c del C:\Windows\System32\oobe\setup.bat&schtasks /delete /tn DeleteSetupScript /f" /sc onstart /ru SYSTEM /rl HIGHEST /f >>Z:\Windows\System32\OOBE\setup.bat
echo echo Rebooting... >>Z:\Windows\System32\OOBE\setup.bat
echo shutdown -r -t 0 >>Z:\Windows\System32\OOBE\setup.bat
if "%nowre%"=="" (
echo Preparing Recovery partition...
md R:\Recovery\WindowsRE
xcopy Z:\Windows\System32\Recovery\Winre.wim R:\Recovery\WindowsRE
Z:\Windows\System32\Reagentc /setreimage /path R:\Recovery\WindowsRE /target Z:\Windows
attrib +s +h R:\Recovery\WindowsRE /s /d
)
echo Rebooting...
wpeutil reboot
:help
echo Starts Setup.
echo.
echo SETUP [/^|]
echo SETUP /?
echo     /^| - force to run Setup, even if in Windows OS.
exit /b