# -*- coding: utf-8 -*-
"""
pyqtgraph asosidagi Evaluation Graph va Accuracy Graph widgetlari.
"""
from __future__ import annotations
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSignal
from engine.classification import MoveClass

pg.setConfigOption("background", "#111318")
pg.setConfigOption("foreground", "#d8d8d8")


class EvaluationGraphWidget(QWidget):
    point_clicked = pyqtSignal(int)  # ply index (0-based)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plot = pg.PlotWidget()
        self.plot.setLabel("bottom", "Yarim yurish (ply)")
        self.plot.setLabel("left", "Baholash (pawn)")
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        layout.addWidget(self.plot)
        self._curve = None
        self._scatter_blunders = None
        self._scatter_missed = None

    def set_data(self, eval_series_cp: list[float], moves: list):
        self.plot.clear()
        capped = [max(min(v, 800), -800) / 100 for v in eval_series_cp]
        xs = list(range(1, len(capped) + 1))

        self.plot.addLine(y=0, pen=pg.mkPen("#888", width=1))

        pos_x = xs
        pen = pg.mkPen("#4caf50", width=2)
        self.plot.plot(pos_x, capped, pen=pen)

        blunder_x, blunder_y = [], []
        missed_x, missed_y = [], []
        for i, ma in enumerate(moves):
            if ma.move_class == MoveClass.BLUNDER:
                blunder_x.append(i + 1)
                blunder_y.append(capped[i])
            elif ma.move_class == MoveClass.MISSED_WIN:
                missed_x.append(i + 1)
                missed_y.append(capped[i])

        if blunder_x:
            scatter = pg.ScatterPlotItem(blunder_x, blunder_y, size=10, brush=pg.mkBrush("#e53935"),
                                          symbol="x", pen=pg.mkPen("#e53935"))
            self.plot.addItem(scatter)
        if missed_x:
            scatter2 = pg.ScatterPlotItem(missed_x, missed_y, size=10, brush=pg.mkBrush("#ff9800"),
                                           symbol="t", pen=pg.mkPen("#ff9800"))
            self.plot.addItem(scatter2)


class AccuracyGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plot = pg.PlotWidget()
        self.plot.setLabel("bottom", "Yurish raqami")
        self.plot.setLabel("left", "Accuracy (%)")
        self.plot.setYRange(0, 100)
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        layout.addWidget(self.plot)

    def set_data(self, moves: list):
        self.plot.clear()
        white_x, white_y, black_x, black_y = [], [], [], []
        for i, ma in enumerate(moves):
            if ma.is_white:
                white_x.append(ma.move_number)
                white_y.append(ma.accuracy)
            else:
                black_x.append(ma.move_number)
                black_y.append(ma.accuracy)
        if white_x:
            self.plot.plot(white_x, white_y, pen=pg.mkPen("#eeeeee", width=2), name="Oq")
        if black_x:
            self.plot.plot(black_x, black_y, pen=pg.mkPen("#777777", width=2), name="Qora")
