from decimal import Decimal
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.numbers import parse_decimal
from core.settings import app_name, logo_path


BLUE = colors.HexColor("#1A365D")
LIGHT_BLUE = colors.HexColor("#E8EEF6")
GREEN = colors.HexColor("#D7EF78")


def _header_story(title: str, subtitle: str = ""):
    styles = getSampleStyleSheet()
    story = []
    logo = logo_path()
    if logo and logo.is_file():
        story.extend([Image(str(logo), width=18 * mm, height=18 * mm), Spacer(1, 2)])
    story.append(Paragraph(
        escape(app_name()),
        ParagraphStyle("Brand", parent=styles["Heading2"], alignment=1, fontSize=13, textColor=BLUE, spaceAfter=3),
    ))
    story.append(Paragraph(
        escape(title),
        ParagraphStyle("Title", parent=styles["Heading1"], alignment=1, fontSize=16, leading=19, textColor=BLUE, spaceAfter=3),
    ))
    if subtitle:
        story.append(Paragraph(escape(subtitle), ParagraphStyle("Subtitle", parent=styles["Normal"], alignment=1, fontSize=9)))
    story.append(Spacer(1, 7))
    return story


def _inventory_table(rows):
    table = Table(rows, colWidths=[23 * mm, 93 * mm, 25 * mm, 30 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return table


def generar_pdf_inventario(title, catalogue, values, output_path, *, empty=False):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm, topMargin=11 * mm, bottomMargin=11 * mm)
    styles = getSampleStyleSheet()
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading3"], alignment=1, fontSize=10,
        leading=12, textColor=BLUE, spaceBefore=5, spaceAfter=4,
    )
    cell_style = ParagraphStyle("InventoryCell", parent=styles["BodyText"], fontSize=7.5, leading=8.5)
    story = _header_story(title)
    for category_index, (category, items) in enumerate(catalogue):
        story.append(Paragraph(escape(category), section_style))
        rows = [["CÓDIGO", "ARTÍCULO", "CANTIDAD", "UNIDAD"]]
        for item_index, (code, item, unit) in enumerate(items):
            quantity = "" if empty else str(values.get((category_index, item_index), "")).strip()
            rows.append([code, Paragraph(escape(item), cell_style), quantity, unit])
        story.append(_inventory_table(rows))
    doc.build(story)
    return str(path)


def _amount(value) -> Decimal:
    return Decimal("0") if not str(value).strip() else parse_decimal(value)


def _money(value: Decimal) -> str:
    return f"{value:.2f}".replace(".", ",") + " €"


def generar_pdf_botellas(month_name, year, daily_values, output_path, *, empty=False):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=22 * mm, leftMargin=22 * mm, topMargin=11 * mm, bottomMargin=11 * mm)
    story = _header_story("RECAUDACIÓN DE BOTELLAS", f"MES: {month_name.upper()} {year}")
    data = [["DÍA", "EFECTIVO", "VISA", "CRÉDITO", "UD."]]
    totals = [Decimal("0"), Decimal("0"), Decimal("0")]
    total_units = Decimal("0")
    for day in range(1, 32):
        raw = ("", "", "", "") if empty else daily_values.get(day, ("", "", "", ""))
        amounts = [_amount(raw[index]) for index in range(3)]
        units = _amount(raw[3])
        totals = [totals[index] + amounts[index] for index in range(3)]
        total_units += units
        data.append([
            day,
            "" if not str(raw[0]).strip() else _money(amounts[0]),
            "" if not str(raw[1]).strip() else _money(amounts[1]),
            "" if not str(raw[2]).strip() else _money(amounts[2]),
            "" if not str(raw[3]).strip() else str(units.normalize()),
        ])
    data.append(["TOTAL", *(_money(total) for total in totals), str(total_units.normalize())])
    table = Table(data, colWidths=[17 * mm, 38 * mm, 38 * mm, 38 * mm, 20 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#BFC3C7")),
        ("BACKGROUND", (0, -1), (-1, -1), GREEN),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
    ]))
    story.append(table)
    doc.build(story)
    return str(path)
