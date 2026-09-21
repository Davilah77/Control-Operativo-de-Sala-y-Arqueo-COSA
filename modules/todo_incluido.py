from calendar import monthrange
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from core.database import connect, transaction
from core.numbers import parse_decimal


MONTHS = [
    "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril", "05 - Mayo", "06 - Junio",
    "07 - Julio", "08 - Agosto", "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre",
]


def build_todo_incluido(parent, _app) -> None:
    parent._controller = AllInclusiveModule(parent)


class AllInclusiveModule:
    def __init__(self, parent):
        self.parent = parent
        self.entries = {}
        self.day_headers = {}
        self.total_labels = {}
        self._build()
        self.load_month()

    def _build(self):
        toolbar = ctk.CTkFrame(self.parent)
        toolbar.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(toolbar, text="Consumos mensuales de todo incluido", font=ctk.CTkFont(size=17, weight="bold")).pack(side="left", padx=15, pady=12)
        self.month = ctk.CTkOptionMenu(toolbar, values=MONTHS, width=145, command=lambda _value: self.load_month())
        self.month.set(MONTHS[datetime.now().month - 1])
        self.month.pack(side="left", padx=6)
        years = [str(year) for year in range(datetime.now().year - 2, datetime.now().year + 4)]
        self.year = ctk.CTkOptionMenu(toolbar, values=years, width=95, command=lambda _value: self.load_month())
        self.year.set(str(datetime.now().year))
        self.year.pack(side="left", padx=6)
        ctk.CTkButton(toolbar, text="Guardar mes", width=120, command=self.save).pack(side="right", padx=15)

        self.grid_frame = ctk.CTkScrollableFrame(self.parent, orientation="horizontal", fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=10, pady=5)
        ctk.CTkLabel(self.grid_frame, text="Artículo", width=155, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="ew", padx=4, pady=6)
        for day in range(1, 32):
            header = ctk.CTkLabel(self.grid_frame, text=str(day), width=42, font=ctk.CTkFont(weight="bold"), corner_radius=5)
            header.grid(row=0, column=day, padx=1, pady=6)
            self.day_headers[day] = header
        ctk.CTkLabel(
            self.grid_frame, text="Total", width=62, height=28,
            font=ctk.CTkFont(weight="bold"), fg_color=("#B9D7EA", "#1F4E68"),
            text_color=("#102A3A", "white"), corner_radius=5,
        ).grid(row=0, column=32, padx=4)

        with connect() as conn:
            self.articles = conn.execute(
                "SELECT id,nombre FROM articulos_todo_incluido WHERE activo=1 ORDER BY orden,nombre"
            ).fetchall()
        for row_index, article in enumerate(self.articles, start=1):
            ctk.CTkLabel(self.grid_frame, text=article["nombre"], width=155, anchor="w").grid(row=row_index, column=0, sticky="ew", padx=4, pady=3)
            for day in range(1, 32):
                variable = ctk.StringVar(value="")
                entry = ctk.CTkEntry(self.grid_frame, textvariable=variable, width=42, height=28, justify="center")
                entry.grid(row=row_index, column=day, padx=1, pady=2)
                self.entries[(article["id"], day)] = (variable, entry)
            total = ctk.CTkLabel(
                self.grid_frame, text="0", width=62, height=28,
                fg_color=("#D7EBF7", "#245B78"), text_color=("#102A3A", "white"),
                corner_radius=5,
            )
            total.grid(row=row_index, column=32, padx=4)
            self.total_labels[article["id"]] = total

        ctk.CTkLabel(
            self.parent,
            text="Cabecera verde: día completo · ámbar: día parcialmente rellenado · sin color: pendiente. Los días inexistentes quedan bloqueados.",
            text_color="gray",
        ).pack(pady=(0, 8))

    def _period(self):
        return int(self.year.get()), int(self.month.get().split(" - ")[0])

    def load_month(self):
        try:
            year, month = self._period()
            valid_days = monthrange(year, month)[1]
            prefix = f"{year:04d}-{month:02d}-"
            with connect() as conn:
                rows = conn.execute(
                    """SELECT articulo_id,fecha,cantidad FROM consumos_todo_incluido
                    WHERE fecha LIKE ?""", (prefix + "%",)
                ).fetchall()
            values = {(row["articulo_id"], int(row["fecha"][-2:])): row["cantidad"] for row in rows}
            totals = {article["id"]: 0 for article in self.articles}
            saved_per_day = {day: 0 for day in range(1, 32)}
            for (article_id, day), (variable, entry) in self.entries.items():
                entry.configure(state="normal")
                if day > valid_days:
                    variable.set("")
                    entry.configure(state="disabled", fg_color=("gray78", "gray18"))
                    continue
                entry.configure(fg_color=("white", "#343638"))
                if (article_id, day) in values:
                    quantity = values[(article_id, day)]
                    variable.set(str(quantity))
                    totals[article_id] += quantity
                    saved_per_day[day] += 1
                else:
                    variable.set("")
            article_count = len(self.articles)
            for day, header in self.day_headers.items():
                if day > valid_days:
                    header.configure(fg_color=("gray75", "gray18"), text_color="gray")
                elif saved_per_day[day] == article_count:
                    header.configure(fg_color="#2E8B57", text_color="white")
                elif saved_per_day[day] > 0:
                    header.configure(fg_color="#B7791F", text_color="white")
                else:
                    header.configure(fg_color="transparent", text_color=("gray10", "gray90"))
            for article_id, label in self.total_labels.items():
                label.configure(text=str(totals[article_id]))
        except Exception as exc:
            messagebox.showerror("No se pudo cargar el mes", str(exc))

    def save(self):
        try:
            year, month = self._period()
            valid_days = monthrange(year, month)[1]
            prefix = f"{year:04d}-{month:02d}-"
            values = []
            for (article_id, day), (variable, _entry) in self.entries.items():
                if day > valid_days or not variable.get().strip():
                    continue
                number = parse_decimal(variable.get())
                if number != number.to_integral_value():
                    raise ValueError("Las cantidades deben ser números enteros.")
                values.append((f"{prefix}{day:02d}", article_id, int(number)))
            with transaction() as conn:
                conn.execute("DELETE FROM consumos_todo_incluido WHERE fecha LIKE ?", (prefix + "%",))
                conn.executemany(
                    "INSERT INTO consumos_todo_incluido(fecha,articulo_id,cantidad) VALUES (?,?,?)",
                    values,
                )
            messagebox.showinfo("Todo incluido", "El mes se ha guardado correctamente.")
            self.load_month()
        except Exception as exc:
            messagebox.showerror("No se pudo guardar", str(exc))
