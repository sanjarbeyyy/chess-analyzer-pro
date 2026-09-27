# -*- coding: utf-8 -*-
"""
SQLite ma'lumotlar bazasi: tahlil qilingan o'yinlar tarixi va
o'yinchi profili statistikasi.
"""
from __future__ import annotations
import sqlite3
import json
import os
from datetime import datetime


DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".chess_analyzer", "data.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    white TEXT,
    black TEXT,
    result TEXT,
    opening TEXT,
    white_accuracy REAL,
    black_accuracy REAL,
    blunders_white INTEGER DEFAULT 0,
    blunders_black INTEGER DEFAULT 0,
    pgn TEXT,
    analysis_json TEXT
);

CREATE TABLE IF NOT EXISTS profile_stats (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    games_analyzed INTEGER DEFAULT 0,
    total_white_accuracy REAL DEFAULT 0,
    total_black_accuracy REAL DEFAULT 0,
    favorite_opening TEXT
);
"""


class Database:
    def __init__(self, path: str = DEFAULT_DB_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)
        self.conn.execute(
            "INSERT OR IGNORE INTO profile_stats (id, games_analyzed) VALUES (1, 0)"
        )
        self.conn.commit()

    def save_game(self, headers: dict, pgn_text: str, analysis_summary: dict) -> int:
        cur = self.conn.execute(
            """INSERT INTO games
               (created_at, white, black, result, opening, white_accuracy, black_accuracy,
                blunders_white, blunders_black, pgn, analysis_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.utcnow().isoformat(),
                headers.get("White", "?"),
                headers.get("Black", "?"),
                headers.get("Result", "*"),
                analysis_summary.get("opening_name", ""),
                analysis_summary.get("white_accuracy", 0),
                analysis_summary.get("black_accuracy", 0),
                analysis_summary.get("blunders_white", 0),
                analysis_summary.get("blunders_black", 0),
                pgn_text,
                json.dumps(analysis_summary, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        self._update_profile(analysis_summary)
        return cur.lastrowid

    def _update_profile(self, summary: dict):
        row = self.conn.execute(
            "SELECT games_analyzed, total_white_accuracy, total_black_accuracy FROM profile_stats WHERE id=1"
        ).fetchone()
        games_analyzed, total_white, total_black = row
        games_analyzed += 1
        total_white += summary.get("white_accuracy", 0)
        total_black += summary.get("black_accuracy", 0)
        self.conn.execute(
            """UPDATE profile_stats
               SET games_analyzed=?, total_white_accuracy=?, total_black_accuracy=?
               WHERE id=1""",
            (games_analyzed, total_white, total_black),
        )
        self.conn.commit()

    def get_profile_summary(self) -> dict:
        row = self.conn.execute(
            "SELECT games_analyzed, total_white_accuracy, total_black_accuracy FROM profile_stats WHERE id=1"
        ).fetchone()
        games_analyzed, total_white, total_black = row
        avg_white = round(total_white / games_analyzed, 1) if games_analyzed else 0
        avg_black = round(total_black / games_analyzed, 1) if games_analyzed else 0

        opening_row = self.conn.execute(
            """SELECT opening, COUNT(*) c FROM games
               WHERE opening IS NOT NULL AND opening != ''
               GROUP BY opening ORDER BY c DESC LIMIT 1"""
        ).fetchone()
        favorite_opening = opening_row[0] if opening_row else "-"

        blunder_row = self.conn.execute(
            "SELECT SUM(blunders_white) + SUM(blunders_black) FROM games"
        ).fetchone()
        total_blunders = blunder_row[0] or 0

        return {
            "games_analyzed": games_analyzed,
            "avg_white_accuracy": avg_white,
            "avg_black_accuracy": avg_black,
            "favorite_opening": favorite_opening,
            "total_blunders": total_blunders,
        }

    def list_games(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            """SELECT id, created_at, white, black, result, opening,
                      white_accuracy, black_accuracy
               FROM games ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        cols = ["id", "created_at", "white", "black", "result", "opening",
                "white_accuracy", "black_accuracy"]
        return [dict(zip(cols, r)) for r in rows]

    def get_game(self, game_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT pgn, analysis_json FROM games WHERE id=?", (game_id,)
        ).fetchone()
        if not row:
            return None
        return {"pgn": row[0], "analysis": json.loads(row[1])}

    def close(self):
        self.conn.close()
