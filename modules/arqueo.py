import json
from decimal import Decimal
from tkinter import messagebox

import customtkinter as ctk

from core.database import connect, transaction
from core.dates import to_display, to_iso, today_display
from core.numbers import format_money, money, parse_decimal


DENOMINATIONS = tuple(Decimal(value) for value in (
    "0.05", "0.10", "0.20", "0.50", "1", "2", "5", "10", "20", "50", "100", "200"
))


def build_arqueo(parent, _app) -> None:
    parent._controller = CashCountModule(parent)


class CashCountModule:
    def __init__(self, parent):
        self.parent = parent
        self.quantity_vars = {}
        self.subtotal_labels = {}
        self._build()
        self.calculate()
        self.refresh_history()

    def _build(self) -> None:
        root = ctk.CTkFrame(self.parent, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=5, pady=5)
        root.grid_columnconfigure((0, 1, 2), weight=1)
        root.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(root)
        left.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")
        ctk.CTkLabel(left, text="Desglose de monedas y billetes", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=5)
        for row, denomination in enumerate(DENOMINATIONS):
            label = f"{denomination:.2f} €" if denomination < 5 else f"{denomination:.0f} €"
            ctk.CTkLabel(scroll, text=label, width=70, anchor="e").grid(row=row, column=0, padx=5, pady=3)
            ctk.CTkLabel(scroll, text="×", text_color="gray").grid(row=row, column=1)
            variable = ctk.StringVar(value="0")
            variable.trace_add("write", lambda *_: self.calculate())
            self.quantity_vars[denomination] = variable
            ctk.CTkEntry(scroll, textvariable=variable, width=75, justify="center").grid(row=row, column=2, padx=5, pady=3)
            subtotal = ctk.CTkLabel(scroll, text="0.00 €", width=95, anchor="e")
            subtotal.grid(row=row, column=3, padx=8)
            self.subtotal_labels[denomination] = subtotal
        self.total_cash_label = ctk.CTkLabel(left, text="Total en caja: 0.00 €", font=ctk.CTkFont(size=16, weight="bold"), text_color="#2CC985")
        self.total_cash_label.pack(pady=10)

        right = ctk.CTkFrame(root)
        right.grid(row=0, column=1, padx=8, pady=5, sticky="nsew")
        ctk.CTkLabel(right, text="Ventas y cuadre", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))
        form = ctk.CTkFrame(right, fg_color="transparent")
        form.pack(fill="x", padx=25)
        self.date_var = self._field(form, 0, "Fecha", today_display())
        self.fund_var = self._field(form, 1, "Fondo fijo (€)", "300.00", trace=True)
        self.lunch_var = self._field(form, 2, "Efectivo almuerzo (€)", "0.00", trace=True)
        self.dinner_var = self._field(form, 3, "Efectivo cena (€)", "0.00", trace=True)
        self.visa_var = self._field(form, 4, "Total VISA (€)", "0.00", trace=True)
        self.credit_var = self._field(form, 5, "Créditos / habitación (€)", "0.00")
        self.sales_label = ctk.CTkLabel(form, text="Efectivo de ventas: 0.00 €")
        self.sales_label.grid(row=6, column=0, columnspan=2, sticky="e", pady=(15, 3))
        self.daily_label = ctk.CTkLabel(form, text="Total diario: 0.00 €", font=ctk.CTkFont(weight="bold"))
        self.daily_label.grid(row=7, column=0, columnspan=2, sticky="e", pady=3)
        self.difference_label = ctk.CTkLabel(right, text="Diferencia: 0.00 €", font=ctk.CTkFont(size=17, weight="bold"))
        self.difference_label.pack(pady=25)
        buttons = ctk.CTkFrame(right, fg_color="transparent")
        buttons.pack(fill="x", padx=25)
        ctk.CTkButton(buttons, text="Guardar arqueo", command=self.save).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(buttons, text="Limpiar", command=self.clear, fg_color="transparent", border_width=1).pack(side="left", fill="x", expand=True, padx=(5, 0))

        history_card = ctk.CTkFrame(root)
        history_card.grid(row=0, column=2, padx=8, pady=5, sticky="nsew")
        ctk.CTkLabel(history_card, text="Arqueos guardados", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))
        self.history = ctk.CTkScrollableFrame(history_card, fg_color="transparent")
        self.history.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _field(self, parent, row, label, value, trace=False):
        ctk.CTkLabel(parent, text=f"{label}:").grid(row=row, column=0, sticky="w", pady=6)
        variable = ctk.StringVar(value=value)
        if trace:
            variable.trace_add("write", lambda *_: self.calculate())
        ctk.CTkEntry(parent, textvariable=variable, width=155).grid(row=row, column=1, sticky="e", pady=6)
        parent.grid_columnconfigure(1, weight=1)
        return variable

    @staticmethod
    def _safe_number(variable) -> Decimal:
        try:
            return parse_decimal(variable.get())
        except ValueError:
            return Decimal("0")

    def calculate(self) -> None:
        total_cash = Decimal("0")
        for denomination, variable in self.quantity_vars.items():
            subtotal = denomination * self._safe_number(variable)
            total_cash += subtotal
            self.subtotal_labels[denomination].configure(text=format_money(subtotal))
        fund = self._safe_number(self.fund_var)
        sales = self._safe_number(self.lunch_var) + self._safe_number(self.dinner_var)
        daily = sales + self._safe_number(self.visa_var)
        difference = total_cash - fund - sales
        self.total_cash_label.configure(text=f"Total en caja: {format_money(total_cash)}")
        self.sales_label.configure(text=f"Efectivo de ventas: {format_money(sales)}")
        self.daily_label.configure(text=f"Total diario: {format_money(daily)}")
        if abs(difference) < Decimal("0.01"):
            text, color = "Diferencia: 0.00 € (cuadrado)", "#2CC985"
        elif difference < 0:
            text, color = f"Diferencia: {format_money(difference)} (falta)", "#FF4D4D"
        else:
            text, color = f"Diferencia: +{format_money(difference)} (sobra)", "#3B82F6"
        self.difference_label.configure(text=text, text_color=color)

    def save(self) -> None:
        try:
            date_iso = to_iso(self.date_var.get())
            quantities = {}
            for denomination, variable in self.quantity_vars.items():
                value = parse_decimal(variable.get())
                if value != value.to_integral_value():
                    raise ValueError("Las cantidades de monedas y billetes deben ser enteras.")
                quantities[str(denomination)] = int(value)
            total_cash = sum(Decimal(key) * value for key, value in quantities.items())
            fund, lunch, dinner, visa = map(money, (
                self.fund_var.get(), self.lunch_var.get(), self.dinner_var.get(), self.visa_var.get()
            ))
            credits = str(money(self.credit_var.get()))
            daily = lunch + dinner + visa
            difference = total_cash - fund - lunch - dinner
            with transaction() as conn:
                conn.execute(
                    """INSERT INTO arqueo_caja
                    (fecha,total_efectivo,fondo_fijo,almuerzo_efectivo,cena_efectivo,total_visa,creditos,total_diario,diferencia,desglose_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (date_iso, float(total_cash), float(fund), float(lunch), float(dinner), float(visa), credits, float(daily), float(difference), json.dumps(quantities)),
                )
            messagebox.showinfo("Arqueo", "El arqueo se ha guardado correctamente.")
            self.refresh_history()
        except Exception as exc:
            messagebox.showerror("No se pudo guardar", str(exc))

    def clear(self) -> None:
        for variable in self.quantity_vars.values():
            variable.set("0")
        for variable in (self.lunch_var, self.dinner_var, self.visa_var, self.credit_var):
            variable.set("0.00")

    def refresh_history(self) -> None:
        for widget in self.history.winfo_children():
            widget.destroy()
        with connect() as conn:
            rows = conn.execute(
                """SELECT id,fecha,total_efectivo,total_diario,diferencia
                FROM arqueo_caja ORDER BY id DESC LIMIT 31"""
            ).fetchall()
        if not rows:
            ctk.CTkLabel(self.history, text="Todavía no hay arqueos.", text_color="gray").pack(pady=20)
            return
        for row in rows:
            card = ctk.CTkFrame(self.history, fg_color=("gray84", "gray22"))
            card.pack(fill="x", pady=3)
            text = (
                f"{to_display(row['fecha'])}\n"
                f"Caja: {format_money(row['total_efectivo'])} · Ventas: {format_money(row['total_diario'])}\n"
                f"Diferencia: {format_money(row['diferencia'])}"
            )
            ctk.CTkLabel(card, text=text, anchor="w", justify="left").pack(side="left", fill="x", expand=True, padx=8, pady=7)
            ctk.CTkButton(
                card, text="×", width=30, fg_color="#A33",
                command=lambda record_id=row["id"]: self.delete_history(record_id),
            ).pack(side="right", padx=6, pady=6)

    def delete_history(self, record_id: int) -> None:
        if not messagebox.askyesno("Eliminar arqueo", "¿Eliminar este arqueo guardado?"):
            return
        with transaction() as conn:
            conn.execute("DELETE FROM arqueo_caja WHERE id=?", (record_id,))
        self.refresh_history()
