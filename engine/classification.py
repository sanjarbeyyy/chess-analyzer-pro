# -*- coding: utf-8 -*-
"""
Yurish klassifikatsiyasi va Accuracy hisoblash moduli.

Chess.com'ning ochiq ma'lum bo'lgan yondashuviga o'xshash mantiq:
  - Har bir pozitsiya oq (yoki qora) uchun "Win %" ga aylantiriladi
    (mashhur logistik formula orqali, centipawn -> win probability).
  - Yurishdan oldingi va keyingi Win % farqi asosida CPL (Centipawn Loss)
    va "Accuracy" hisoblanadi.
  - Yurish turi (Brilliant/Best/Blunder va h.k.) Win% farqi, real CP farqi
    va ba'zi qo'shimcha shartlar (masalan qurbonlik) asosida aniqlanadi.

Bu YAQINLASHTIRISH: Chess.com algoritmi ochiq manba emas, shuning uchun
bu yerda umumiy tan olingan (ochiq loyihalarda - masalan Lichess accuracy
va turli community reverse-engineering ishlarida - qo'llanilgan) formulalar
ishlatiladi. Constants.py orqali koeffitsientlarni sozlash mumkin.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import math
import chess


class MoveClass(Enum):
    BRILLIANT = "brilliant"
    GREAT = "great"
    BEST = "best"
    EXCELLENT = "excellent"
    GOOD = "good"
    BOOK = "book"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"
    MISSED_WIN = "missed_win"


# Har bir klassifikatsiya uchun: (label_uz, belgi/emoji, rang)
MOVE_CLASS_META = {
    MoveClass.BRILLIANT:   ("Brilliant",    "💎", "#26c2a3"),
    MoveClass.GREAT:       ("Great",        "⭐", "#4da2ff"),
    MoveClass.BEST:        ("Best",         "✅", "#4caf50"),
    MoveClass.EXCELLENT:   ("Excellent",    "👍", "#8bc34a"),
    MoveClass.GOOD:        ("Good",         "✔",  "#a0a0a0"),
    MoveClass.BOOK:        ("Book",         "📖", "#9c8b6f"),
    MoveClass.INACCURACY:  ("Inaccuracy",   "?!", "#e6b800"),
    MoveClass.MISTAKE:     ("Mistake",      "?",  "#ff9800"),
    MoveClass.BLUNDER:     ("Blunder",      "??", "#e53935"),
    MoveClass.MISSED_WIN:  ("Missed Win",   "⚠",  "#c62828"),
}


@dataclass
class EvalPoint:
    """Bitta pozitsiyaning tahlil natijasi."""
    cp: float | None       # centipawn (oq nuqtai nazaridan, mate bo'lsa None)
    mate: int | None       # mate bo'lsa necha yurishda (musbat=oq g'alaba)

    def to_white_cp(self) -> float:
        """Mate holatlarini ham katta CP qiymatiga aylantiradi (grafik/hisob uchun)."""
        if self.mate is not None:
            # Mate qancha yaqin bo'lsa, qiymat shuncha katta (cheklangan)
            sign = 1 if self.mate > 0 else -1
            magnitude = max(1, 10000 - abs(self.mate) * 10)
            return sign * magnitude
        return self.cp if self.cp is not None else 0.0


def cp_to_win_percent(cp: float, is_white: bool = True) -> float:
    """
    Centipawn qiymatini "g'alaba ehtimoli %" ga aylantiradi.
    Lichess/chess community tomonidan keng qo'llaniladigan logistik formula:
        Win% = 50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1)
    cp har doim OQ nuqtai nazaridan beriladi deb qabul qilinadi.
    """
    cp = max(min(cp, 3000), -3000)  # ekstremal qiymatlarni cheklash
    win = 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)
    return win if is_white else 100 - win


def winpct_to_accuracy(win_before: float, win_after: float) -> float:
    """
    Bitta yurish accuracy'sini hisoblaydi (0-100).
    Win% pasayishi qancha katta bo'lsa, accuracy shuncha past bo'ladi.
    Formula (community tomonidan reverse-engineer qilingan, lichess'ga yaqin):
        Accuracy = 103.1668 * exp(-0.04354 * (win_before - win_after)) - 3.1668
    """
    diff = max(0.0, win_before - win_after)
    acc = 103.1668 * math.exp(-0.04354 * diff) - 3.1668
    return max(0.0, min(100.0, acc))


def classify_move(
    *,
    cp_before: float,
    cp_after: float,
    is_white: bool,
    played_move: chess.Move,
    best_move: chess.Move,
    board_before: chess.Board,
    is_book: bool = False,
    is_only_good_move: bool = False,
    missed_mate: bool = False,
    top_moves_cp: list[float] | None = None,
) -> MoveClass:
    """
    Yurish turi (Brilliant, Best, Blunder, ...) ni aniqlaydi.

    cp_before / cp_after -- OQ nuqtai nazaridan berilgan baholar (yurishdan
    oldin va keyin), depth yetarlicha chuqur bo'lgan Stockfish tahlilidan.
    """
    if is_book:
        return MoveClass.BOOK

    win_before = cp_to_win_percent(cp_before, is_white=is_white)
    win_after = cp_to_win_percent(cp_after, is_white=is_white)
    win_drop = win_before - win_after  # musbat = yomonlashish

    # Real yutqazilgan yoki topilmagan mat imkoniyati
    if missed_mate:
        return MoveClass.MISSED_WIN

    cp_loss = abs(cp_after - cp_before) if win_drop > 0 else 0

    played_is_best = played_move == best_move

    # --- "Qurbonlik" ni aniqlash (Brilliant uchun zaruriy shart) ---
    is_sacrifice = False
    try:
        captured_piece = board_before.piece_at(played_move.to_square)
        moving_piece = board_before.piece_at(played_move.from_square)
        if moving_piece is not None:
            piece_values = {
                chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0,
            }
            moving_value = piece_values.get(moving_piece.piece_type, 0)
            captured_value = piece_values.get(captured_piece.piece_type, 0) if captured_piece else 0
            # Agar dona qadrliroq donaga almashtirilmasdan xavf ostida qolsa -> qurbonlik belgisi
            board_after = board_before.copy()
            board_after.push(played_move)
            attacked = board_after.is_attacked_by(not board_before.turn, played_move.to_square)
            if attacked and moving_value > captured_value and moving_value >= 3:
                is_sacrifice = True
    except Exception:
        is_sacrifice = False

    # --- Klassifikatsiya qoidalari (eng kuchlidan boshlab tekshiriladi) ---
    if played_is_best and is_sacrifice and win_after >= win_before - 2 and win_after > 50:
        return MoveClass.BRILLIANT

    if played_is_best and is_only_good_move and win_before < 60:
        # Yagona yaxshi yurish bo'lgan, ammo unchalik oshkor bo'lmagan holat
        return MoveClass.GREAT

    if played_is_best:
        return MoveClass.BEST

    if win_drop <= 2:
        return MoveClass.EXCELLENT
    elif win_drop <= 5:
        return MoveClass.GOOD
    elif win_drop <= 10:
        return MoveClass.INACCURACY
    elif win_drop <= 20:
        return MoveClass.MISTAKE
    else:
        return MoveClass.BLUNDER


def game_accuracy(per_move_accuracy: list[float]) -> float:
    """O'yin bo'yicha umumiy accuracy (o'rtacha, oxirgi yurishlar biroz og'irroq)."""
    if not per_move_accuracy:
        return 0.0
    n = len(per_move_accuracy)
    weights = [1.0 + (i / n) * 0.5 for i in range(n)]  # oxiriga borgan sari og'irlik +50%
    total_w = sum(weights)
    weighted = sum(a * w for a, w in zip(per_move_accuracy, weights))
    return round(weighted / total_w, 1)
