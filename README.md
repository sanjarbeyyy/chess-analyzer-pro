# Chess Analyzer Pro

Chess.com'ning "Game Review" bo'limiga o'xshash, lekin **to'liq oflayn** ishlaydigan
shaxmat o'yinlarini tahlil qilish dasturi. Stockfish dvijogi, `python-chess` va
PyQt5 asosida qurilgan.

## Imkoniyatlar

- PGN / FEN yuklash, professional 2D taxta
- Har yurish uchun: engine bahosi, top-3 variant, CP loss, depth
- Chess.com uslubidagi klassifikatsiya: 💎 Brilliant, ⭐ Great, ✅ Best,
  👍 Excellent, ✔ Good, ?! Inaccuracy, ? Mistake, ?? Blunder, ⚠ Missed Win
- Accuracy: umumiy + Opening/Middlegame/Endgame bo'yicha
- Evaluation Graph va Accuracy Graph (pyqtgraph)
- Opening Explorer (debyut va variant aniqlash)
- Endgame Analyzer (King&Pawn/Rook/Queen/Bishop endgame turlari + maslahat)
- AI Sharhlovchi (Stockfish natijalarini oddiy tilga o'giradi)
- PDF hisobot (reportlab)
- O'yinchi profili (SQLite: o'yinlar soni, o'rtacha accuracy, sevimli debyut)
- Turnir tahlili (bir nechta PGN'ni ketma-ket tahlil qilish)

## O'rnatish (Windows)

1. **Python 3.10+ o'rnating**: https://www.python.org/downloads/
   (o'rnatishda "Add Python to PATH" belgisini bosing)

2. **Stockfish yuklab oling**: https://stockfishchess.org/download/
   (Windows uchun `.exe` faylni yuklab, masalan `C:\Stockfish\stockfish.exe`
   ga saqlang)

3. **Kerakli kutubxonalarni o'rnating** (loyiha papkasida, terminal/cmd orqali):

   ```
   pip install -r requirements.txt
   ```

4. **Dasturni ishga tushiring**:

   ```
   python main.py
   ```

5. Birinchi marta ochilganda **Sozlamalar** bo'limidan Stockfish
   faylining to'liq yo'lini ko'rsating (masalan `C:\Stockfish\stockfish.exe`).

## O'rnatish (Linux)

```bash
sudo apt-get install stockfish        # yoki boshqa distributivga mos usul
pip install -r requirements.txt
python main.py
```

Dastur avtomatik ravishda `/usr/games/stockfish`, `/usr/bin/stockfish` kabi
standart joylardan Stockfish'ni topishga harakat qiladi.

## 🚀 ENG OSON YO'L: GitHub Actions orqali avtomatik .exe (Windows kerak emas)

Bu usulda sizga na Windows kompyuter, na qo'lda buyruq kerak — hammasi
GitHub'ning bepul bulut serverida avtomatik bajariladi.

1. **GitHub'da yangi repository yarating** (agar hali yo'q bo'lsa) va shu
   loyiha papkasidagi barcha fayllarni (shu jumladan `.github` papkasini)
   o'sha repo'ga yuklang (push qiling).
2. GitHub'dagi repo sahifasida yuqoridagi **"Actions"** bo'limini oching.
3. Chap tomondan **"Build Windows EXE"** workflow'ini tanlang.
4. O'ng tomondan **"Run workflow"** tugmasini bosing (yashil tugma).
5. ~3-5 daqiqa kuting — jarayon avtomatik: kutubxonalarni o'rnatadi,
   rasmiy Stockfish'ning eng so'nggi Windows versiyasini yuklab oladi,
   `.exe` faylni yig'adi.
6. Tugagach, o'sha run sahifasining pastida **"Artifacts"** bo'limidan
   `ChessAnalyzerPro-windows` arxivini yuklab oling — ichida
   `ChessAnalyzerPro.exe` va `stockfish.exe` tayyor holda bo'ladi.
7. Ikkalasini bir papkaga qo'yib, `ChessAnalyzerPro.exe`ni ishga tushiring.

Bu usul har safar kod o'zgarganda ham (yoki qo'lda "Run workflow" bosilganda)
avtomatik yangi `.exe` yig'ib beradi — Windows kompyuteringiz umuman
bo'lmasa ham.

## Muqobil yo'l: o'z Windows kompyuteringizda yig'ish

Loyihada tayyor `chess_analyzer.spec` va `build.bat` fayllari bor — Linux'da
sinovdan o'tkazilgan (barcha hidden import/hook'lar to'g'ri sozlangan holda).
Windows'da `.exe` olish uchun:

1. Stockfish'ning Windows versiyasini (`stockfish.exe`) yuklab, uni loyiha
   papkasiga (`main.py` bilan bir joyga) qo'ying.
2. `build.bat` faylini ikki marta bosing (yoki `cmd`da `build.bat` deb yozing).
3. Skript avtomatik ravishda: kutubxonalarni o'rnatadi → PyInstaller bilan
   `.exe` ni yig'adi → `stockfish.exe`ni `dist` papkasiga nusxalaydi.
4. Tayyor: `dist\ChessAnalyzerPro.exe` — shu faylni (yoki butun `dist`
   papkasini, Stockfish bilan birga) istalgan Windows kompyuteriga ko'chirib,
   Python o'rnatilmagan bo'lsa ham ishlatish mumkin.

Agar `stockfish.exe`ni dastur bilan bir papkaga qo'ysangiz, dastur uni
avtomatik topadi (Sozlamalar orqali qo'lda ko'rsatish shart emas).

Qo'lda yig'ish (build.bat ishlatmasdan):
```
pip install -r requirements.txt pyinstaller
pyinstaller chess_analyzer.spec --noconfirm
```

## Loyiha strukturasi

```
chess_analyzer/
├── main.py                    - kirish nuqtasi
├── chess_analyzer.spec        - PyInstaller konfiguratsiyasi (.exe yig'ish uchun)
├── build.bat                  - Windows uchun bitta bosishda .exe yig'uvchi skript
├── .github/workflows/build.yml - GitHub Actions: bulutda avtomatik .exe yig'ish
├── engine/
│   ├── stockfish_engine.py    - Stockfish UCI wrapper
│   ├── analyzer.py            - to'liq o'yin tahlili
│   └── classification.py      - yurish klassifikatsiyasi + accuracy formula
├── gui/
│   ├── main_window.py         - asosiy oyna
│   ├── board_widget.py        - 2D taxta
│   ├── analysis_panel.py      - eval bar, top-3, yurishlar ro'yxati
│   └── graph_widget.py        - Evaluation/Accuracy grafiklar
├── reports/
│   └── pdf_report.py          - PDF hisobot generatori
├── database/
│   └── db.py                  - SQLite (profil, o'yinlar tarixi)
└── utils/
    ├── opening_book.py        - debyut aniqlash lug'ati
    ├── endgame_analyzer.py    - endgame turi va maslahat
    └── commentator.py         - AI Sharhlovchi (matn generatori)
```

## Muhim eslatmalar

- **Accuracy va klassifikatsiya formulalari** Chess.com'ning ochiq bo'lmagan
  ichki algoritmiga yaqinlashtirilgan (community tomonidan tan olingan
  win%-asoslangan formulalar). Raqamlar taxminan mos keladi, ammo 100% bir xil
  bo'lishi kafolatlanmaydi.
- **Opening Explorer** hozircha ~40 ta eng mashhur debyut/variantni o'z ichiga
  olgan yengil lug'atga asoslangan (`utils/opening_book.py`). To'liq ECO bazasi
  kerak bo'lsa, shu faylga yozuvlar qo'shishingiz kifoya.
- **Tahlil chuqurligi (Depth)** qancha yuqori bo'lsa, natija shuncha aniq,
  lekin tahlil shuncha sekin bo'ladi. Kuchsizroq kompyuterlar uchun Depth 14-16
  tavsiya etiladi, kuchli kompyuterlar uchun 20+.
- Dastur to'liq **oflayn** ishlaydi — internetga ulanish shart emas (faqat
  Stockfish'ni birinchi marta yuklab olish uchun kerak bo'ladi).
