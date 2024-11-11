@echo OFF
if "%1"=="/?" goto help
:start
cls
echo Microsoft Windows Setup
echo -----------------------
if "%1"=="/^|" goto force
if not exist X:\Windows\System32\wpeutil.exe echo This program cannot run in Windows OS mode.
if not exist X:\Windows\System32\wpeutil.exe echo Setup cannot continue.
if not exist X:\Windows\System32\wpeutil.exe exit /b 2
:force
echo Phase 1/3 - Collecting information
echo.
echo Before installing, please give the following installation information to install Windows.
pause
goto setup1
:notWindowsInstallDisc
echo The selected drive does not appear to be a Windows install disc.
echo Please try again.
:setup1
echo lis vol>X:\temp.txt
diskpart /s X:\temp.txt
del X:\temp.txt
set /p src="Select your source drive letter (for example D): "
%src%:
cd %src%:\sources
if not exist dism.exe goto notWindowsInstallDisc
if not exist dismapi.dll goto notWindowsInstallDisc
if not exist dismcore.dll goto notWindowsInstallDisc
if not exist dismcoreps.dll goto notWindowsInstallDisc
if not exist dismprov.dll goto notWindowsInstallDisc
goto setup2
:imageNotFound
echo The selected install image does not appear to exist.
echo Please try again.
:setup2
set /p img="Select your source image (for example install.wim): "
if not exist %img% goto imageNotFound
dism /get-wiminfo /wimfile:%img%
set /p idx="Select your source image index (for example 6): "
goto setup3
:unspecifiedDrive
echo Please specify a drive number.
:setup3
echo lis dis>X:\temp.txt
diskpart /s X:\temp.txt
del X:\temp.txt
set /p drv="Select your target drive number (for example 0): "
if not defined drv goto unspecifiedDrive
goto setup4
:unspecifiedName
echo Please specify a user name.
:setup4
set /p name="Specify your user name: "
if not defined name goto unspecifiedName
set /p pass="Specify your user password (optional): "
echo WARNING: All data will be destroyed!
echo Close the window now to cancel or
pause
cls
echo Microsoft Windows Setup
echo -----------------------
echo Phase 2/3 - Installing Windows
echo.
echo Windows is now being installed. Please wait.
echo DO NOT TERMINATE THIS SCRIPT NOW - THE SYSTEM WOULD BE RENDERED UNBOOTABLE!
echo.
echo Writing script...
echo sel dis %drv% >X:\temp.txt
echo clean >>X:\temp.txt
echo conv gpt >>X:\temp.txt
echo cre par efi size=512 >>X:\temp.txt
echo form fs=fat32 quick >>X:\temp.txt
echo ass letter w >>X:\temp.txt
echo cre par pri >>X:\temp.txt
echo form quick >>X:\temp.txt
echo ass letter z >>X:\temp.txt
echo Loading script...
diskpart /s X:\temp.txt
del X:\temp.txt
echo Applying image...
dism /apply-image /imagefile:%img% /index:%idx% /applydir:Z:\
echo Writing boot files...
bcdboot Z:\Windows /s W:
echo Editing registry...
reg load "HKLM\SYS" "Z:\Windows\System32\config\SYSTEM"
reg add "HKLM\SYS\Setup" /v "CmdLine" /d "cmd.exe /c OOBE\setup.bat" /f
reg unload "HKLM\SYS"
reg load "HKLM\SOFT" "Z:\Windows\System32\config\SOFTWARE"
reg add "HKLM\SOFT\Policies\Microsoft\Windows\OOBE" /f
reg add "HKLM\SOFT\Policies\Microsoft\Windows\OOBE" /v "DisablePrivacyExperience" /t REG_DWORD /d "1" /f
reg unload "HKLM\SOFT"
echo Writing setup file...
echo @echo OFF >Z:\Windows\System32\OOBE\setup.bat
echo echo Microsoft Windows Setup >>Z:\Windows\System32\OOBE\setup.bat
echo echo ----------------------- >>Z:\Windows\System32\OOBE\setup.bat
echo echo Phase 3/3 - Configuring Windows >>Z:\Windows\System32\OOBE\setup.bat
echo. >>Z:\Windows\System32\OOBE\setup.bat
echo echo Windows is now being configured. Please wait. >>Z:\Windows\System32\OOBE\setup.bat
echo echo DO NOT TERMINATE THIS SCRIPT NOW - THE SYSTEM WOULD BE RENDERED UNBOOTABLE! >>Z:\Windows\System32\OOBE\setup.bat
echo oobe\windeploy >>Z:\Windows\System32\OOBE\setup.bat
if "%pass%"=="" goto nopass
:pass
echo net user "%name%" "%pass%" /add >>Z:\Windows\System32\OOBE\setup.bat
goto passend
:nopass
echo net user "%name%" /add >>Z:\Windows\System32\OOBE\setup.bat
:passend
echo net localgroup Users "%name%" /add >>Z:\Windows\System32\OOBE\setup.bat
echo net localgroup Administrators "%name%" /add >>Z:\Windows\System32\OOBE\setup.bat
echo reg add "HKLM\SYSTEM\Setup" /v "CmdLine" /d "cmd.exe /c OOBE\setup.bat" /f >>Z:\Windows\System32\OOBE\setup.bat
echo reg add "HKLM\SYSTEM\Setup" /v "OOBEInProgress" /t REG_DWORD /d "0" /f >>Z:\Windows\System32\OOBE\setup.bat
echo reg add "HKLM\SYSTEM\Setup" /v "SetupType" /t REG_DWORD /d "0" /f >>Z:\Windows\System32\OOBE\setup.bat
echo reg add "HKLM\SYSTEM\Setup" /v "SystemSetupInProgress" /t REG_DWORD /d "0" /f >>Z:\Windows\System32\OOBE\setup.bat
echo shutdown -r -t 0 >>Z:\Windows\System32\OOBE\setup.bat
echo Rebooting...
wpeutil reboot
:help
echo Installs Windows.
echo.
echo SETUP [/^|]
echo SETUP /?
echo   /^| - force to run Setup, even if in Windows OS
exit /b