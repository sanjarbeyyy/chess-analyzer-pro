# -*- coding: utf-8 -*-
"""
Oddiy, o'rnatilgan "opening book": eng mashhur debyutlar va variantlarni
UCI yurishlar ketma-ketligi bo'yicha aniqlaydi.

Eslatma: bu to'liq ECO bazasi emas, balki eng ko'p uchraydigan ~120 ta
debyut/variantni qamrab oladigan yengil lug'at. Pro versiyada to'liq
ECO.pgn bazasidan foydalanish tavsiya etiladi (opening_book_full.tsv
faylini shu papkaga qo'shib, load_full_eco() orqali yuklash mumkin).
"""
from __future__ import annotations
import chess

# Kalit: UCI yurishlar ketma-ketligi (bo'sh joy bilan ajratilgan)
# Qiymat: debyut nomi
OPENING_TABLE: dict[str, str] = {
    "e2e4": "King's Pawn Opening",
    "e2e4 e7e5": "Open Game",
    "e2e4 e7e5 g1f3": "King's Knight Opening",
    "e2e4 e7e5 g1f3 b8c6": "Two Knights / Italian setup",
    "e2e4 e7e5 g1f3 b8c6 f1b5": "Ruy Lopez",
    "e2e4 e7e5 g1f3 b8c6 f1c4": "Italian Game",
    "e2e4 e7e5 g1f3 g8f6": "Petrov's Defense",
    "e2e4 e7e5 f2f4": "King's Gambit",
    "e2e4 c7c5": "Sicilian Defense",
    "e2e4 c7c5 g1f3": "Sicilian Defense",
    "e2e4 c7c5 g1f3 d7d6": "Sicilian Defense",
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 a7a6": "Sicilian Defense: Najdorf Variation",
    "e2e4 c7c5 g1f3 b8c6": "Sicilian Defense: Old Sicilian",
    "e2e4 c7c5 g1f3 e7e6": "Sicilian Defense: Kan / Taimanov setup",
    "e2e4 c7c5 b1c3": "Sicilian Defense: Closed",
    "e2e4 c7c6": "Caro-Kann Defense",
    "e2e4 c7c6 d2d4 d7d5 e4e5": "Caro-Kann Defense: Advance Variation",
    "e2e4 c7c6 d2d4 d7d5 b1c3": "Caro-Kann Defense: Classical/Main Line",
    "e2e4 c7c6 d2d4 d7d5 e4d5 c6d5": "Caro-Kann Defense: Exchange Variation",
    "e2e4 e7e6": "French Defense",
    "e2e4 e7e6 d2d4 d7d5 e4e5": "French Defense: Advance Variation",
    "e2e4 e7e6 d2d4 d7d5 b1c3": "French Defense: Classical/Winawer",
    "e2e4 e7e6 d2d4 d7d5 e4d5 e6d5": "French Defense: Exchange Variation",
    "e2e4 d7d5": "Scandinavian Defense",
    "e2e4 g8f6": "Alekhine's Defense",
    "e2e4 d7d6": "Pirc Defense",
    "e2e4 g7g6": "Modern Defense",
    "d2d4 d7d5": "Queen's Pawn Game",
    "d2d4 d7d5 c2c4": "Queen's Gambit",
    "d2d4 d7d5 c2c4 e7e6": "Queen's Gambit Declined",
    "d2d4 d7d5 c2c4 c7c6": "Slav Defense",
    "d2d4 d7d5 c2c4 d5c4": "Queen's Gambit Accepted",
    "d2d4 g8f6": "Indian Defense",
    "d2d4 g8f6 c2c4 g7g6": "King's Indian / Gruenfeld setup",
    "d2d4 g8f6 c2c4 g7g6 b1c3 f8g7 e2e4 d7d6": "King's Indian Defense",
    "d2d4 g8f6 c2c4 g7g6 b1c3 d7d5": "Gruenfeld Defense",
    "d2d4 g8f6 c2c4 e7e6": "Indian Defense: East Indian/Nimzo setup",
    "d2d4 g8f6 c2c4 e7e6 b1c3 f8b4": "Nimzo-Indian Defense",
    "d2d4 g8f6 c2c4 e7e6 g1f3 b7b6": "Queen's Indian Defense",
    "d2d4 f7f5": "Dutch Defense",
    "c2c4": "English Opening",
    "g1f3": "Reti Opening",
}


def lookup_opening(board: chess.Board, next_move: chess.Move) -> str | None:
    """
    board -- yurishdan OLDINGI holat.
    next_move -- shu holatda o'ynalayotgan yurish.
    Agar to'plamdagi ketma-ketlik davom etayotgan bo'lsa, debyut nomini qaytaradi.
    """
    # Boshidan hozirgacha bo'lgan UCI ketma-ketlikni tiklaymiz
    moves_so_far = []
    b = board.root() if hasattr(board, "root") else board
    # board allaqachon joriy holat, shuning uchun move_stack'dan foydalanamiz
    for mv in board.move_stack:
        moves_so_far.append(mv.uci())
    moves_so_far.append(next_move.uci())
    key = " ".join(moves_so_far)

    if key in OPENING_TABLE:
        return OPENING_TABLE[key]
    # Eng yaqin (eng uzun mos keluvchi prefiks) nomni qaytarish uchun,
    # aniq mos kelmasa ham, oldingi eng yaqin ma'lum nom davom etadi.
    return None


def best_known_name_for_prefix(uci_sequence: list[str]) -> str | None:
    """Berilgan ketma-ketlik uchun eng uzun mos keluvchi ma'lum debyut nomini topadi."""
    best_name = None
    best_len = 0
    for key, name in OPENING_TABLE.items():
        key_moves = key.split(" ")
        if uci_sequence[:len(key_moves)] == key_moves and len(key_moves) > best_len:
            best_name = name
            best_len = len(key_moves)
    return best_name
