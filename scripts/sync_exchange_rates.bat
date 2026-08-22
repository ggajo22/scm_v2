@echo off
REM Scheduled USD/KRW exchange-rate sync (see .moai/project/scheduled-jobs.md).
REM Safe to run more than once a day: dates already stored are skipped, and
REM when there is nothing new the command exits 0 without writing.
setlocal

cd /d C:\app\scm_v2\backend || exit /b 1

set PYTHONIOENCODING=utf-8

if not exist "C:\app\scm_v2\logs" mkdir "C:\app\scm_v2\logs"

echo [%DATE% %TIME%] sync_exchange_rates start >> "C:\app\scm_v2\logs\sync_exchange_rates.log"
"C:\Users\ggajo\AppData\Local\Programs\Python\Python312\python.exe" manage.py sync_exchange_rates >> "C:\app\scm_v2\logs\sync_exchange_rates.log" 2>&1
set RC=%ERRORLEVEL%
echo [%DATE% %TIME%] sync_exchange_rates exit=%RC% >> "C:\app\scm_v2\logs\sync_exchange_rates.log"

exit /b %RC%
