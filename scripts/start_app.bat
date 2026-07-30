@echo off
REM 启动 MySQL（若未运行）
set MYSQL_BIN=C:\Program Files\MySQL\MySQL Server 8.4\bin
set DATADIR=D:\Dify_agent\storage\mysql\data
tasklist /FI "IMAGENAME eq mysqld.exe" 2>NUL | find /I "mysqld.exe" >NUL
if errorlevel 1 (
  echo Starting MySQL...
  start "" "%MYSQL_BIN%\mysqld.exe" --datadir=%DATADIR% --port=3306 --standalone
  timeout /t 5 /nobreak >NUL
)
cd /d D:\Dify_agent
python app.py
