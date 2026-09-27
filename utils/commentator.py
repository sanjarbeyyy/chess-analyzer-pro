# -*- coding: utf-8 -*-
"""
Stockfish natijalarini oddiy, tushunarli o'zbek tiliga o'giruvchi
"AI Sharhlovchi" moduli. Bu shablon-asosidagi generator (LLM chaqirmaydi),
lekin xohlasangiz api-based izohlash bilan almashtirish mumkin
(masalan Anthropic API orqali, agar ilova internetga ulangan bo'lsa).
"""
from __future__ import annotations
from engine.classification import MoveClass


CLASS_PHRASES = {
    MoveClass.BRILLIANT: "ajoyib, kutilmagan qurbonlik bilan pozitsiyani mustahkamladi",
    MoveClass.GREAT: "qiyin pozitsiyada yagona to'g'ri yo'lni topdi",
    MoveClass.BEST: "eng kuchli yurishni o'ynadi",
    MoveClass.EXCELLENT: "juda aniq yurish, deyarli eng yaxshisiga teng",
    MoveClass.GOOD: "yaxshi, ammo eng aniq yurish emas edi",
    MoveClass.BOOK: "ma'lum debyut nazariyasiga mos yurish",
    MoveClass.INACCURACY: "kichik noaniqlikka yo'l qo'ydi",
    MoveClass.MISTAKE: "xatoga yo'l qo'ydi va ustunlikning bir qismini yo'qotdi",
    MoveClass.BLUNDER: "jiddiy xatoga yo'l qo'ydi va pozitsiyani keskin yomonlashtirdi",
    MoveClass.MISSED_WIN: "g'alaba keltiruvchi imkoniyatni qo'ldan boy berdi",
}


def format_eval(cp: float | None, mate: int | None) -> str:
    if mate is not None:
        return f"mat {mate} yurishda"
    if cp is None:
        return "0.00"
    return f"{cp / 100:+.2f}"


def comment_for_move(ma) -> str:
    """
    ma -- engine.analyzer.MoveAnalysis obyekti.
    Oddiy tilga o'girilgan izoh matnini qaytaradi.
    """
    side = "Oq" if ma.is_white else "Qora"
    phrase = CLASS_PHRASES.get(ma.move_class, "yurish o'ynadi")

    text = f"{ma.move_number}-{'oq' if ma.is_white else 'qora'} yurish: {ma.san} — {side} {phrase}."

    if ma.move_class in (MoveClass.MISTAKE, MoveClass.BLUNDER, MoveClass.INACCURACY, MoveClass.MISSED_WIN):
        eval_before = format_eval(ma.cp_before, ma.mate_before)
        eval_after = format_eval(ma.cp_after, ma.mate_after)
        text += (
            f" Baholash {eval_before} dan {eval_after} ga o'zgardi. "
            f"Engine {ma.best_move_san} yurishini tavsiya qilmoqda"
        )
        if ma.best_line_san:
            text += f" (variant: {' '.join(ma.best_line_san[:4])})"
        text += "."

    if ma.move_class == MoveClass.BRILLIANT:
        text += " Bu yurish chuqur hisob-kitob va aniqlik talab qilgan."

    return text


def game_summary_comment(result) -> str:
    """Butun o'yin uchun qisqa umumiy sharh."""
    lines = []
    lines.append(
        f"O'yin natijasi: Oq accuracy {result.white_accuracy}%, "
        f"Qora accuracy {result.black_accuracy}%."
    )
    if result.opening_name:
        lines.append(f"O'ynalgan debyut: {result.opening_name}.")
    if result.blunders:
        lines.append(f"O'yin davomida {len(result.blunders)} ta jiddiy xato (blunder) aniqlandi.")
    if result.missed_wins:
        lines.append(f"{len(result.missed_wins)} ta g'alaba imkoniyati qo'ldan boy berildi.")
    if not result.blunders and not result.missed_wins:
        lines.append("Ikkala tomon ham nisbatan barqaror va aniq o'ynadi.")
    return " ".join(lines)
