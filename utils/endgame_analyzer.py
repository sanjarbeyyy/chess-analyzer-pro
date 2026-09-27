# -*- coding: utf-8 -*-
"""
Endgame turini aniqlash va oddiy nazariy maslahat berish moduli.
To'liq tablebase (Syzygy) ulanmagan holatda ishlaydigan, dona tarkibiga
asoslangan evristik tahlil.
"""
from __future__ import annotations
import chess


def classify_endgame_type(board: chess.Board) -> str | None:
    """Taxtadagi donalar tarkibiga qarab endgame turini aniqlaydi."""
    piece_map = board.piece_map()
    total_non_king = sum(1 for p in piece_map.values() if p.piece_type != chess.KING)
    if total_non_king > 14:
        return None  # hali endgame emas

    types_present = set(p.piece_type for p in piece_map.values() if p.piece_type != chess.KING)

    if types_present <= {chess.PAWN}:
        return "King and Pawn Endgame"
    if types_present <= {chess.ROOK, chess.PAWN}:
        return "Rook Endgame"
    if types_present <= {chess.QUEEN, chess.PAWN}:
        return "Queen Endgame"
    if types_present <= {chess.BISHOP, chess.PAWN}:
        # Ikkala tomonda har xil rangdagi fillar bo'lsa alohida ta'kidlanadi
        bishops = [sq for sq, p in piece_map.items() if p.piece_type == chess.BISHOP]
        if len(bishops) == 2:
            colors = {chess.square_color(sq) for sq in bishops}
            if len(colors) == 2:
                return "Bishop Endgame (Opposite-Colored Bishops)"
        return "Bishop Endgame"
    if types_present <= {chess.KNIGHT, chess.PAWN}:
        return "Knight Endgame"
    if chess.ROOK in types_present and chess.BISHOP in types_present and chess.KNIGHT not in types_present and chess.QUEEN not in types_present:
        return "Rook + Minor Piece Endgame"
    return "Mixed / Complex Endgame"


def theoretical_hint(board: chess.Board, endgame_type: str) -> str | None:
    """Ba'zi keng tarqalgan holatlar uchun oddiy nazariy maslahat."""
    piece_map = board.piece_map()
    pawns = [sq for sq, p in piece_map.items() if p.piece_type == chess.PAWN]

    if endgame_type == "King and Pawn Endgame" and len(pawns) == 1:
        pawn_sq = pawns[0]
        pawn_color = piece_map[pawn_sq].color
        king_sq = board.king(pawn_color)
        enemy_king_sq = board.king(not pawn_color)
        # Oddiy "kvadrat qoidasi" evristikasi (aniq emas, faqat taxminiy signal)
        file_diff = abs(chess.square_file(pawn_sq) - chess.square_file(enemy_king_sq))
        rank_diff = abs(chess.square_rank(pawn_sq) - chess.square_rank(enemy_king_sq))
        if max(file_diff, rank_diff) <= 1:
            return "Bu pozitsiyada raqib shohi piyodani ushlab qolish 'kvadrati' ichida — ehtimol durang."
        return "Piyoda mustaqil o'tishi mumkinmi yoki yordamchi shoh kerakmi, tekshirib ko'ring."

    if "Rook Endgame" in endgame_type:
        return "Ladya endgamelarida faollik ko'pincha material ustunlikdan muhimroq — ladyani faol pozitsiyaga qo'ying."

    if "Opposite-Colored Bishops" in endgame_type:
        return "Har xil rangli fillar durangga moyil — hatto piyoda ustunligi bo'lsa ham ehtiyot bo'ling."

    if endgame_type == "Queen Endgame":
        return "Ferzli endgamelarda shohning xavfsizligi va abadiy shax imkoniyatlariga e'tibor bering."

    return None
