from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from core.settings import reports_directory
from inventario_pdf import generar_pdf_botellas, generar_pdf_inventario
from modules.inventario_data import BODEGA, DESAYUNOS


MONTHS = [
    "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril", "05 - Mayo", "06 - Junio",
    "07 - Julio", "08 - Agosto", "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre",
]
FORM_TYPES = ("Inventario de bodega", "Inventario de desayunos", "Recaudación de botellas")


def build_inventario(parent, _app) -> None:
    parent._controller = InventoryModule(parent)


class InventoryModule:
    def __init__(self, parent):
        self.parent = parent
        self.entries = {}
        self._build()

    def _build(self):
        toolbar = ctk.CTkFrame(self.parent)
        toolbar.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(toolbar, text="Plantillas de inventario", font=ctk.CTkFont(size=17, weight="bold")).pack(side="left", padx=15, pady=12)
        self.form_type = ctk.CTkOptionMenu(toolbar, values=list(FORM_TYPES), width=205, command=lambda _value: self._render_form())
        self.form_type.set(FORM_TYPES[0])
        self.form_type.pack(side="left", padx=8)
        ctk.CTkButton(toolbar, text="Exportar vacío", width=115, fg_color="#606A73", command=lambda: self.export(True)).pack(side="right", padx=(5, 15))
        ctk.CTkButton(toolbar, text="Exportar datos", width=120, command=lambda: self.export(False)).pack(side="right", padx=5)

        self.form = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        self.form.pack(fill="both", expand=True, padx=12, pady=(5, 10))
        self._render_form()

    def _clear_form(self):
        for widget in self.form.winfo_children():
            widget.destroy()
        self.entries = {}

    def _render_form(self):
        self._clear_form()
        selected = self.form_type.get()
        if selected == FORM_TYPES[2]:
            self._render_bottles()
        else:
            catalogue = BODEGA if selected == FORM_TYPES[0] else DESAYUNOS
            self._render_inventory(catalogue)

    def _render_inventory(self, catalogue):
        self.form.grid_columnconfigure(1, weight=1)
        headers = ("Código", "Artículo", "Cantidad", "Unidad")
        for column, label in enumerate(headers):
            ctk.CTkLabel(self.form, text=label, font=ctk.CTkFont(weight="bold"), anchor="w").grid(row=0, column=column, sticky="ew", padx=5, pady=(4, 8))
        row = 1
        for category_index, (category, items) in enumerate(catalogue):
            ctk.CTkLabel(
                self.form, text=category, font=ctk.CTkFont(weight="bold"),
                fg_color=("#DCE6F1", "#263C52"), corner_radius=5,
            ).grid(row=row, column=0, columnspan=4, sticky="ew", padx=3, pady=(9, 4), ipady=4)
            row += 1
            for item_index, (code, item, unit) in enumerate(items):
                ctk.CTkLabel(self.form, text=code or "—", width=90).grid(row=row, column=0, padx=5, pady=2)
                ctk.CTkLabel(self.form, text=item, anchor="w").grid(row=row, column=1, sticky="ew", padx=5, pady=2)
                variable = ctk.StringVar(value="")
                ctk.CTkEntry(self.form, textvariable=variable, width=105, justify="center").grid(row=row, column=2, padx=5, pady=2)
                ctk.CTkLabel(self.form, text=unit, width=95, anchor="w").grid(row=row, column=3, padx=5, pady=2)
                self.entries[(category_index, item_index)] = variable
                row += 1

    def _render_bottles(self):
        period = ctk.CTkFrame(self.form, fg_color="transparent")
        period.pack(pady=(4, 12))
        ctk.CTkLabel(period, text="Mes:").pack(side="left", padx=5)
        self.month = ctk.CTkOptionMenu(period, values=MONTHS, width=155)
        self.month.set(MONTHS[datetime.now().month - 1])
        self.month.pack(side="left", padx=5)
        ctk.CTkLabel(period, text="Año:").pack(side="left", padx=(15, 5))
        years = [str(year) for year in range(datetime.now().year - 2, datetime.now().year + 4)]
        self.year = ctk.CTkOptionMenu(period, values=years, width=95)
        self.year.set(str(datetime.now().year))
        self.year.pack(side="left", padx=5)

        grid = ctk.CTkFrame(self.form, fg_color="transparent")
        grid.pack(fill="x", padx=25)
        grid.grid_columnconfigure((1, 2, 3), weight=1)
        for column, label in enumerate(("Día", "Efectivo", "VISA", "Crédito", "Unidades")):
            ctk.CTkLabel(grid, text=label, font=ctk.CTkFont(weight="bold")).grid(row=0, column=column, sticky="ew", padx=4, pady=5)
        for day in range(1, 32):
            ctk.CTkLabel(grid, text=str(day), width=45).grid(row=day, column=0, padx=4, pady=2)
            variables = []
            for column in range(1, 5):
                variable = ctk.StringVar(value="")
                ctk.CTkEntry(grid, textvariable=variable, justify="center", width=125).grid(row=day, column=column, sticky="ew", padx=4, pady=2)
                variables.append(variable)
            self.entries[day] = variables

    def export(self, empty):
        try:
            output_directory = reports_directory()
            output_directory.mkdir(parents=True, exist_ok=True)
            selected = self.form_type.get()
            suffix = "_vacio" if empty else ""
            if selected == FORM_TYPES[2]:
                month_number, month_name = self.month.get().split(" - ", 1)
                year = int(self.year.get())
                values = {day: tuple(variable.get() for variable in variables) for day, variables in self.entries.items()}
                path = output_directory / f"recaudacion_botellas_{year}_{month_number}{suffix}.pdf"
                result = generar_pdf_botellas(month_name, year, values, path, empty=empty)
            else:
                is_warehouse = selected == FORM_TYPES[0]
                catalogue = BODEGA if is_warehouse else DESAYUNOS
                slug = "inventario_bodega" if is_warehouse else "inventario_desayunos"
                title = "INVENTARIO DE BODEGA" if is_warehouse else "INVENTARIO DE DESAYUNOS Y VARIOS"
                values = {key: variable.get() for key, variable in self.entries.items()}
                path = output_directory / f"{slug}{suffix}.pdf"
                result = generar_pdf_inventario(title, catalogue, values, path, empty=empty)
            messagebox.showinfo("Inventario", f"Se ha creado:\n\n{result}")
        except Exception as exc:
            messagebox.showerror("No se pudo exportar", str(exc))
