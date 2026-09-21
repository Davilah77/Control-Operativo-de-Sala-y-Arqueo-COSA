from calendar import monthrange
from datetime import timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.database import connect
from core.dates import parse_date, to_display


BLUE = colors.HexColor("#1A365D")
LIGHT_BLUE = colors.HexColor("#E8EEF6")


def _month_rows(conn, sql: str, month: int, year: int):
    rows = conn.execute(sql, (f"{year:04d}-{month:02d}-%", f"%/{month:02d}/{year:04d}")).fetchall()
    return sorted(rows, key=lambda row: parse_date(row["fecha"]))


def _document(path, title, subtitle, *, pagesize=A4, margins=14 * mm):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path), pagesize=pagesize,
        rightMargin=margins, leftMargin=margins, topMargin=margins, bottomMargin=margins,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Heading1"], fontSize=16, leading=20,
        textColor=BLUE, alignment=1, spaceAfter=5,
    )
    story = [Paragraph(title, title_style), Paragraph(subtitle, ParagraphStyle("Subtitle", parent=styles["Normal"], alignment=1, fontSize=10)), Spacer(1, 8)]
    return path, doc, story


def _styled_table(data, widths=None, font_size=8, repeat_rows=1):
    table = Table(data, colWidths=widths, repeatRows=repeat_rows)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def generar_pdf_recaudacion_mensual(mes, anio, archivo_salida):
    path, doc, story = _document(
        archivo_salida, "RECAUDACIÓN - MESA CLARA", f"Periodo: {mes:02d}/{anio}",
        pagesize=A4, margins=12 * mm,
    )
    with connect() as conn:
        rows = _month_rows(conn, "SELECT * FROM recaudacion_diaria WHERE fecha LIKE ? OR fecha LIKE ?", mes, anio)
    headers = ["Día", "Forma", "Venta directa", "D", "A", "C", "Total forma", "Total día", "Menús"]
    data = [headers]
    base_keys = ("efectivo_bodega", "visa_bodega", "credito_habitacion")
    count_keys = (
        "efectivo_desayunos", "efectivo_almuerzos", "efectivo_cenas",
        "visa_desayunos", "visa_almuerzos", "visa_cenas",
        "credito_desayunos", "credito_almuerzos", "credito_cenas",
    )
    price_keys = ("precio_desayuno", "precio_almuerzo", "precio_cena")
    grand_total = 0.0
    grand_menus = 0
    payment_names = ("Efectivo", "VISA", "Crédito")
    for row in rows:
        bases = [row[key] for key in base_keys]
        counts = [int(row[key]) for key in count_keys]
        prices = [row[key] for key in price_keys]
        payment_totals = [
            bases[index] + sum(counts[index * 3 + service] * prices[service] for service in range(3))
            for index in range(3)
        ]
        daily_total = sum(payment_totals)
        daily_menus = sum(counts)
        grand_total += daily_total
        grand_menus += daily_menus
        for index, payment in enumerate(payment_names):
            start = index * 3
            data.append([
                parse_date(row["fecha"]).day, payment, f"{bases[index]:.2f} €",
                *counts[start:start + 3], f"{payment_totals[index]:.2f} €",
                f"{daily_total:.2f} €" if index == 0 else "", daily_menus if index == 0 else "",
            ])
    if not rows:
        data.append(["—", *("—" for _ in range(8))])
    else:
        data.append(["TOTAL", "MES", "", "", "", "", "", f"{grand_total:.2f} €", grand_menus])
    story.append(_styled_table(data, [13 * mm, 22 * mm, 27 * mm, 10 * mm, 10 * mm, 10 * mm, 25 * mm, 27 * mm, 18 * mm], 7.2))
    doc.build(story)
    return str(path)


def generar_pdf_arqueo_mensual(mes, anio, archivo_salida):
    path, doc, story = _document(archivo_salida, "ARQUEOS DE CAJA", f"Periodo: {mes:02d}/{anio}")
    with connect() as conn:
        rows = _month_rows(
            conn,
            """SELECT fecha,total_efectivo,fondo_fijo,almuerzo_efectivo,cena_efectivo,total_visa,total_diario,diferencia
            FROM arqueo_caja WHERE fecha LIKE ? OR fecha LIKE ?""",
            mes, anio,
        )
    data = [["Fecha", "Caja", "Fondo", "Ef. ventas", "VISA", "Total diario"]]
    for row in rows:
        sales = row["almuerzo_efectivo"] + row["cena_efectivo"]
        data.append([to_display(row["fecha"]), *(
            f"{value:.2f} €" for value in (row["total_efectivo"], row["fondo_fijo"], sales, row["total_visa"], row["total_diario"])
        )])
    if not rows:
        data.append(["—"] * 6)
    story.append(_styled_table(data, [30 * mm] + [28 * mm] * 5, 8))
    doc.build(story)
    return str(path)


def generar_pdf_temperaturas_mensual(mes, anio, archivo_salida):
    path, doc, story = _document(
        archivo_salida, "REGISTRO APPCC - TEMPERATURAS DEL LAVAVAJILLAS",
        f"Periodo: {mes:02d}/{anio} - Límites: lavado ≥ 60 °C, aclarado ≥ 82 °C",
        pagesize=A4, margins=10 * mm,
    )
    with connect() as conn:
        rows = _month_rows(
            conn,
            """SELECT fecha,servicio,temp_lavado,temp_aclarado,correcto,observaciones,responsable
            FROM temperaturas_lavavajillas WHERE fecha LIKE ? OR fecha LIKE ?""",
            mes, anio,
        )
    styles = getSampleStyleSheet()
    small = ParagraphStyle("Cell", parent=styles["BodyText"], fontSize=7, leading=8)
    data = [["Fecha", "Servicio", "T. lavado", "T. aclarado", "Estado", "Responsable", "Observaciones / medidas"]]
    for row in rows:
        data.append([
            to_display(row["fecha"]), row["servicio"], f"{row['temp_lavado']:.1f} °C", f"{row['temp_aclarado']:.1f} °C",
            "OK" if row["correcto"] else "INCIDENCIA", row["responsable"] or "—", Paragraph(row["observaciones"] or "—", small),
        ])
    if not rows:
        data.append(["—"] * 7)
    story.append(_styled_table(data, [23 * mm, 22 * mm, 24 * mm, 24 * mm, 23 * mm, 31 * mm, 43 * mm], 7))
    doc.build(story)
    return str(path)


def generar_pdf_todo_incluido_mensual(mes, anio, archivo_salida):
    path, doc, story = _document(
        archivo_salida, "GASTOS DE TODO INCLUIDO", f"Periodo: {mes:02d}/{anio}",
        pagesize=landscape(A3), margins=9 * mm,
    )
    days = monthrange(anio, mes)[1]
    with connect() as conn:
        articles = conn.execute("SELECT id,nombre FROM articulos_todo_incluido WHERE activo=1 ORDER BY orden,nombre").fetchall()
        rows = conn.execute(
            """SELECT articulo_id,fecha,cantidad FROM consumos_todo_incluido
            WHERE fecha LIKE ?""", (f"{anio:04d}-{mes:02d}-%",)
        ).fetchall()
    values = {(row["articulo_id"], parse_date(row["fecha"]).day): row["cantidad"] for row in rows}
    data = [["Artículo", *(str(day) for day in range(1, days + 1)), "Total"]]
    for article in articles:
        daily = [values.get((article["id"], day), 0) for day in range(1, days + 1)]
        data.append([article["nombre"], *daily, sum(daily)])
    story.append(_styled_table(data, [38 * mm] + [9.2 * mm] * days + [13 * mm], 5.8))
    doc.build(story)
    return str(path)


def generar_pdf_limpieza_semanal(fecha_semana, archivo_salida):
    selected = parse_date(fecha_semana)
    monday = selected - timedelta(days=selected.weekday())
    sunday = monday + timedelta(days=6)
    path, doc, story = _document(
        archivo_salida, "REGISTRO DE LIMPIEZA - MESA CLARA",
        f"Semana del {monday:%d/%m/%Y} al {sunday:%d/%m/%Y}", pagesize=landscape(A3),
    )
    dates = [(monday + timedelta(days=index)).isoformat() for index in range(7)]
    with connect() as conn:
        tasks = conn.execute("SELECT id,nombre,turno FROM tareas_limpieza WHERE activo=1 ORDER BY orden,nombre").fetchall()
        placeholders = ",".join("?" for _ in dates)
        assignments = {(row["tarea_id"], row["fecha"]): row["responsable"] for row in conn.execute(
            f"SELECT tarea_id,fecha,responsable FROM asignaciones_limpieza WHERE fecha IN ({placeholders})", dates
        )}
        note = conn.execute("SELECT observaciones FROM notas_limpieza WHERE semana_inicio=?", (monday.isoformat(),)).fetchone()
    headers = ["Zona de limpieza", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "Turno"]
    data = [headers]
    for task in tasks:
        data.append([task["nombre"], *(assignments.get((task["id"], day), "") for day in dates), task["turno"]])
    story.append(_styled_table(data, [57 * mm] + [29 * mm] * 7 + [38 * mm], 7))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Observaciones:</b> {(note['observaciones'] if note else '') or '—'}", getSampleStyleSheet()["BodyText"]))
    doc.build(story)
    return str(path)


def generar_pdf_temperaturas_buffet_semanal(fecha_semana, archivo_salida):
    selected = parse_date(fecha_semana)
    monday = selected - timedelta(days=selected.weekday())
    sunday = monday + timedelta(days=6)
    path, doc, story = _document(
        archivo_salida, "TEMPERATURAS DE ALIMENTOS EXPUESTOS EN EL BUFFET",
        f"Semana del {monday:%d/%m/%Y} al {sunday:%d/%m/%Y} - Caliente: mínimo 65 °C - Frío y postres: máximo 8 °C",
        pagesize=landscape(A3), margins=9 * mm,
    )
    with connect() as conn:
        rows = conn.execute(
            """SELECT * FROM temperaturas_buffet
            WHERE fecha BETWEEN ? AND ? ORDER BY fecha,
            CASE servicio WHEN 'Desayuno' THEN 1 WHEN 'Almuerzo' THEN 2 ELSE 3 END""",
            (monday.isoformat(), sunday.isoformat()),
        ).fetchall()
    headers = [
        "Fecha", "Servicio", "Producto caliente", "T.1", "T.2",
        "Producto frío", "T.1", "T.2", "Postre", "T.1", "T.2",
        "Estado", "Responsable", "Observaciones",
    ]
    data = [headers]
    for row in rows:
        data.append([
            to_display(row["fecha"]), row["servicio"], row["producto_caliente"] or "—",
            "—" if row["caliente_t1"] is None else f"{row['caliente_t1']:.1f}",
            "—" if row["caliente_t2"] is None else f"{row['caliente_t2']:.1f}",
            row["producto_frio"] or "—",
            "—" if row["frio_t1"] is None else f"{row['frio_t1']:.1f}",
            "—" if row["frio_t2"] is None else f"{row['frio_t2']:.1f}",
            row["producto_postre"] or "—",
            "—" if row["postre_t1"] is None else f"{row['postre_t1']:.1f}",
            "—" if row["postre_t2"] is None else f"{row['postre_t2']:.1f}",
            "OK" if row["correcto"] else "INCIDENCIA", row["responsable"] or "—", row["observaciones"] or "—",
        ])
    if not rows:
        data.append(["—"] * len(headers))
    widths = [24 * mm, 22 * mm, 39 * mm, 13 * mm, 13 * mm, 39 * mm, 13 * mm, 13 * mm, 35 * mm, 13 * mm, 13 * mm, 24 * mm, 31 * mm, 55 * mm]
    story.append(_styled_table(data, widths, 6.5))
    doc.build(story)
    return str(path)
