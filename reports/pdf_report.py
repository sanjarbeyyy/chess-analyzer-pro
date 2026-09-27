# -*- coding: utf-8 -*-
"""
reportlab yordamida o'yin tahlili bo'yicha PDF hisobot yaratish.
"""
from __future__ import annotations
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)

from engine.classification import MOVE_CLASS_META


def _eval_graph_image(eval_series: list[float], path: str, width_px=900, height_px=300):
    """matplotlib bo'lmasa ham ishlaydigan sodda SVG->PNG grafik (numpy asosida oddiy chizish)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    fig, ax = plt.subplots(figsize=(width_px / 100, height_px / 100), dpi=100)
    capped = [max(min(v, 800), -800) for v in eval_series]
    ax.plot(range(1, len(capped) + 1), [v / 100 for v in capped], color="#2e7d32", linewidth=1.5)
    ax.axhline(0, color="#888", linewidth=0.8)
    ax.fill_between(range(1, len(capped) + 1), [v / 100 for v in capped], 0,
                     where=[v >= 0 for v in capped], color="#e8f5e9", alpha=0.6)
    ax.fill_between(range(1, len(capped) + 1), [v / 100 for v in capped], 0,
                     where=[v < 0 for v in capped], color="#ffebee", alpha=0.6)
    ax.set_xlabel("Yarim yurish (ply)")
    ax.set_ylabel("Baholash (pawn)")
    ax.set_title("Evaluation Graph")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def generate_pdf_report(result, output_path: str, game_summary_text: str = ""):
    """
    result -- engine.analyzer.GameAnalysisResult
    output_path -- yaratiladigan PDF fayl yo'li
    """
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleUZ", parent=styles["Title"], fontSize=20)
    h2_style = ParagraphStyle("H2UZ", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    normal = styles["Normal"]

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                             leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                             topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    story = []

    white = result.headers.get("White", "Oq")
    black = result.headers.get("Black", "Qora")
    game_result = result.headers.get("Result", "*")

    story.append(Paragraph("Shaxmat O'yini Tahlil Hisoboti", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>{white}</b> vs <b>{black}</b> &nbsp;&nbsp; Natija: {game_result}", normal))
    if result.opening_name:
        story.append(Paragraph(f"Debyut: {result.opening_name}", normal))
    story.append(Spacer(1, 14))

    # --- Accuracy jadvali ---
    story.append(Paragraph("Accuracy", h2_style))
    acc_data = [["", "Oq", "Qora"],
                ["Umumiy", f"{result.white_accuracy}%", f"{result.black_accuracy}%"]]
    for phase_key, phase_label in [("opening", "Debyut"), ("middlegame", "O'rta o'yin"), ("endgame", "Endshpil")]:
        pa = result.phase_accuracy.get(phase_key, {})
        acc_data.append([
            phase_label,
            f"{pa.get('white')}%" if pa.get("white") is not None else "-",
            f"{pa.get('black')}%" if pa.get("black") is not None else "-",
        ])
    acc_table = Table(acc_data, colWidths=[6 * cm, 5 * cm, 5 * cm])
    acc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(acc_table)
    story.append(Spacer(1, 14))

    # --- Xatolar ro'yxati ---
    story.append(Paragraph("Asosiy Xatolar (Blunder / Missed Win)", h2_style))
    if result.blunders or result.missed_wins:
        err_data = [["Yurish", "Notatsiya", "Turi", "Eng yaxshi yurish"]]
        combined = sorted(result.blunders + result.missed_wins, key=lambda m: m.ply)
        for ma in combined:
            label, emoji, _ = MOVE_CLASS_META[ma.move_class]
            err_data.append([
                f"{ma.move_number}.{'..' if not ma.is_white else ''}",
                ma.san,
                f"{emoji} {label}",
                ma.best_move_san,
            ])
        err_table = Table(err_data, colWidths=[2.5 * cm, 3 * cm, 4.5 * cm, 6 * cm])
        err_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(err_table)
    else:
        story.append(Paragraph("Jiddiy xatolar aniqlanmadi — barqaror o'yin.", normal))
    story.append(Spacer(1, 14))

    # --- Evaluation grafigi (agar matplotlib mavjud bo'lsa) ---
    graph_path = output_path + "_eval_graph.png"
    if result.eval_series:
        made = _eval_graph_image(result.eval_series, graph_path)
        if made and os.path.exists(made):
            story.append(Paragraph("Evaluation Graph", h2_style))
            story.append(Image(made, width=16 * cm, height=16 * cm * 300 / 900))
            story.append(Spacer(1, 14))

    # --- Umumiy AI sharh ---
    if game_summary_text:
        story.append(Paragraph("AI Sharhlovchi Xulosasi", h2_style))
        story.append(Paragraph(game_summary_text, normal))
        story.append(Spacer(1, 14))

    # --- Har yurish uchun to'liq jadval (yangi sahifada) ---
    story.append(PageBreak())
    story.append(Paragraph("Har Yurish Bo'yicha Tafsilotlar", h2_style))
    move_data = [["#", "Yurish", "Baho (oldin→keyin)", "Turi", "CP Loss", "Eng yaxshi"]]
    for ma in result.moves:
        label, emoji, _ = MOVE_CLASS_META[ma.move_class]
        before_txt = f"{(ma.cp_before or 0)/100:+.2f}" if ma.mate_before is None else f"#{ma.mate_before}"
        after_txt = f"{(ma.cp_after or 0)/100:+.2f}" if ma.mate_after is None else f"#{ma.mate_after}"
        move_data.append([
            f"{ma.move_number}{'.' if ma.is_white else '...'}",
            ma.san,
            f"{before_txt} → {after_txt}",
            f"{emoji} {label}",
            f"{ma.cp_loss:.0f}",
            ma.best_move_san,
        ])
    move_table = Table(move_data, colWidths=[1.5 * cm, 2.3 * cm, 3.7 * cm, 3.7 * cm, 2 * cm, 3.3 * cm], repeatRows=1)
    move_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
    ]))
    story.append(move_table)

    doc.build(story)
    return output_path
