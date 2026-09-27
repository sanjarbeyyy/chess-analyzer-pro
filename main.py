#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chess Analyzer Pro
==================
Chess.com'ga o'xshash, faqat o'yinlarni tahlil qiladigan oflayn Windows/Linux
dasturi. Stockfish, python-chess va PyQt5 asosida qurilgan.

Ishga tushirish:
    python main.py

Talablar: requirements.txt fayliga qarang. Stockfish alohida o'rnatilgan
bo'lishi kerak (yoki Sozlamalar bo'limida to'g'ridan-to'g'ri .exe/binary
yo'lini ko'rsatishingiz mumkin).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

from gui.main_window import MainWindow


def apply_dark_theme(app: QApplication):
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 32, 38))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(24, 26, 31))
    palette.setColor(QPalette.AlternateBase, QColor(40, 42, 48))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(45, 48, 54))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.Highlight, QColor(76, 130, 219))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)


def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
