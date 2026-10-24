@echo off
REM Tu build tren may Windows (can Python 3.12): bam dup file nay
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm VeMongBan.spec
echo.
echo Xong: dist\VeMongBan.exe
pause
