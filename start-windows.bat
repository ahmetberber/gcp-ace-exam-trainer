@echo off
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 main.py & exit /b)
where pythonw >nul 2>nul && (start "" pythonw main.py & exit /b)
echo Python bulunamadi. https://www.python.org/downloads/ adresinden Python 3.10+ kurun
echo (kurulumda "Add python.exe to PATH" secenegini isaretleyin) ve tekrar deneyin.
pause
