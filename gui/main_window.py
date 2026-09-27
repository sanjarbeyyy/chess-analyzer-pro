# -*- coding: utf-8 -*-
"""
Dasturning asosiy oynasi. Barcha bo'limlarni (taxta, tahlil paneli,
grafiklar, PGN yuklash, sozlamalar) birlashtiradi.
"""
from __future__ import annotations
import io
import os
import sys
import traceback

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
    QPushButton, QFileDialog, QLabel, QProgressBar, QMessageBox, QToolBar,
    QAction, QInputDialog, QTableWidget, QTableWidgetItem, QLineEdit,
    QSpinBox, QFormLayout, QDialog, QDialogButtonBox, QPlainTextEdit,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import chess
import chess.pgn

from gui.board_widget import BoardWidget
from gui.analysis_panel import AnalysisPanel
from gui.graph_widget import EvaluationGraphWidget, AccuracyGraphWidget
from engine.stockfish_engine import StockfishEngine
from engine.analyzer import GameAnalyzer, GameAnalysisResult
from utils.endgame_analyzer import classify_endgame_type, theoretical_hint
from utils.commentator import game_summary_comment
from reports.pdf_report import generate_pdf_report
from database.db import Database


class AnalysisWorker(QThread):
    progress = pyqtSignal(int, int)
    finished_ok = pyqtSignal(object)   # GameAnalysisResult
    failed = pyqtSignal(str)

    def __init__(self, game: chess.pgn.Game, engine_path: str | None, depth: int, multipv: int):
        super().__init__()
        self.game = game
        self.engine_path = engine_path
        self.depth = depth
        self.multipv = multipv

    def run(self):
        try:
            with StockfishEngine(path=self.engine_path) as engine:
                analyzer = GameAnalyzer(engine, depth=self.depth, multipv=self.multipv)

                def cb(ply, total, ma):
                    self.progress.emit(ply, total)

                result = analyzer.analyze_game(self.game, progress_cb=cb)
            self.finished_ok.emit(result)
        except Exception as e:
            self.failed.emit(f"{e}\n\n{traceback.format_exc()}")


class SettingsDialog(QDialog):
    def __init__(self, parent, engine_path: str, depth: int, multipv: int):
        super().__init__(parent)
        self.setWindowTitle("Sozlamalar")
        layout = QFormLayout(self)

        self.engine_path_edit = QLineEdit(engine_path or "")
        browse_btn = QPushButton("Tanlash...")
        browse_btn.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.engine_path_edit)
        path_row.addWidget(browse_btn)
        layout.addRow("Stockfish yo'li:", path_row)

        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(4, 40)
        self.depth_spin.setValue(depth)
        layout.addRow("Tahlil chuqurligi (Depth):", self.depth_spin)

        self.multipv_spin = QSpinBox()
        self.multipv_spin.setRange(1, 10)
        self.multipv_spin.setValue(multipv)
        layout.addRow("MultiPV (variantlar soni):", self.multipv_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Stockfish faylini tanlang")
        if path:
            self.engine_path_edit.setText(path)

    def values(self):
        return self.engine_path_edit.text().strip() or None, self.depth_spin.value(), self.multipv_spin.value()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chess Analyzer Pro — Shaxmat O'yinlarini Tahlil Qilish")
        self.resize(1400, 860)

        self.engine_path: str | None = None
        self.depth = 16
        self.multipv = 3

        self.game: chess.pgn.Game | None = None
        self.result: GameAnalysisResult | None = None
        self.board_states: list[chess.Board] = []
        self.current_index = -1  # -1 = boshlang'ich holat

        self.db = Database()

        self._build_ui()
        self._build_toolbar()

    # ---------------------------------------------------------- UI qurish
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        outer.addWidget(self.progress_bar)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter, stretch=1)

        # Chap: taxta + navigatsiya + grafiklar
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.board_widget = BoardWidget()
        self.board_widget.square_clicked.connect(self._on_square_clicked)
        left_layout.addWidget(self.board_widget, stretch=3)

        nav_row = QHBoxLayout()
        self.btn_start = QPushButton("|<")
        self.btn_prev = QPushButton("<")
        self.btn_next = QPushButton(">")
        self.btn_end = QPushButton(">|")
        self.btn_flip = QPushButton("Aylantirish")
        for b, fn in [
            (self.btn_start, self._go_start), (self.btn_prev, self._go_prev),
            (self.btn_next, self._go_next), (self.btn_end, self._go_end),
            (self.btn_flip, self.board_widget.flip),
        ]:
            b.clicked.connect(fn)
            nav_row.addWidget(b)
        left_layout.addLayout(nav_row)

        self.info_label = QLabel("PGN fayl yuklang yoki 'Fayl > PGN yuklash' dan foydalaning.")
        self.info_label.setWordWrap(True)
        left_layout.addWidget(self.info_label)

        self.graph_tabs = QTabWidget()
        self.eval_graph = EvaluationGraphWidget()
        self.acc_graph = AccuracyGraphWidget()
        self.graph_tabs.addTab(self.eval_graph, "Evaluation Graph")
        self.graph_tabs.addTab(self.acc_graph, "Accuracy Graph")
        left_layout.addWidget(self.graph_tabs, stretch=2)

        splitter.addWidget(left)

        # O'ng: tahlil paneli (tablar: Tahlil / Opening / Endgame / Profil / Turnir)
        self.right_tabs = QTabWidget()
        self.analysis_panel = AnalysisPanel()
        self.analysis_panel.move_selected.connect(self._go_to_move)
        self.right_tabs.addTab(self.analysis_panel, "Tahlil")

        self.opening_label = QLabel("Debyut hali aniqlanmadi.")
        self.opening_label.setWordWrap(True)
        self.opening_label.setAlignment(Qt.AlignTop)
        self.right_tabs.addTab(self.opening_label, "Opening Explorer")

        self.endgame_label = QLabel("Endgame hali boshlanmadi.")
        self.endgame_label.setWordWrap(True)
        self.endgame_label.setAlignment(Qt.AlignTop)
        self.right_tabs.addTab(self.endgame_label, "Endgame Analyzer")

        self.profile_widget = self._build_profile_tab()
        self.right_tabs.addTab(self.profile_widget, "O'yinchi Profili")

        self.tournament_widget = self._build_tournament_tab()
        self.right_tabs.addTab(self.tournament_widget, "Turnir Tahlili")

        splitter.addWidget(self.right_tabs)
        splitter.setSizes([850, 550])

    def _build_profile_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.profile_summary_label = QLabel("")
        self.profile_summary_label.setWordWrap(True)
        layout.addWidget(self.profile_summary_label)

        self.games_table = QTableWidget(0, 6)
        self.games_table.setHorizontalHeaderLabels(
            ["ID", "Sana", "Oq", "Qora", "Natija", "Oq/Qora Accuracy"]
        )
        layout.addWidget(self.games_table)

        refresh_btn = QPushButton("Yangilash")
        refresh_btn.clicked.connect(self._refresh_profile)
        layout.addWidget(refresh_btn)
        self._refresh_profile()
        return w

    def _build_tournament_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        info = QLabel(
            "Bir nechta PGN faylni (yoki bitta ko'p-o'yinli PGN faylni) tanlang — "
            "dastur barchasini ketma-ket tahlil qilib, umumiy statistika chiqaradi."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        pick_btn = QPushButton("PGN fayllarni tanlash va tahlil qilish")
        pick_btn.clicked.connect(self._run_tournament_analysis)
        layout.addWidget(pick_btn)

        self.tournament_output = QPlainTextEdit()
        self.tournament_output.setReadOnly(True)
        layout.addWidget(self.tournament_output, stretch=1)
        return w

    def _build_toolbar(self):
        tb = QToolBar()
        self.addToolBar(tb)

        act_load_pgn = QAction("PGN yuklash", self)
        act_load_pgn.triggered.connect(self._load_pgn_dialog)
        tb.addAction(act_load_pgn)

        act_load_fen = QAction("FEN yuklash", self)
        act_load_fen.triggered.connect(self._load_fen_dialog)
        tb.addAction(act_load_fen)

        act_analyze = QAction("Tahlil qilish", self)
        act_analyze.triggered.connect(self._start_analysis)
        tb.addAction(act_analyze)

        act_pdf = QAction("PDF hisobot", self)
        act_pdf.triggered.connect(self._export_pdf)
        tb.addAction(act_pdf)

        act_settings = QAction("Sozlamalar", self)
        act_settings.triggered.connect(self._open_settings)
        tb.addAction(act_settings)

    # ---------------------------------------------------------- PGN/FEN
    def _load_pgn_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "PGN faylni tanlang", "", "PGN files (*.pgn)")
        if not path:
            return
        with open(path, encoding="utf-8", errors="replace") as f:
            game = chess.pgn.read_game(f)
        if game is None:
            QMessageBox.warning(self, "Xato", "PGN fayl o'qib bo'lmadi.")
            return
        self._set_game(game)

    def _load_fen_dialog(self):
        fen, ok = QInputDialog.getText(self, "FEN yuklash", "FEN qatorini kiriting:")
        if not ok or not fen.strip():
            return
        try:
            board = chess.Board(fen.strip())
        except Exception as e:
            QMessageBox.warning(self, "Xato", f"FEN noto'g'ri: {e}")
            return
        game = chess.pgn.Game()
        game.setup(board)
        self._set_game(game)

    def _set_game(self, game: chess.pgn.Game):
        self.game = game
        self.result = None
        board = game.board()
        self.board_states = [board.copy()]
        for move in game.mainline_moves():
            board.push(move)
            self.board_states.append(board.copy())
        self.current_index = 0
        self._render_current_board()
        white = game.headers.get("White", "?")
        black = game.headers.get("Black", "?")
        self.info_label.setText(f"Yuklandi: {white} vs {black} — {len(self.board_states)-1} yurish. "
                                 f"Tahlil qilish uchun 'Tahlil qilish' tugmasini bosing.")

    # ---------------------------------------------------------- Tahlil
    def _open_settings(self):
        dlg = SettingsDialog(self, self.engine_path or "", self.depth, self.multipv)
        if dlg.exec_() == QDialog.Accepted:
            self.engine_path, self.depth, self.multipv = dlg.values()

    def _start_analysis(self):
        if self.game is None:
            QMessageBox.information(self, "Ma'lumot", "Avval PGN yoki FEN yuklang.")
            return
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.worker = AnalysisWorker(self.game, self.engine_path, self.depth, self.multipv)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_analysis_done)
        self.worker.failed.connect(self._on_analysis_failed)
        self.worker.start()

    def _on_progress(self, ply, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(ply)

    def _on_analysis_failed(self, msg: str):
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Tahlil xatosi", msg)

    def _on_analysis_done(self, result: GameAnalysisResult):
        self.progress_bar.setVisible(False)
        self.result = result
        self.analysis_panel.load_moves(result.moves)
        self.analysis_panel.set_game_accuracy(result.white_accuracy, result.black_accuracy)
        self.eval_graph.set_data(result.eval_series, result.moves)
        self.acc_graph.set_data(result.moves)

        self.opening_label.setText(
            f"Aniqlangan debyut:\n\n{result.opening_name or 'Aniqlanmadi'}\n\n"
            + game_summary_comment(result)
        )

        self.current_index = len(self.board_states) - 1
        self._render_current_board()

        # Bazaga saqlash
        pgn_text = str(self.game)
        summary = {
            "white_accuracy": result.white_accuracy,
            "black_accuracy": result.black_accuracy,
            "opening_name": result.opening_name,
            "blunders_white": sum(1 for m in result.blunders if m.is_white),
            "blunders_black": sum(1 for m in result.blunders if not m.is_white),
        }
        try:
            self.db.save_game(result.headers, pgn_text, summary)
            self._refresh_profile()
        except Exception:
            pass

        QMessageBox.information(
            self, "Tayyor",
            f"Tahlil yakunlandi.\nOq accuracy: {result.white_accuracy}%\n"
            f"Qora accuracy: {result.black_accuracy}%"
        )

    # ---------------------------------------------------------- Navigatsiya
    def _render_current_board(self):
        if not self.board_states or self.current_index < 0:
            return
        board = self.board_states[self.current_index]
        last_move = board.peek() if board.move_stack else None
        best_move = None
        if self.result and 0 <= self.current_index - 1 < len(self.result.moves):
            ma = self.result.moves[self.current_index - 1]
            try:
                best_move = chess.Move.from_uci(ma.uci) if ma.move_class.value == "best" else None
            except Exception:
                best_move = None
        self.board_widget.set_board(board, last_move=last_move, best_move=best_move)

        # Endgame tekshiruvi
        etype = classify_endgame_type(board)
        if etype:
            hint = theoretical_hint(board, etype)
            text = f"Endgame turi: {etype}"
            if hint:
                text += f"\n\nMaslahat: {hint}"
            self.endgame_label.setText(text)
        else:
            self.endgame_label.setText("Hali endgame bosqichi emas.")

        if self.result and self.current_index - 1 >= 0:
            self.analysis_panel.show_move(self.current_index - 1)

    def _go_start(self):
        self.current_index = 0
        self._render_current_board()

    def _go_prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._render_current_board()

    def _go_next(self):
        if self.current_index < len(self.board_states) - 1:
            self.current_index += 1
            self._render_current_board()

    def _go_end(self):
        self.current_index = len(self.board_states) - 1
        self._render_current_board()

    def _go_to_move(self, move_idx: int):
        # move_idx -- result.moves ichidagi indeks (0-based); board_states[move_idx+1] ga mos keladi
        self.current_index = move_idx + 1
        self._render_current_board()

    def _on_square_clicked(self, square: int):
        pass  # Kelajakda: qo'lda yurish/variant qo'yish uchun kengaytirilishi mumkin

    # ---------------------------------------------------------- PDF
    def _export_pdf(self):
        if not self.result:
            QMessageBox.information(self, "Ma'lumot", "Avval o'yinni tahlil qiling.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "PDF saqlash", "chess_report.pdf", "PDF files (*.pdf)")
        if not path:
            return
        try:
            from utils.commentator import game_summary_comment
            generate_pdf_report(self.result, path, game_summary_comment(self.result))
            QMessageBox.information(self, "Tayyor", f"PDF hisobot saqlandi:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Xato", f"PDF yaratishda xato: {e}")

    # ---------------------------------------------------------- Profil
    def _refresh_profile(self):
        try:
            summary = self.db.get_profile_summary()
            self.profile_summary_label.setText(
                f"Tahlil qilingan o'yinlar: {summary['games_analyzed']}\n"
                f"O'rtacha Oq Accuracy: {summary['avg_white_accuracy']}%\n"
                f"O'rtacha Qora Accuracy: {summary['avg_black_accuracy']}%\n"
                f"Sevimli debyut: {summary['favorite_opening']}\n"
                f"Jami xatolar (blunder): {summary['total_blunders']}"
            )
            games = self.db.list_games()
            self.games_table.setRowCount(len(games))
            for row, g in enumerate(games):
                values = [g["id"], g["created_at"][:10], g["white"], g["black"],
                          g["result"], f"{g['white_accuracy']}% / {g['black_accuracy']}%"]
                for col, val in enumerate(values):
                    self.games_table.setItem(row, col, QTableWidgetItem(str(val)))
        except Exception:
            pass

    # ---------------------------------------------------------- Turnir
    def _run_tournament_analysis(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "PGN fayllarni tanlang", "", "PGN files (*.pgn)")
        if not paths:
            return
        self.tournament_output.setPlainText("Tahlil boshlandi, iltimos kuting...\n")

        all_games = []
        for p in paths:
            with open(p, encoding="utf-8", errors="replace") as f:
                while True:
                    g = chess.pgn.read_game(f)
                    if g is None:
                        break
                    all_games.append(g)

        if not all_games:
            self.tournament_output.appendPlainText("Hech qanday o'yin topilmadi.")
            return

        results = []
        try:
            with StockfishEngine(path=self.engine_path) as engine:
                analyzer = GameAnalyzer(engine, depth=max(10, self.depth - 4), multipv=1)
                for i, g in enumerate(all_games, start=1):
                    self.tournament_output.appendPlainText(f"[{i}/{len(all_games)}] tahlil qilinmoqda...")
                    from PyQt5.QtWidgets import QApplication
                    QApplication.processEvents()
                    r = analyzer.analyze_game(g)
                    results.append(r)
        except Exception as e:
            self.tournament_output.appendPlainText(f"Xato: {e}")
            return

        total_white = sum(r.white_accuracy for r in results) / len(results)
        total_black = sum(r.black_accuracy for r in results) / len(results)
        opening_counts = {}
        for r in results:
            if r.opening_name:
                opening_counts[r.opening_name] = opening_counts.get(r.opening_name, 0) + 1
        top_opening = max(opening_counts.items(), key=lambda kv: kv[1])[0] if opening_counts else "-"

        phase_totals = {"opening": [], "middlegame": [], "endgame": []}
        for r in results:
            for phase in phase_totals:
                pa = r.phase_accuracy.get(phase, {})
                for side in ("white", "black"):
                    if pa.get(side) is not None:
                        phase_totals[phase].append(pa[side])
        weakest_phase = min(
            phase_totals.items(),
            key=lambda kv: (sum(kv[1]) / len(kv[1])) if kv[1] else 999,
        )[0]

        self.tournament_output.appendPlainText(
            f"\n=== Turnir Natijasi ({len(results)} ta o'yin) ===\n"
            f"Umumiy Oq Accuracy: {total_white:.1f}%\n"
            f"Umumiy Qora Accuracy: {total_black:.1f}%\n"
            f"Eng ko'p o'ynalgan debyut: {top_opening}\n"
            f"Eng zaif bosqich: {weakest_phase}\n"
        )

    def closeEvent(self, event):
        try:
            self.db.close()
        except Exception:
            pass
        super().closeEvent(event)
