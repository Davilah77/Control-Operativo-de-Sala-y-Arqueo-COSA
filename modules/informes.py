from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from core.dates import today_display
from core.settings import reports_directory
from informes_pdf import (
    generar_pdf_arqueo_mensual,
    generar_pdf_limpieza_semanal,
    generar_pdf_recaudacion_mensual,
    generar_pdf_temperaturas_mensual,
    generar_pdf_temperaturas_buffet_semanal,
    generar_pdf_todo_incluido_mensual,
)


MONTHS = [
    "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril", "05 - Mayo", "06 - Junio",
    "07 - Julio", "08 - Agosto", "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre",
]


def build_informes(parent, _app) -> None:
    parent._controller = ReportsModule(parent)


class ReportsModule:
    def __init__(self, parent):
        self.parent = parent
        self._build()

    def _build(self):
        card = ctk.CTkFrame(self.parent)
        card.pack(fill="both", expand=True, padx=25, pady=18)
        ctk.CTkLabel(card, text="Informes y cierre", font=ctk.CTkFont(size=19, weight="bold")).pack(pady=(22, 5))
        self.path_label = ctk.CTkLabel(card, text="", text_color="gray")
        self.path_label.pack(pady=(0, 15))
        self.refresh_output_path()
        selectors = ctk.CTkFrame(card, fg_color="transparent")
        selectors.pack(pady=8)
        ctk.CTkLabel(selectors, text="Mes:").grid(row=0, column=0, padx=6)
        self.month = ctk.CTkOptionMenu(selectors, values=MONTHS, width=150)
        self.month.set(MONTHS[datetime.now().month - 1])
        self.month.grid(row=0, column=1, padx=6)
        ctk.CTkLabel(selectors, text="Año:").grid(row=0, column=2, padx=6)
        years = [str(year) for year in range(datetime.now().year - 2, datetime.now().year + 4)]
        self.year = ctk.CTkOptionMenu(selectors, values=years, width=100)
        self.year.set(str(datetime.now().year))
        self.year.grid(row=0, column=3, padx=6)

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.pack(fill="x", padx=45, pady=20)
        buttons.grid_columnconfigure((0, 1), weight=1)
        reports = (
            ("Recaudación mensual", "recaudacion", generar_pdf_recaudacion_mensual),
            ("Arqueos de caja", "arqueos", generar_pdf_arqueo_mensual),
            ("Temperaturas", "temperaturas", generar_pdf_temperaturas_mensual),
            ("Todo incluido", "todo_incluido", generar_pdf_todo_incluido_mensual),
        )
        for index, (label, slug, function) in enumerate(reports):
            ctk.CTkButton(
                buttons, text=f"Exportar {label}", height=42,
                command=lambda s=slug, f=function: self.export_month(s, f),
            ).grid(row=index // 2, column=index % 2, sticky="ew", padx=8, pady=8)

        week = ctk.CTkFrame(card, fg_color=("gray84", "gray22"))
        week.pack(fill="x", padx=55, pady=12)
        ctk.CTkLabel(week, text="Informes semanales", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=14, pady=12)
        self.week_date = ctk.StringVar(value=today_display())
        ctk.CTkEntry(week, textvariable=self.week_date, width=130).pack(side="left", padx=8)
        ctk.CTkButton(week, text="Limpieza", width=95, command=self.export_cleaning).pack(side="right", padx=(4, 14))
        ctk.CTkButton(week, text="Temp. buffet", width=105, command=self.export_buffet).pack(side="right", padx=4)

    def export_month(self, slug, function):
        month = int(self.month.get().split(" - ")[0])
        year = int(self.year.get())
        filename = reports_directory() / f"{slug}_{year}_{month:02d}.pdf"
        self._run(function, month, year, filename)

    def export_cleaning(self):
        safe_date = self.week_date.get().replace("/", "-")
        filename = reports_directory() / f"limpieza_semana_{safe_date}.pdf"
        self._run(generar_pdf_limpieza_semanal, self.week_date.get(), filename)

    def export_buffet(self):
        safe_date = self.week_date.get().replace("/", "-")
        filename = reports_directory() / f"temperaturas_buffet_semana_{safe_date}.pdf"
        self._run(generar_pdf_temperaturas_buffet_semanal, self.week_date.get(), filename)

    def refresh_output_path(self):
        self.path_label.configure(text=f"Carpeta de destino: {reports_directory()}")

    @staticmethod
    def _run(function, *args):
        try:
            result = function(*args)
            messagebox.showinfo("Informe generado", f"Se ha creado:\n\n{result}")
        except Exception as exc:
            messagebox.showerror("No se pudo generar el informe", str(exc))
