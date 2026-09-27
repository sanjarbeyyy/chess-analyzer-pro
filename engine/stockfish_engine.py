# -*- coding: utf-8 -*-
"""
Stockfish UCI dvijogi bilan ishlash uchun wrapper.
python-chess kutubxonasining chess.engine modulidan foydalanadi.
"""
from __future__ import annotations
import shutil
import sys
import chess
import chess.engine
from dataclasses import dataclass


DEFAULT_CANDIDATE_PATHS = [
    "/usr/games/stockfish",
    "/usr/bin/stockfish",
    "/usr/local/bin/stockfish",
    "stockfish",
    "stockfish.exe",
]


def find_stockfish_path(custom_path: str | None = None) -> str:
    """Stockfish binary joylashgan yo'lni topadi."""
    import os

    if custom_path and shutil.which(custom_path):
        return custom_path
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    # PyInstaller bilan .exe qilib yig'ilganda, .exe fayli bilan bir papkada
    # joylashgan stockfish.exe / stockfish ni ham qidiramiz.
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        for name in ("stockfish.exe", "stockfish"):
            candidate = os.path.join(exe_dir, name)
            if os.path.isfile(candidate):
                return candidate

    for p in DEFAULT_CANDIDATE_PATHS:
        found = shutil.which(p)
        if found:
            return found
        if os.path.isfile(p):
            return p

    raise FileNotFoundError(
        "Stockfish topilmadi. Iltimos, Stockfish 18 ni yuklab, "
        ".exe fayli bilan bir papkaga joylashtiring, yoki "
        "Sozlamalar bo'limida uning to'liq yo'lini ko'rsating."
    )


@dataclass
class LineInfo:
    """Bitta variant (PV) haqida ma'lumot."""
    move: chess.Move
    cp: float | None      # OQ nuqtai nazaridan
    mate: int | None
    pv: list[chess.Move]
    depth: int

    @property
    def score_text(self) -> str:
        if self.mate is not None:
            return f"#{self.mate}"
        if self.cp is not None:
            return f"{self.cp / 100:+.2f}"
        return "0.00"


class StockfishEngine:
    """Bitta Stockfish jarayonini boshqaruvchi klass."""

    def __init__(self, path: str | None = None, threads: int = 2, hash_mb: int = 256):
        self.path = find_stockfish_path(path)
        self.engine = chess.engine.SimpleEngine.popen_uci(self.path)
        try:
            self.engine.configure({"Threads": threads, "Hash": hash_mb})
        except Exception:
            pass  # ba'zi buildlar bu optsiyalarni qo'llamasligi mumkin

    def analyse_position(
        self, board: chess.Board, depth: int = 18, multipv: int = 3, time_limit: float | None = None
    ) -> list[LineInfo]:
        """Berilgan pozitsiyani tahlil qilib, top-N variantni qaytaradi."""
        limit = chess.engine.Limit(depth=depth, time=time_limit)
        infos = self.engine.analyse(board, limit, multipv=multipv)
        if isinstance(infos, dict):
            infos = [infos]

        results: list[LineInfo] = []
        for info in infos:
            pv = info.get("pv", [])
            if not pv:
                continue
            score = info["score"].white()  # har doim OQ nuqtai nazaridan
            cp = score.score(mate_score=100000)
            mate = score.mate()
            results.append(
                LineInfo(
                    move=pv[0],
                    cp=None if mate is not None else cp,
                    mate=mate,
                    pv=list(pv),
                    depth=info.get("depth", depth),
                )
            )
        return results

    def best_move_and_eval(self, board: chess.Board, depth: int = 18) -> LineInfo:
        lines = self.analyse_position(board, depth=depth, multipv=1)
        if not lines:
            raise RuntimeError("Stockfish natija qaytarmadi (pozitsiya tugagan bo'lishi mumkin).")
        return lines[0]

    def close(self):
        try:
            self.engine.quit()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
