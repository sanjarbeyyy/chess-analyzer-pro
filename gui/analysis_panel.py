# -*- coding: utf-8 -*-
"""
O'ng paneldagi tahlil bo'limi: joriy yurish bahosi, top-3 variant,
klassifikatsiya belgisi va to'liq yurishlar ro'yxati.
"""
from __future__ import annotations
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QGroupBox, QProgressBar, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from engine.classification import MOVE_CLASS_META


class EvalBar(QWidget):
    """Vertikal baholash paneli (chess.com uslubidagi oq/qora ustunlar nisbati)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(36)
        self.white_pct = 50.0
        self.label = ""

    def set_eval(self, cp: float | None, mate: int | None):
        if mate is not None:
            self.white_pct = 100.0 if mate > 0 else 0.0
            self.label = f"#{abs(mate)}"
        else:
            cp = cp or 0
            from engine.classification import cp_to_win_percent
            self.white_pct = cp_to_win_percent(cp, is_white=True)
            self.label = f"{cp/100:+.1f}"
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter
        painter = QPainter(self)
        h = self.height()
        white_h = int(h * self.white_pct / 100)
        painter.fillRect(0, 0, self.width(), h - white_h, QColor("#2b2b2b"))
        painter.fillRect(0, h - white_h, self.width(), white_h, QColor("#f0f0f0"))
        painter.setPen(QColor("#999"))
        painter.drawText(0, h - 4, self.width(), 14, Qt.AlignHCenter, self.label)


class AnalysisPanel(QWidget):
    move_selected = pyqtSignal(int)  # index in moves list

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.moves = []

    def _build_ui(self):
        root = QHBoxLayout(self)

        self.eval_bar = EvalBar()
        root.addWidget(self.eval_bar)

        right = QVBoxLayout()

        # Klassifikatsiya belgisi
        self.class_label = QLabel("—")
        self.class_label.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        self.class_label.setFont(f)
        right.addWidget(self.class_label)

        # Top-3 variant
        top_box = QGroupBox("Eng yaxshi 3 variant")
        top_layout = QVBoxLayout()
        self.top_line_labels = [QLabel("-") for _ in range(3)]
        for lbl in self.top_line_labels:
            lbl.setWordWrap(True)
            top_layout.addWidget(lbl)
        top_box.setLayout(top_layout)
        right.addWidget(top_box)

        # CP loss / depth info
        info_frame = QFrame()
        info_layout = QHBoxLayout(info_frame)
        self.cp_loss_label = QLabel("CP Loss: -")
        self.depth_label = QLabel("Depth: -")
        info_layout.addWidget(self.cp_loss_label)
        info_layout.addWidget(self.depth_label)
        right.addWidget(info_frame)

        # AI sharh
        self.comment_label = QLabel("")
        self.comment_label.setWordWrap(True)
        self.comment_label.setStyleSheet("color:#bbbbbb; padding:6px;")
        right.addWidget(self.comment_label)

        # Yurishlar ro'yxati
        self.move_list = QListWidget()
        self.move_list.itemClicked.connect(self._on_item_clicked)
        right.addWidget(self.move_list, stretch=1)

        # Accuracy progress
        acc_box = QGroupBox("Accuracy")
        acc_layout = QVBoxLayout()
        self.white_acc_bar = QProgressBar()
        self.white_acc_bar.setFormat("Oq: %p%")
        self.black_acc_bar = QProgressBar()
        self.black_acc_bar.setFormat("Qora: %p%")
        acc_layout.addWidget(self.white_acc_bar)
        acc_layout.addWidget(self.black_acc_bar)
        acc_box.setLayout(acc_layout)
        right.addWidget(acc_box)

        root.addLayout(right, stretch=1)

    def load_moves(self, moves: list):
        self.moves = moves
        self.move_list.clear()
        for i, ma in enumerate(moves):
            label, emoji, color = MOVE_CLASS_META[ma.move_class]
            side = "" if ma.is_white else "..."
            text = f"{ma.move_number}{side} {ma.san}  {emoji}"
            item = QListWidgetItem(text)
            item.setForeground(QColor(color))
            self.move_list.addItem(item)

    def set_game_accuracy(self, white_acc: float, black_acc: float):
        self.white_acc_bar.setValue(int(white_acc))
        self.black_acc_bar.setValue(int(black_acc))

    def show_move(self, index: int):
        if not (0 <= index < len(self.moves)):
            return
        ma = self.moves[index]
        self.eval_bar.set_eval(ma.cp_after, ma.mate_after)

        label, emoji, color = MOVE_CLASS_META[ma.move_class]
        self.class_label.setText(f"{emoji}  {label}")
        self.class_label.setStyleSheet(f"color:{color};")

        for i, top in enumerate(ma.top_lines[:3]):
            self.top_line_labels[i].setText(
                f"{i+1}. {top['move_san']}  ({top['score_text']})  {' '.join(top['pv_san'][:5])}"
            )
        for i in range(len(ma.top_lines), 3):
            self.top_line_labels[i].setText("-")

        self.cp_loss_label.setText(f"CP Loss: {ma.cp_loss:.0f}")
        self.depth_label.setText(f"Depth: {ma.depth}")

        self.move_list.setCurrentRow(index)

        from utils.commentator import comment_for_move
        try:
            self.comment_label.setText(comment_for_move(ma))
        except Exception:
            self.comment_label.setText("")

    def _on_item_clicked(self, item):
        idx = self.move_list.row(item)
        self.move_selected.emit(idx)
