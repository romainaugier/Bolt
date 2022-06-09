@echo off

rem Script to update Bolt on W:/ and Z:/ servers

set BOLTDIR=D:\dev\Bolt
set WDIR=W:\RESSOURCES\romanotools\BOLT
set ZDIR=Z:\OEUF\BOLT\Bolt

echo Updating %WDIR%

robocopy %BOLTDIR% %WDIR% /S /J /Z /MT:%NUMBER_OF_PROCESSORS% /ns /nc /nfl /ndl /njh /njs /np /XD "Tests" "Colors" "__pycache__" ".git" /XF .gitignore UPDATE.bat

echo Updating %ZDIR%

robocopy %BOLTDIR% %ZDIR% /S /J /Z /MT:%NUMBER_OF_PROCESSORS% /ns /nc /nfl /ndl /njh /njs /np /XD "Tests" "Colors" "__pycache__" ".git" /XF .gitignore UPDATE.bat

