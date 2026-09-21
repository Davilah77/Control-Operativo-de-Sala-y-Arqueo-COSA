from tkinter import messagebox

import customtkinter as ctk

from core.database import connect, transaction
from core.dates import to_display, to_iso, today_display
from core.numbers import parse_decimal


MIN_WASH = 60.0
MIN_RINSE = 82.0


def build_temperaturas(parent, _app) -> None:
    parent._controller = TemperatureModule(parent)


class TemperatureModule:
    def __init__(self, parent):
        self.parent = parent
        self._build()
        self.refresh()

    def _build(self):
        root = ctk.CTkFrame(self.parent, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=8, pady=8)
        root.grid_columnconfigure((0, 1), weight=1)
        root.grid_rowconfigure(0, weight=1)
        form_card = ctk.CTkFrame(root)
        form_card.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        ctk.CTkLabel(form_card, text="Control APPCC del lavavajillas", font=ctk.CTkFont(size=17, weight="bold")).pack(pady=(18, 4))
        ctk.CTkLabel(form_card, text=f"Límites: lavado ≥ {MIN_WASH:.0f} °C · aclarado ≥ {MIN_RINSE:.0f} °C", text_color="gray").pack(pady=(0, 15))
        form = ctk.CTkFrame(form_card, fg_color="transparent")
        form.pack(fill="x", padx=25)
        self.date_var = self._entry(form, 0, "Fecha", today_display())
        ctk.CTkLabel(form, text="Servicio:").grid(row=1, column=0, sticky="w", pady=6)
        self.service = ctk.CTkOptionMenu(form, values=["Almuerzo", "Cena"], width=155)
        self.service.grid(row=1, column=1, sticky="e", pady=6)
        self.wash_var = self._entry(form, 2, "Temperatura de lavado (°C)", "")
        self.rinse_var = self._entry(form, 3, "Temperatura de aclarado (°C)", "")
        self.responsible = ctk.CTkEntry(form, placeholder_text="Responsable")
        self.responsible.grid(row=4, column=0, columnspan=2, sticky="ew", pady=8)
        self.notes = ctk.CTkEntry(form, placeholder_text="Observaciones o medidas correctoras")
        self.notes.grid(row=5, column=0, columnspan=2, sticky="ew", pady=8)
        ctk.CTkButton(form_card, text="Guardar lectura", command=self.save).pack(fill="x", padx=25, pady=18)

        history_card = ctk.CTkFrame(root)
        history_card.grid(row=0, column=1, padx=(6, 0), sticky="nsew")
        ctk.CTkLabel(history_card, text="Lecturas recientes", font=ctk.CTkFont(size=17, weight="bold")).pack(pady=15)
        self.history = ctk.CTkScrollableFrame(history_card, fg_color="transparent")
        self.history.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    @staticmethod
    def _entry(parent, row, label, value):
        ctk.CTkLabel(parent, text=f"{label}:").grid(row=row, column=0, sticky="w", pady=6)
        variable = ctk.StringVar(value=value)
        ctk.CTkEntry(parent, textvariable=variable, width=155).grid(row=row, column=1, sticky="e", pady=6)
        parent.grid_columnconfigure(1, weight=1)
        return variable

    def save(self):
        try:
            date_iso = to_iso(self.date_var.get())
            wash = float(parse_decimal(self.wash_var.get()))
            rinse = float(parse_decimal(self.rinse_var.get()))
            correct = int(wash >= MIN_WASH and rinse >= MIN_RINSE)
            service = self.service.get()
            values = (wash, rinse, correct, self.notes.get().strip(), self.responsible.get().strip())
            with transaction() as conn:
                existing = conn.execute(
                    """SELECT id FROM temperaturas_lavavajillas
                    WHERE fecha IN (?, ?) AND servicio=? ORDER BY id DESC LIMIT 1""",
                    (date_iso, to_display(date_iso), service),
                ).fetchone()
                if existing:
                    conn.execute(
                        """UPDATE temperaturas_lavavajillas SET
                        fecha=?, temp_lavado=?, temp_aclarado=?, correcto=?, observaciones=?, responsable=? WHERE id=?""",
                        (date_iso, *values, existing["id"]),
                    )
                else:
                    conn.execute(
                        """INSERT INTO temperaturas_lavavajillas
                        (fecha,servicio,temp_lavado,temp_aclarado,correcto,observaciones,responsable)
                        VALUES (?,?,?,?,?,?,?)""",
                        (date_iso, service, *values),
                    )
            status = "correcta" if correct else "con incidencia"
            messagebox.showinfo("Temperaturas", f"Lectura guardada como {status}.")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("No se pudo guardar", str(exc))

    def refresh(self):
        for widget in self.history.winfo_children():
            widget.destroy()
        with connect() as conn:
            rows = conn.execute(
                """SELECT id,fecha,servicio,temp_lavado,temp_aclarado,correcto,responsable,observaciones
                FROM temperaturas_lavavajillas ORDER BY id DESC LIMIT 40"""
            ).fetchall()
        if not rows:
            ctk.CTkLabel(self.history, text="Todavía no hay lecturas.", text_color="gray").pack(pady=20)
            return
        for row in rows:
            card = ctk.CTkFrame(self.history, fg_color=("gray84", "gray22"))
            card.pack(fill="x", pady=3)
            color = "#2CC985" if row["correcto"] else "#FF4D4D"
            status = "OK" if row["correcto"] else "INCIDENCIA"
            detail = f"{to_display(row['fecha'])} · {row['servicio']} · {row['temp_lavado']:.1f}/{row['temp_aclarado']:.1f} °C"
            if row["responsable"]:
                detail += f" · {row['responsable']}"
            ctk.CTkLabel(card, text=detail, anchor="w").pack(side="left", fill="x", expand=True, padx=10, pady=8)
            ctk.CTkLabel(card, text=status, text_color=color, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=8)
            ctk.CTkButton(card, text="×", width=30, fg_color="#A33", command=lambda record_id=row["id"]: self.delete(record_id)).pack(side="right", padx=(2, 8), pady=5)

    def delete(self, record_id):
        if not messagebox.askyesno("Eliminar lectura", "¿Eliminar esta lectura errónea?"):
            return
        with transaction() as conn:
            conn.execute("DELETE FROM temperaturas_lavavajillas WHERE id=?", (record_id,))
        self.refresh()
