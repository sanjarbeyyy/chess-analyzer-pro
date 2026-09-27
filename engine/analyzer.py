# -*- coding: utf-8 -*-
"""
To'liq o'yin tahlili: PGN/board -> har yurish uchun eval, top-3, klassifikatsiya,
CP loss, va umumiy accuracy.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import chess
import chess.pgn

from .stockfish_engine import StockfishEngine, LineInfo
from .classification import (
    MoveClass, classify_move, cp_to_win_percent, winpct_to_accuracy, game_accuracy,
)
from utils.opening_book import lookup_opening


@dataclass
class MoveAnalysis:
    ply: int                       # 1,2,3,... (yarim yurish raqami)
    move_number: int               # to'liq yurish raqami (1.,2.,...)
    is_white: bool
    san: str                       # "Nf3" kabi
    uci: str
    cp_before: float | None
    cp_after: float | None
    mate_before: int | None
    mate_after: int | None
    best_move_san: str
    best_line_san: list[str]
    top_lines: list[dict]          # [{move, score_text, pv_san}, ...] (top-3)
    move_class: MoveClass
    cp_loss: float
    accuracy: float
    depth: int
    fen_before: str
    fen_after: str
    is_book: bool = False


@dataclass
class GameAnalysisResult:
    headers: dict
    moves: list[MoveAnalysis] = field(default_factory=list)
    white_accuracy: float = 0.0
    black_accuracy: float = 0.0
    phase_accuracy: dict = field(default_factory=dict)  # {"opening":{"white":..,"black":..}, ...}
    opening_name: str = ""
    eval_series: list[float] = field(default_factory=list)   # har ply uchun CP (oq nuqtai nazaridan)
    blunders: list[MoveAnalysis] = field(default_factory=list)
    missed_wins: list[MoveAnalysis] = field(default_factory=list)


OPENING_PLY_LIMIT = 20     # ~10 to'liq yurish
ENDGAME_PIECE_THRESHOLD = 12  # taxtada shuncha yoki kamroq dona qolsa endgame


def _phase_for_ply(ply: int, board: chess.Board) -> str:
    if ply <= OPENING_PLY_LIMIT:
        return "opening"
    piece_count = len(board.piece_map())
    if piece_count <= ENDGAME_PIECE_THRESHOLD:
        return "endgame"
    return "middlegame"


class GameAnalyzer:
    def __init__(self, engine: StockfishEngine, depth: int = 18, multipv: int = 3):
        self.engine = engine
        self.depth = depth
        self.multipv = multipv

    def analyze_game(self, game: chess.pgn.Game, progress_cb=None) -> GameAnalysisResult:
        board = game.board()
        result = GameAnalysisResult(headers=dict(game.headers))

        moves = list(game.mainline_moves())
        total = len(moves)

        prev_cp = 0.0
        prev_mate = None

        white_accs: list[float] = []
        black_accs: list[float] = []
        phase_accs = {
            "opening": {"white": [], "black": []},
            "middlegame": {"white": [], "black": []},
            "endgame": {"white": [], "black": []},
        }

        book_hit_so_far = True

        for ply, move in enumerate(moves, start=1):
            is_white = board.turn == chess.WHITE
            fen_before = board.fen()

            # --- Kitob (opening) tekshiruvi ---
            is_book = False
            if book_hit_so_far:
                opening_match = lookup_opening(board, move)
                if opening_match:
                    is_book = True
                    if not result.opening_name:
                        result.opening_name = opening_match
                else:
                    book_hit_so_far = False

            # --- Yurishdan oldingi tahlil (top-N) ---
            lines_before = self.engine.analyse_position(board, depth=self.depth, multipv=self.multipv)
            if not lines_before:
                board.push(move)
                continue

            best_line = lines_before[0]
            cp_before = best_line.cp if best_line.mate is None else None
            mate_before = best_line.mate

            top_lines_payload = []
            for ln in lines_before:
                pv_san = []
                tmp_board = board.copy()
                for pv_mv in ln.pv[:6]:
                    try:
                        pv_san.append(tmp_board.san(pv_mv))
                        tmp_board.push(pv_mv)
                    except Exception:
                        break
                top_lines_payload.append({
                    "move_san": board.san(ln.move),
                    "score_text": ln.score_text,
                    "pv_san": pv_san,
                })

            san = board.san(move)
            board.push(move)
            fen_after = board.fen()

            # --- Yurishdan keyingi baho ---
            delivered_checkmate = board.is_checkmate()
            if board.is_game_over():
                if delivered_checkmate:
                    # Yurishni o'ynagan tomon mat qo'ydi -- bu eng yaxshi natija,
                    # "yo'qotilgan" hech narsa yo'q.
                    cp_after = 100000 if is_white else -100000
                    mate_after = 1 if is_white else -1
                else:
                    cp_after, mate_after = 0.0, None  # pat/durang
            else:
                after_lines = self.engine.analyse_position(board, depth=self.depth, multipv=1)
                if after_lines:
                    cp_after = after_lines[0].cp
                    mate_after = after_lines[0].mate
                else:
                    cp_after, mate_after = 0.0, None

            cp_before_val = cp_before if cp_before is not None else (100000 if (mate_before or 0) > 0 else -100000)
            cp_after_val = cp_after if cp_after is not None else (100000 if (mate_after or 0) > 0 else -100000)

            if delivered_checkmate:
                missed_mate = False
            else:
                missed_mate = (mate_before is not None and mate_before != 0 and
                               ((mate_before > 0) == is_white) and
                               (mate_after is None or abs(mate_after) > abs(mate_before) + 1 or
                                ((mate_after or 0) > 0) != ((mate_before or 0) > 0)))

            move_class = classify_move(
                cp_before=cp_before_val,
                cp_after=cp_after_val,
                is_white=is_white,
                played_move=move,
                best_move=best_line.move,
                board_before=chess.Board(fen_before),
                is_book=is_book,
                missed_mate=missed_mate,
            )

            win_before = cp_to_win_percent(cp_before_val, is_white=is_white)
            win_after = cp_to_win_percent(cp_after_val, is_white=is_white)
            move_accuracy = winpct_to_accuracy(win_before, win_after)
            cp_loss = max(0.0, (cp_before_val - cp_after_val) if is_white else (cp_after_val - cp_before_val))

            move_number = (ply + 1) // 2
            board_for_phase = chess.Board(fen_after)
            phase = _phase_for_ply(ply, board_for_phase)

            ma = MoveAnalysis(
                ply=ply,
                move_number=move_number,
                is_white=is_white,
                san=san,
                uci=move.uci(),
                cp_before=cp_before,
                cp_after=cp_after,
                mate_before=mate_before,
                mate_after=mate_after,
                best_move_san=top_lines_payload[0]["move_san"] if top_lines_payload else san,
                best_line_san=top_lines_payload[0]["pv_san"] if top_lines_payload else [],
                top_lines=top_lines_payload,
                move_class=move_class,
                cp_loss=round(cp_loss, 1),
                accuracy=round(move_accuracy, 1),
                depth=best_line.depth,
                fen_before=fen_before,
                fen_after=fen_after,
                is_book=is_book,
            )
            result.moves.append(ma)
            result.eval_series.append(cp_after_val if mate_after is None else (100000 if mate_after > 0 else -100000))

            if not is_book:
                if is_white:
                    white_accs.append(move_accuracy)
                else:
                    black_accs.append(move_accuracy)
                side = "white" if is_white else "black"
                phase_accs[phase][side].append(move_accuracy)

            if move_class == MoveClass.BLUNDER:
                result.blunders.append(ma)
            if move_class == MoveClass.MISSED_WIN:
                result.missed_wins.append(ma)

            if progress_cb:
                progress_cb(ply, total, ma)

        result.white_accuracy = game_accuracy(white_accs)
        result.black_accuracy = game_accuracy(black_accs)
        for phase in phase_accs:
            result.phase_accuracy[phase] = {
                "white": round(sum(phase_accs[phase]["white"]) / len(phase_accs[phase]["white"]), 1)
                if phase_accs[phase]["white"] else None,
                "black": round(sum(phase_accs[phase]["black"]) / len(phase_accs[phase]["black"]), 1)
                if phase_accs[phase]["black"] else None,
            }
        return result
