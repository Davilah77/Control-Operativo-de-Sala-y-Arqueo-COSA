import json

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.database import initialize_database
from core.paths import APP_DIR
from core.settings import load_settings, reports_directory, save_settings
from modules.registry import AVAILABLE_MODULES


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class MesaClaraApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mesa Clara - Control operativo")
        self.geometry("1220x820")
        self.minsize(1050, 700)
        initialize_database()
        self._build_header()
        self._load_modules()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=10)
        header.pack(fill="x", padx=15, pady=(15, 5))
        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.pack(side="left", padx=15, pady=14)
        ctk.CTkLabel(
            titles, text="Mesa Clara",
            font=ctk.CTkFont(size=21, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles, text="Registros protegidos, cálculos automáticos e informes mensuales",
            text_color="gray",
        ).pack(anchor="w")

        self.theme_switch = ctk.CTkSwitch(header, text="Modo oscuro", command=self._toggle_theme)
        self.theme_switch.select()
        self.theme_switch.pack(side="right", padx=(8, 18))
        ctk.CTkButton(
            header, text="⚙", width=42, height=36, font=ctk.CTkFont(size=20),
            command=self._open_settings,
        ).pack(side="right", padx=5)

    def _load_modules(self) -> None:
        config_path = APP_DIR / "config.json"
        try:
            enabled = json.loads(config_path.read_text(encoding="utf-8"))["enabled_modules"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showwarning("Configuración", f"Se usará la configuración predeterminada.\n\n{exc}")
            enabled = list(AVAILABLE_MODULES)

        self.tabs = ctk.CTkTabview(self, corner_radius=10)
        self.tabs.pack(fill="both", expand=True, padx=15, pady=10)
        self.module_controllers = {}
        loaded = 0
        for module_id in enabled:
            definition = AVAILABLE_MODULES.get(module_id)
            if definition is None:
                continue
            tab = self.tabs.add(definition.title)
            try:
                definition.builder(tab, self)
                self.module_controllers[module_id] = getattr(tab, "_controller", None)
                loaded += 1
            except Exception as exc:
                ctk.CTkLabel(
                    tab, text=f"No se pudo cargar este módulo:\n{exc}", text_color="#FF6B6B"
                ).pack(pady=40)
        if not loaded:
            messagebox.showerror("Configuración", "No hay módulos válidos habilitados en config.json.")

    def _toggle_theme(self) -> None:
        ctk.set_appearance_mode("Dark" if self.theme_switch.get() else "Light")

    def _open_settings(self) -> None:
        window = ctk.CTkToplevel(self)
        window.title("Ajustes de Mesa Clara")
        window.geometry("650x230")
        window.resizable(False, False)
        window.transient(self)
        window.grab_set()
        ctk.CTkLabel(window, text="Ajustes", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 14))
        row = ctk.CTkFrame(window, fg_color="transparent")
        row.pack(fill="x", padx=24)
        ctk.CTkLabel(row, text="Carpeta de informes:").pack(anchor="w", pady=(0, 5))
        path_row = ctk.CTkFrame(row, fg_color="transparent")
        path_row.pack(fill="x")
        value = ctk.StringVar(value=str(reports_directory()))
        entry = ctk.CTkEntry(path_row, textvariable=value)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def choose_directory():
            selected = filedialog.askdirectory(parent=window, initialdir=value.get())
            if selected:
                value.set(selected)

        ctk.CTkButton(path_row, text="Examinar…", width=95, command=choose_directory).pack(side="right")

        def save():
            selected = value.get().strip()
            if not selected:
                messagebox.showerror("Ajustes", "Selecciona una carpeta para los informes.", parent=window)
                return
            try:
                save_settings({**load_settings(), "reports_directory": selected})
                reports_directory().mkdir(parents=True, exist_ok=True)
                reports = self.module_controllers.get("informes")
                if reports is not None:
                    reports.refresh_output_path()
                window.destroy()
                messagebox.showinfo("Ajustes", "La carpeta de informes se ha actualizado.", parent=self)
            except OSError as exc:
                messagebox.showerror("Ajustes", f"No se pudo guardar la configuración:\n{exc}", parent=window)

        ctk.CTkButton(window, text="Guardar ajustes", command=save).pack(fill="x", padx=24, pady=24)


if __name__ == "__main__":
    MesaClaraApp().mainloop()
