@echo off
setlocal
cd /d "C:\Users\pynbj\OneDrive\1.文档-积累要看的文件\1. 投资框架"
"C:\Users\pynbj\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\Users\pynbj\OneDrive\1.文档-积累要看的文件\1. 投资框架\stock_tracker.py" run-daily --news-limit 8 --notify >> "C:\Users\pynbj\OneDrive\1.文档-积累要看的文件\1. 投资框架\.tmp_idea_test\daily_task.log" 2>&1
endlocal
