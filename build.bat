@echo off
REM ============================================================
REM  Chess Analyzer Pro -- Windows uchun .exe yig'ish skripti
REM  Ishlatish: shu faylni loyiha papkasida ikki marta bosing,
REM  yoki cmd'da "build.bat" deb yozing.
REM ============================================================

echo === 1/4: Python borligini tekshirish ===
python --version
if errorlevel 1 (
    echo XATO: Python topilmadi. Avval https://www.python.org/downloads/ dan
    echo Python 3.10+ ni o'rnating va "Add Python to PATH" ni belgilang.
    pause
    exit /b 1
)

echo.
echo === 2/4: Kerakli kutubxonalarni o'rnatish ===
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo === 3/4: .exe faylni yig'ish (PyInstaller) ===
python -m PyInstaller chess_analyzer.spec --noconfirm

if errorlevel 1 (
    echo XATO: Yig'ish muvaffaqiyatsiz tugadi. Yuqoridagi xato xabarini o'qing.
    pause
    exit /b 1
)

echo.
echo === 4/4: Stockfish faylini nusxalash (agar mavjud bo'lsa) ===
if exist "stockfish.exe" (
    copy /Y "stockfish.exe" "dist\stockfish.exe"
    echo Stockfish nusxalandi -- dist papkasi to'liq tayyor.
) else (
    echo DIQQAT: "stockfish.exe" bu papkada topilmadi.
    echo Uni https://stockfishchess.org/download/ dan yuklab, shu papkaga
    echo qo'ying va build.bat ni qayta ishga tushiring -- yoki dasturni
    echo ishga tushirgach, Sozlamalar bo'limidan Stockfish yo'lini qo'lda
    echo ko'rsating.
)

echo.
echo ============================================================
echo   TAYYOR! Fayl: dist\ChessAnalyzerPro.exe
echo   Butun "dist" papkasini boshqa kompyuterga ko'chirsangiz ham
echo   dastur ishlayveradi.
echo ============================================================
pause
