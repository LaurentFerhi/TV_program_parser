@echo on
call C:\ProgramData\Anaconda3\Scripts\activate.bat
python TV_prog.py
start "" "file://%cd:\=/%/Programme.html"