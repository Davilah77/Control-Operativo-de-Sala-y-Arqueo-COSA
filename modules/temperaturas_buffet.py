from tkinter import messagebox

import customtkinter as ctk

from core.database import connect, transaction
from core.dates import to_display, to_iso, today_display
from core.numbers import parse_decimal


def build_temperaturas_buffet(parent, _app) -> None:
    parent._controller = BuffetTemperatureModule(parent)


class BuffetTemperatureModule:
    CATEGORIES = (
        ("caliente", "Expositor caliente", "≥ 65 °C", lambda value: value >= 65),
        ("frio", "Expositor frío / ensaladas", "≤ 8 °C", lambda value: value <= 8),
        ("postre", "Expositor de postres", "≤ 8 °C", lambda value: value <= 8),
    )

    def __init__(self, parent):
        self.parent = parent
        self.fields = {}
        self._build()
        self.refresh()

    def _build(self):
        root = ctk.CTkFrame(self.parent, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=8, pady=8)
        root.grid_columnconfigure((0, 1), weight=1)
        root.grid_rowconfigure(0, weight=1)

        form_card = ctk.CTkScrollableFrame(root)
        form_card.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        ctk.CTkLabel(form_card, text="Temperaturas de alimentos del buffet", font=ctk.CTkFont(size=17, weight="bold")).pack(pady=(8, 3))
        ctk.CTkLabel(form_card, text="Dos mediciones por producto y servicio", text_color="gray").pack(pady=(0, 12))
        top = ctk.CTkFrame(form_card, fg_color="transparent")
        top.pack(fill="x", padx=18)
        ctk.CTkLabel(top, text="Fecha:").grid(row=0, column=0, sticky="w", pady=5)
        self.date_var = ctk.StringVar(value=today_display())
        ctk.CTkEntry(top, textvariable=self.date_var, width=145).grid(row=0, column=1, sticky="e", pady=5)
        ctk.CTkLabel(top, text="Servicio:").grid(row=1, column=0, sticky="w", pady=5)
        self.service = ctk.CTkOptionMenu(top, values=["Desayuno", "Almuerzo", "Cena"], width=145)
        self.service.grid(row=1, column=1, sticky="e", pady=5)
        top.grid_columnconfigure(1, weight=1)

        for key, label, limit, _validator in self.CATEGORIES:
            section = ctk.CTkFrame(form_card, fg_color=("gray84", "gray22"))
            section.pack(fill="x", padx=18, pady=7)
            ctk.CTkLabel(section, text=f"{label} ({limit})", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 5))
            product = ctk.CTkEntry(section, placeholder_text="Producto", width=210)
            product.grid(row=1, column=0, padx=(10, 5), pady=(0, 9), sticky="ew")
            t1 = ctk.CTkEntry(section, placeholder_text="T.1", width=70, justify="center")
            t1.grid(row=1, column=1, padx=4, pady=(0, 9))
            t2 = ctk.CTkEntry(section, placeholder_text="T.2", width=70, justify="center")
            t2.grid(row=1, column=2, padx=(4, 10), pady=(0, 9))
            section.grid_columnconfigure(0, weight=1)
            self.fields[key] = (product, t1, t2)

        self.responsible = ctk.CTkEntry(form_card, placeholder_text="Responsable")
        self.responsible.pack(fill="x", padx=18, pady=6)
        self.notes = ctk.CTkEntry(form_card, placeholder_text="Observaciones o medidas correctoras")
        self.notes.pack(fill="x", padx=18, pady=6)
        ctk.CTkButton(form_card, text="Guardar mediciones", command=self.save).pack(fill="x", padx=18, pady=(8, 14))

        history_card = ctk.CTkFrame(root)
        history_card.grid(row=0, column=1, padx=(6, 0), sticky="nsew")
        ctk.CTkLabel(history_card, text="Registros recientes", font=ctk.CTkFont(size=17, weight="bold")).pack(pady=15)
        self.history = ctk.CTkScrollableFrame(history_card, fg_color="transparent")
        self.history.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _category_values(self):
        result = {}
        for key, _label, _limit, validator in self.CATEGORIES:
            product_entry, t1_entry, t2_entry = self.fields[key]
            product = product_entry.get().strip()
            raw_t1, raw_t2 = t1_entry.get().strip(), t2_entry.get().strip()
            if not product and not raw_t1 and not raw_t2:
                result[key] = ("", None, None, True)
                continue
            if not product or not raw_t1 or not raw_t2:
                raise ValueError(f"Completa producto, T.1 y T.2 en el expositor {key}.")
            t1, t2 = float(parse_decimal(raw_t1, minimum=None)), float(parse_decimal(raw_t2, minimum=None))
            result[key] = (product, t1, t2, validator(t1) and validator(t2))
        if not any(values[0] for values in result.values()):
            raise ValueError("Introduce al menos un producto con sus dos temperaturas.")
        return result

    def save(self):
        try:
            date_iso = to_iso(self.date_var.get())
            values = self._category_values()
            correct = int(all(category[3] for category in values.values()))
            params = [date_iso, self.service.get()]
            for key, *_ in self.CATEGORIES:
                params.extend(values[key][:3])
            params.extend((correct, self.responsible.get().strip(), self.notes.get().strip()))
            with transaction() as conn:
                conn.execute(
                    """INSERT INTO temperaturas_buffet
                    (fecha,servicio,producto_caliente,caliente_t1,caliente_t2,
                    producto_frio,frio_t1,frio_t2,producto_postre,postre_t1,postre_t2,
                    correcto,responsable,observaciones)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(fecha,servicio) DO UPDATE SET
                    producto_caliente=excluded.producto_caliente, caliente_t1=excluded.caliente_t1, caliente_t2=excluded.caliente_t2,
                    producto_frio=excluded.producto_frio, frio_t1=excluded.frio_t1, frio_t2=excluded.frio_t2,
                    producto_postre=excluded.producto_postre, postre_t1=excluded.postre_t1, postre_t2=excluded.postre_t2,
                    correcto=excluded.correcto, responsable=excluded.responsable, observaciones=excluded.observaciones""",
                    params,
                )
            status = "correctas" if correct else "con incidencia"
            messagebox.showinfo("Temperaturas del buffet", f"Mediciones guardadas como {status}.")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("No se pudo guardar", str(exc))

    def refresh(self):
        for widget in self.history.winfo_children():
            widget.destroy()
        with connect() as conn:
            rows = conn.execute("SELECT * FROM temperaturas_buffet ORDER BY fecha DESC,id DESC LIMIT 42").fetchall()
        if not rows:
            ctk.CTkLabel(self.history, text="Todavía no hay registros.", text_color="gray").pack(pady=20)
            return
        dates = list(dict.fromkeys(row["fecha"] for row in rows))
        day_colors = {
            current_date: (("#E3EAF2", "#343A40") if index % 2 == 0 else ("#F0E7DC", "#403A34"))
            for index, current_date in enumerate(dates)
        }
        for row in rows:
            card = ctk.CTkFrame(self.history, fg_color=day_colors[row["fecha"]])
            card.pack(fill="x", pady=3)
            color = "#2CC985" if row["correcto"] else "#FF4D4D"
            lines = [f"{to_display(row['fecha'])} · {row['servicio']}"]
            for key, label, _limit, _validator in self.CATEGORIES:
                product = row[f"producto_{key}"]
                if product:
                    lines.append(f"{label}: {product} · {row[f'{key}_t1']:.1f}/{row[f'{key}_t2']:.1f} °C")
            ctk.CTkLabel(card, text="\n".join(lines), anchor="w", justify="left").pack(side="left", fill="x", expand=True, padx=9, pady=7)
            ctk.CTkLabel(card, text="OK" if row["correcto"] else "INCIDENCIA", text_color=color, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=5)
            ctk.CTkButton(card, text="×", width=30, fg_color="#A33", command=lambda record_id=row["id"]: self.delete(record_id)).pack(side="right", padx=(2, 7), pady=5)

    def delete(self, record_id):
        if not messagebox.askyesno("Eliminar registro", "¿Eliminar estas mediciones del buffet?"):
            return
        with transaction() as conn:
            conn.execute("DELETE FROM temperaturas_buffet WHERE id=?", (record_id,))
        self.refresh()
