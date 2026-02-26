@echo off
setlocal
pushd "%~dp0.."
python "stock_tracker.py" run-daily --news-limit 8 --notify >> "%~dp0daily_task.log" 2>&1
if errorlevel 9009 py -3 "stock_tracker.py" run-daily --news-limit 8 --notify >> "%~dp0daily_task.log" 2>&1
popd
endlocal
