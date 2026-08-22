@echo off
REM Scheduled Shopify order sync (see .moai/project/scheduled-jobs.md).
REM Registered in Windows Task Scheduler; do not run two copies at once --
REM the task must be configured with "Do not start a new instance".
setlocal

REM Django reads .env via python-decouple, which searches upward from the
REM working directory -- so this MUST run from the backend directory.
cd /d C:\app\scm_v2\backend || exit /b 1

REM Windows console defaults to cp949 here; without this, any non-ASCII in
REM an error message crashes the run with UnicodeEncodeError before the
REM real error is ever logged.
set PYTHONIOENCODING=utf-8

if not exist "C:\app\scm_v2\logs" mkdir "C:\app\scm_v2\logs"

echo [%DATE% %TIME%] sync_orders start >> "C:\app\scm_v2\logs\sync_orders.log"
"C:\Users\ggajo\AppData\Local\Programs\Python\Python312\python.exe" manage.py sync_orders >> "C:\app\scm_v2\logs\sync_orders.log" 2>&1
set RC=%ERRORLEVEL%
echo [%DATE% %TIME%] sync_orders exit=%RC% >> "C:\app\scm_v2\logs\sync_orders.log"

REM Propagate the exit code so Task Scheduler's "Last Run Result" reflects
REM failures instead of always showing 0x0.
exit /b %RC%
