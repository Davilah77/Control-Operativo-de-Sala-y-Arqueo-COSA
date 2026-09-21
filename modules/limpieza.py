from datetime import timedelta
from tkinter import messagebox

import customtkinter as ctk

from core.database import connect, transaction
from core.dates import parse_date, today_display


DAYS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")


def build_limpieza(parent, _app) -> None:
    parent._controller = CleaningModule(parent)


class CleaningModule:
    def __init__(self, parent):
        self.parent = parent
        self.entries = {}
        self.current_monday = None
        self._build()
        self.load_week()

    def _build(self):
        toolbar = ctk.CTkFrame(self.parent)
        toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(toolbar, text="Plan semanal de limpieza", font=ctk.CTkFont(size=17, weight="bold")).pack(side="left", padx=14, pady=11)
        self.week_var = ctk.StringVar(value=today_display())
        ctk.CTkEntry(toolbar, textvariable=self.week_var, width=130).pack(side="left", padx=8)
        ctk.CTkButton(toolbar, text="Cargar semana", width=115, command=self.load_week).pack(side="left", padx=4)
        ctk.CTkButton(toolbar, text="Guardar semana", width=125, command=self.save).pack(side="right", padx=14)

        self.week_label = ctk.CTkLabel(self.parent, text="", text_color="gray")
        self.week_label.pack(pady=3)
        self.grid_frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=8, pady=4)
        self.grid_frame.grid_columnconfigure(0, weight=1)
        headers = ("Zona / tarea", *DAYS, "Turno")
        widths = (235, *([88] * 7), 125)
        for column, (header, width) in enumerate(zip(headers, widths)):
            ctk.CTkLabel(
                self.grid_frame, text=header, width=width,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=0, column=column, padx=2, pady=5, sticky="ew")

        with connect() as conn:
            self.tasks = conn.execute(
                "SELECT id,nombre,turno FROM tareas_limpieza WHERE activo=1 ORDER BY orden,nombre"
            ).fetchall()
        for row_index, task in enumerate(self.tasks, start=1):
            ctk.CTkLabel(self.grid_frame, text=task["nombre"], anchor="w", width=235).grid(row=row_index, column=0, padx=3, pady=3, sticky="ew")
            for day_index in range(7):
                variable = ctk.StringVar()
                ctk.CTkEntry(self.grid_frame, textvariable=variable, width=88).grid(row=row_index, column=day_index + 1, padx=2, pady=3)
                self.entries[(task["id"], day_index)] = variable
            ctk.CTkLabel(self.grid_frame, text=task["turno"], width=125, wraplength=120).grid(row=row_index, column=8, padx=3, pady=3)

        note_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        note_frame.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(note_frame, text="Observaciones:").pack(side="left", padx=(0, 8))
        self.notes = ctk.CTkEntry(note_frame, placeholder_text="Incidencias o cambios de la semana")
        self.notes.pack(side="left", fill="x", expand=True)

    def _monday(self):
        selected = parse_date(self.week_var.get())
        return selected - timedelta(days=selected.weekday())

    def load_week(self):
        try:
            monday = self._monday()
            sunday = monday + timedelta(days=6)
            self.current_monday = monday
            self.week_var.set(monday.strftime("%d/%m/%Y"))
            self.week_label.configure(text=f"Semana del {monday:%d/%m/%Y} al {sunday:%d/%m/%Y}")
            dates = [(monday + timedelta(days=index)).isoformat() for index in range(7)]
            placeholders = ",".join("?" for _ in dates)
            with connect() as conn:
                assignments = {
                    (row["tarea_id"], row["fecha"]): row["responsable"]
                    for row in conn.execute(
                        f"SELECT tarea_id,fecha,responsable FROM asignaciones_limpieza WHERE fecha IN ({placeholders})",
                        dates,
                    )
                }
                note = conn.execute("SELECT observaciones FROM notas_limpieza WHERE semana_inicio=?", (monday.isoformat(),)).fetchone()
            for (task_id, day_index), variable in self.entries.items():
                variable.set(assignments.get((task_id, dates[day_index]), ""))
            self.notes.delete(0, "end")
            if note:
                self.notes.insert(0, note["observaciones"])
        except Exception as exc:
            messagebox.showerror("No se pudo cargar", str(exc))

    def save(self):
        try:
            monday = self._monday()
            values = []
            for (task_id, day_index), variable in self.entries.items():
                current_date = (monday + timedelta(days=day_index)).isoformat()
                values.append((current_date, task_id, variable.get().strip()))
            with transaction() as conn:
                conn.executemany(
                    """INSERT INTO asignaciones_limpieza(fecha,tarea_id,responsable) VALUES (?,?,?)
                    ON CONFLICT(fecha,tarea_id) DO UPDATE SET responsable=excluded.responsable""",
                    values,
                )
                conn.execute(
                    """INSERT INTO notas_limpieza(semana_inicio,observaciones) VALUES (?,?)
                    ON CONFLICT(semana_inicio) DO UPDATE SET observaciones=excluded.observaciones""",
                    (monday.isoformat(), self.notes.get().strip()),
                )
            messagebox.showinfo("Limpieza", "La planificación semanal se ha guardado.")
            self.load_week()
        except Exception as exc:
            messagebox.showerror("No se pudo guardar", str(exc))

