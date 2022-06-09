rem Installation script for Bolt
@echo off

set INSTALLDIR=D:\BOLT
set BOLTDIR=W:\RESSOURCES\romanotools\BOLT

powershell -Command "[Environment]::GetFolderPath('Desktop')" > tmpFile
set /p DESKTOP= < tmpFile
del tmpFile

set DIREXISTED=1==0

if exist %INSTALLDIR% (
    echo Bolt is already installed
    echo Updating Bolt...
    set DIREXISTED=1==1
) else (
    mkdir %INSTALLDIR%
    echo Installing Bolt...
)

rem Copying Bolt 
robocopy %BOLTDIR% %INSTALLDIR% /S /J /Z /MT:%NUMBER_OF_PROCESSORS% /ns /nc /nfl /ndl /njh /njs /np

if %DIREXISTED% (
    echo Bolt has been updated
) else (
    echo Bolt has been installed in %INSTALLDIR%
)

rem Creating the launcher script and placing it on the desktop
echo Making launcher...
set PYTHON=%INSTALLDIR%\Python\python.exe
set BOLT=%INSTALLDIR%\BoltApp\Startup\Launch.py
echo %PYTHON% %BOLT% > %DESKTOP%\Bolt.bat 
echo pause >> %DESKTOP%\Bolt.bat
echo Launcher has been added on your desktop

echo To launch bolt, use the Bolt.bat script that appeared on your desktop
