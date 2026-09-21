from decimal import Decimal
from tkinter import messagebox

import customtkinter as ctk

from core.database import connect, transaction
from core.dates import to_display, to_iso, today_display
from core.numbers import format_money, money, parse_decimal


SERVICES = ("desayunos", "almuerzos", "cenas")
PAYMENTS = (
    ("efectivo", "Efectivo", "efectivo_bodega", "Bodega (€)"),
    ("visa", "VISA", "visa_bodega", "Bodega (€)"),
    ("credito", "Crédito", "credito_habitacion", "Habitación (€)"),
)


def build_recaudacion(parent, _app) -> None:
    parent._controller = RevenueModule(parent)


class RevenueModule:
    def __init__(self, parent):
        self.parent = parent
        self.base_vars = {}
        self.count_vars = {}
        self.price_vars = {}
        self._build()
        self._load_latest_prices()
        self.calculate()
        self.refresh()

    def _build(self):
        root = ctk.CTkFrame(self.parent, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=8, pady=8)
        root.grid_columnconfigure(0, weight=3)
        root.grid_columnconfigure(1, weight=2)
        root.grid_rowconfigure(0, weight=1)

        form_card = ctk.CTkScrollableFrame(root)
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ctk.CTkLabel(form_card, text="Recaudación diaria", font=ctk.CTkFont(size=17, weight="bold")).pack(pady=(8, 12))
        date_row = ctk.CTkFrame(form_card, fg_color="transparent")
        date_row.pack(fill="x", padx=18)
        ctk.CTkLabel(date_row, text="Fecha:").pack(side="left")
        self.date_var = ctk.StringVar(value=today_display())
        ctk.CTkEntry(date_row, textvariable=self.date_var, width=135).pack(side="right")

        prices = ctk.CTkFrame(form_card, fg_color=("gray84", "gray22"))
        prices.pack(fill="x", padx=18, pady=12)
        ctk.CTkLabel(prices, text="Precios de los servicios", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, pady=(9, 5))
        defaults = ("12.00", "25.00", "25.00")
        labels = ("Desayuno", "Almuerzo", "Cena")
        for column, (service, label, default) in enumerate(zip(SERVICES, labels, defaults)):
            ctk.CTkLabel(prices, text=label).grid(row=1, column=column, padx=8)
            variable = ctk.StringVar(value=default)
            variable.trace_add("write", lambda *_: self.calculate())
            ctk.CTkEntry(prices, textvariable=variable, width=105, justify="center").grid(row=2, column=column, padx=8, pady=(2, 10))
            self.price_vars[service] = variable
            prices.grid_columnconfigure(column, weight=1)

        matrix = ctk.CTkFrame(form_card, fg_color="transparent")
        matrix.pack(fill="x", padx=18, pady=6)
        for column, text in enumerate(("Forma de pago", "Venta directa", "D", "A", "C")):
            ctk.CTkLabel(matrix, text=text, font=ctk.CTkFont(weight="bold")).grid(row=0, column=column, padx=4, pady=6)
        for row_index, (prefix, label, base_key, base_label) in enumerate(PAYMENTS, start=1):
            ctk.CTkLabel(matrix, text=label, anchor="w", width=85).grid(row=row_index, column=0, padx=4, pady=5, sticky="w")
            base_var = ctk.StringVar(value="0.00")
            base_var.trace_add("write", lambda *_: self.calculate())
            self.base_vars[base_key] = base_var
            ctk.CTkEntry(matrix, textvariable=base_var, width=115, placeholder_text=base_label).grid(row=row_index, column=1, padx=4, pady=5)
            for service_index, service in enumerate(SERVICES, start=2):
                variable = ctk.StringVar(value="0")
                variable.trace_add("write", lambda *_: self.calculate())
                self.count_vars[f"{prefix}_{service}"] = variable
                ctk.CTkEntry(matrix, textvariable=variable, width=62, justify="center").grid(row=row_index, column=service_index, padx=4, pady=5)

        ctk.CTkLabel(
            form_card, text="D = desayuno · A = almuerzo · C = cena",
            text_color="gray",
        ).pack(pady=(3, 8))
        self.notes = ctk.CTkEntry(form_card, placeholder_text="Observaciones opcionales")
        self.notes.pack(fill="x", padx=18, pady=6)
        self.total_label = ctk.CTkLabel(form_card, text="Total del día: 0.00 €", font=ctk.CTkFont(size=16, weight="bold"))
        self.total_label.pack(pady=(12, 2))
        self.menu_count_label = ctk.CTkLabel(form_card, text="Menús vendidos: 0", text_color="gray")
        self.menu_count_label.pack(pady=(0, 10))
        ctk.CTkButton(form_card, text="Guardar o actualizar el día", command=self.save).pack(fill="x", padx=18, pady=(4, 12))

        history_card = ctk.CTkFrame(root)
        history_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(history_card, text="Últimos registros", font=ctk.CTkFont(size=17, weight="bold")).pack(pady=15)
        self.history = ctk.CTkScrollableFrame(history_card, fg_color="transparent")
        self.history.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _values(self):
        bases = {key: money(variable.get()) for key, variable in self.base_vars.items()}
        prices = {service: money(variable.get()) for service, variable in self.price_vars.items()}
        if any(price <= 0 for price in prices.values()):
            raise ValueError("Todos los precios deben ser mayores que cero.")
        counts = {}
        for key, variable in self.count_vars.items():
            value = parse_decimal(variable.get())
            if value != value.to_integral_value():
                raise ValueError("Las cantidades de menús deben ser números enteros.")
            counts[key] = int(value)
        return bases, counts, prices

    def _load_latest_prices(self):
        with connect() as conn:
            row = conn.execute(
                """SELECT precio_desayuno,precio_almuerzo,precio_cena
                FROM recaudacion_diaria ORDER BY fecha DESC,id DESC LIMIT 1"""
            ).fetchone()
        if not row:
            return
        for service, variable in self.price_vars.items():
            variable.set(f"{row[f'precio_{service[:-1]}']:.2f}")

    @staticmethod
    def _totals(bases, counts, prices):
        menu_total = sum(counts.values())
        menu_amount = sum(
            Decimal(count) * prices[service]
            for key, count in counts.items()
            for service in SERVICES
            if key.endswith("_" + service)
        )
        return sum(bases.values(), Decimal("0")) + menu_amount, menu_total

    def calculate(self):
        try:
            bases, counts, prices = self._values()
            total, menu_count = self._totals(bases, counts, prices)
            self.total_label.configure(text=f"Total del día: {format_money(total)}")
            self.menu_count_label.configure(text=f"Menús vendidos: {menu_count}")
        except ValueError:
            self.total_label.configure(text="Total del día: —")
            self.menu_count_label.configure(text="Revisa importes y cantidades")

    def save(self):
        try:
            date_iso = to_iso(self.date_var.get())
            bases, counts, prices = self._values()
            legacy_amounts = {
                prefix: sum(Decimal(counts[f"{prefix}_{service}"]) * prices[service] for service in SERVICES)
                for prefix, *_ in PAYMENTS
            }
            columns = [*bases, *counts, *(f"precio_{service[:-1]}" for service in SERVICES)]
            values = [
                *(float(bases[key]) for key in bases),
                *(counts[key] for key in counts),
                *(float(prices[service]) for service in SERVICES),
            ]
            with transaction() as conn:
                conn.execute(
                    f"""INSERT INTO recaudacion_diaria
                    (fecha,{','.join(columns)},efectivo_menu,visa_menu,credito_menu,precio_menu,observaciones)
                    VALUES ({','.join('?' for _ in range(len(columns) + 6))})
                    ON CONFLICT(fecha) DO UPDATE SET
                    {','.join(f'{column}=excluded.{column}' for column in columns)},
                    efectivo_menu=excluded.efectivo_menu, visa_menu=excluded.visa_menu,
                    credito_menu=excluded.credito_menu, precio_menu=excluded.precio_menu,
                    observaciones=excluded.observaciones""",
                    (
                        date_iso, *values,
                        float(legacy_amounts["efectivo"]), float(legacy_amounts["visa"]),
                        float(legacy_amounts["credito"]), float(prices["almuerzos"]),
                        self.notes.get().strip(),
                    ),
                )
            messagebox.showinfo("Recaudación", "El registro diario se ha guardado.")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("No se pudo guardar", str(exc))

    def _row_values(self, row):
        bases = {key: Decimal(str(row[key])) for key in self.base_vars}
        counts = {key: int(row[key]) for key in self.count_vars}
        prices = {service: Decimal(str(row[f"precio_{service[:-1]}"])) for service in SERVICES}
        return bases, counts, prices

    def refresh(self):
        for widget in self.history.winfo_children():
            widget.destroy()
        with connect() as conn:
            rows = conn.execute("SELECT * FROM recaudacion_diaria ORDER BY fecha DESC LIMIT 31").fetchall()
        if not rows:
            ctk.CTkLabel(self.history, text="Todavía no hay registros.", text_color="gray").pack(pady=20)
            return
        for row in rows:
            total, menus = self._totals(*self._row_values(row))
            text = f"{to_display(row['fecha'])}    {format_money(total)}    · {menus} menús"
            card = ctk.CTkFrame(self.history, fg_color=("gray84", "gray22"))
            card.pack(fill="x", pady=3)
            ctk.CTkButton(
                card, text=text, anchor="w", fg_color="transparent", hover_color=("gray75", "gray28"),
                command=lambda selected=row: self.load(selected),
            ).pack(side="left", fill="x", expand=True, padx=(4, 2), pady=4)
            ctk.CTkButton(
                card, text="×", width=30, fg_color="#A33",
                command=lambda record_id=row["id"]: self.delete(record_id),
            ).pack(side="right", padx=(2, 6), pady=5)

    def load(self, row):
        self.date_var.set(to_display(row["fecha"]))
        for key, variable in self.base_vars.items():
            variable.set(f"{row[key]:.2f}")
        for key, variable in self.count_vars.items():
            variable.set(str(int(row[key])))
        for service, variable in self.price_vars.items():
            variable.set(f"{row[f'precio_{service[:-1]}']:.2f}")
        self.notes.delete(0, "end")
        self.notes.insert(0, row["observaciones"] or "")

    def delete(self, record_id):
        if not messagebox.askyesno("Eliminar recaudación", "¿Eliminar este registro diario?"):
            return
        with transaction() as conn:
            conn.execute("DELETE FROM recaudacion_diaria WHERE id=?", (record_id,))
        self.refresh()
