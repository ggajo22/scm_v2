@echo off
REM Weekly full reconciliation of order cancellation/closure state (SPEC-ORDER-029).
REM
REM The 5-minute detection job (sync_order_cancellations) only looks at orders
REM closed within the last 30 days. An order closed longer ago that is cancelled
REM afterwards falls outside that window -- re-running the unbounded backfill is
REM the only path that absorbs it (spec.md section 8, C5). Measured frequency of
REM that ordering is 1 in 1,170 cancellations, but it is permanent when it hits.
REM
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

echo [%DATE% %TIME%] backfill_order_cancellations start >> "C:\app\scm_v2\logs\backfill_order_cancellations.log"
"C:\Users\ggajo\AppData\Local\Programs\Python\Python312\python.exe" manage.py backfill_order_cancellations >> "C:\app\scm_v2\logs\backfill_order_cancellations.log" 2>&1
set RC=%ERRORLEVEL%
echo [%DATE% %TIME%] backfill_order_cancellations exit=%RC% >> "C:\app\scm_v2\logs\backfill_order_cancellations.log"

REM Propagate the exit code so Task Scheduler's "Last Run Result" reflects
REM failures instead of always showing 0x0.
exit /b %RC%
