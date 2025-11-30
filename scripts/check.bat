@echo off
REM Wrapper для запуска check.py на Windows

cd /d %~dp0\..
python scripts\check.py %*
