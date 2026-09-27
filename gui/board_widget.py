# -*- coding: utf-8 -*-
"""
PyQt5 asosidagi 2D shaxmat taxtasi widget'i.
Unicode shaxmat belgilaridan foydalanadi (tashqi rasm fayllari kerak emas).
"""
from __future__ import annotations
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QFont, QPen
from PyQt5.QtCore import Qt, QRect, pyqtSignal
import chess


LIGHT_SQUARE = QColor("#eeeed2")
DARK_SQUARE = QColor("#769656")
HIGHLIGHT_FROM = QColor(255, 255, 0, 110)
HIGHLIGHT_TO = QColor(255, 165, 0, 110)
BEST_MOVE_COLOR = QColor(30, 144, 255, 140)
COORD_COLOR = QColor(50, 50, 50)

UNICODE_PIECES = {
    (chess.PAWN, chess.WHITE): "♙", (chess.KNIGHT, chess.WHITE): "♘",
    (chess.BISHOP, chess.WHITE): "♗", (chess.ROOK, chess.WHITE): "♖",
    (chess.QUEEN, chess.WHITE): "♕", (chess.KING, chess.WHITE): "♔",
    (chess.PAWN, chess.BLACK): "♟", (chess.KNIGHT, chess.BLACK): "♞",
    (chess.BISHOP, chess.BLACK): "♝", (chess.ROOK, chess.BLACK): "♜",
    (chess.QUEEN, chess.BLACK): "♛", (chess.KING, chess.BLACK): "♚",
}


class BoardWidget(QWidget):
    square_clicked = pyqtSignal(int)  # chess.SQUARE index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.board = chess.Board()
        self.flipped = False
        self.last_move: chess.Move | None = None
        self.best_move: chess.Move | None = None
        self.setMinimumSize(400, 400)

    def set_board(self, board: chess.Board, last_move: chess.Move | None = None,
                  best_move: chess.Move | None = None):
        self.board = board
        self.last_move = last_move
        self.best_move = best_move
        self.update()

    def flip(self):
        self.flipped = not self.flipped
        self.update()

    def _square_size(self) -> float:
        side = min(self.width(), self.height())
        return side / 8

    def _square_rect(self, file_idx: int, rank_idx: int, sq_size: float) -> QRect:
        # rank_idx: 0 = 8-rank (yuqori) agar flipped bo'lmasa
        if not self.flipped:
            col = file_idx
            row = 7 - rank_idx
        else:
            col = 7 - file_idx
            row = rank_idx
        return QRect(int(col * sq_size), int(row * sq_size), int(sq_size) + 1, int(sq_size) + 1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        sq_size = self._square_size()

        for rank in range(8):
            for file in range(8):
                square = chess.square(file, rank)
                is_light = (file + rank) % 2 == 1
                rect = self._square_rect(file, rank, sq_size)
                color = LIGHT_SQUARE if is_light else DARK_SQUARE
                painter.fillRect(rect, color)

                if self.last_move and square in (self.last_move.from_square, self.last_move.to_square):
                    hl = HIGHLIGHT_FROM if square == self.last_move.from_square else HIGHLIGHT_TO
                    painter.fillRect(rect, hl)

                if self.best_move and square == self.best_move.to_square:
                    pen = QPen(BEST_MOVE_COLOR, 3)
                    painter.setPen(pen)
                    painter.drawRect(rect.adjusted(2, 2, -2, -2))

                piece = self.board.piece_at(square)
                if piece:
                    painter.setPen(QColor("#111") if piece.color == chess.WHITE else QColor("#000"))
                    font = QFont("DejaVu Sans", int(sq_size * 0.6))
                    painter.setFont(font)
                    symbol = UNICODE_PIECES[(piece.piece_type, piece.color)]
                    # Oq donalarni konturlash uchun engil soya
                    if piece.color == chess.WHITE:
                        painter.setPen(QColor("#fdfdfd"))
                    else:
                        painter.setPen(QColor("#111111"))
                    painter.drawText(rect, Qt.AlignCenter, symbol)

        # Koordinatalar
        painter.setPen(COORD_COLOR)
        small_font = QFont("Arial", max(8, int(sq_size * 0.18)))
        painter.setFont(small_font)
        files = "abcdefgh" if not self.flipped else "hgfedcba"
        ranks = "87654321" if not self.flipped else "12345678"
        for i, f in enumerate(files):
            painter.drawText(int(i * sq_size + 3), int(8 * sq_size - 3), f)
        for i, r in enumerate(ranks):
            painter.drawText(int(3), int(i * sq_size + 14), r)

    def mousePressEvent(self, event):
        sq_size = self._square_size()
        col = int(event.x() / sq_size)
        row = int(event.y() / sq_size)
        if not (0 <= col < 8 and 0 <= row < 8):
            return
        if not self.flipped:
            file_idx, rank_idx = col, 7 - row
        else:
            file_idx, rank_idx = 7 - col, row
        square = chess.square(file_idx, rank_idx)
        self.square_clicked.emit(square)
