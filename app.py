import json

import customtkinter as ctk
from PIL import Image
from tkinter import filedialog, messagebox

from core.backup import backup_on_start_if_enabled
from core.database import initialize_database
from core.paths import APP_DIR
from core.settings import (
    app_name,
    backup_directory,
    detected_onedrive_directory,
    font_scale,
    load_settings,
    logo_path,
    reports_directory,
    save_settings,
)
from modules.registry import AVAILABLE_MODULES


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
ctk.set_widget_scaling(font_scale())


class MesaClaraApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{app_name()} - Control operativo")
        self.geometry("1220x820")
        self.minsize(1050, 700)
        initialize_database()
        self.last_backup_path = None
        self.startup_backup_error = None
        try:
            self.last_backup_path = backup_on_start_if_enabled()
        except Exception as exc:
            self.startup_backup_error = str(exc)
        self._build_header()
        self._load_modules()
        if self.startup_backup_error:
            self.after(250, lambda: messagebox.showwarning(
                "Copia de seguridad",
                f"No se pudo crear la copia automática en OneDrive:\n\n{self.startup_backup_error}",
                parent=self,
            ))

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=10)
        header.pack(fill="x", padx=15, pady=(15, 5))
        self.header = header
        self.logo_label = ctk.CTkLabel(header, text="", width=1)
        self.titles = ctk.CTkFrame(header, fg_color="transparent")
        self.titles.pack(side="left", padx=15, pady=14)
        self.title_label = ctk.CTkLabel(
            self.titles, text=app_name(),
            font=ctk.CTkFont(size=21, weight="bold"),
        )
        self.title_label.pack(anchor="w")
        ctk.CTkLabel(
            self.titles, text="Registros protegidos, cálculos automáticos e informes mensuales",
            text_color="gray",
        ).pack(anchor="w")

        self.theme_switch = ctk.CTkSwitch(header, text="Modo oscuro", command=self._toggle_theme)
        self.theme_switch.select()
        self.theme_switch.pack(side="right", padx=(8, 18))
        ctk.CTkButton(
            header, text="⚙", width=42, height=36, font=ctk.CTkFont(size=20),
            command=self._open_settings,
        ).pack(side="right", padx=5)
        self._refresh_branding()

    def _load_modules(self) -> None:
        config_path = APP_DIR / "config.json"
        try:
            enabled = json.loads(config_path.read_text(encoding="utf-8"))["enabled_modules"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showwarning("Configuración", f"Se usará la configuración predeterminada.\n\n{exc}")
            enabled = list(AVAILABLE_MODULES)

        self.tabs = ctk.CTkTabview(self, corner_radius=10, command=self._on_tab_changed)
        self.tabs.pack(fill="both", expand=True, padx=15, pady=10)
        self.module_controllers = {}
        self.module_definitions = {}
        self.tab_module_ids = {}
        for module_id in enabled:
            definition = AVAILABLE_MODULES.get(module_id)
            if definition is None:
                continue
            self.tabs.add(definition.title)
            self.module_definitions[module_id] = definition
            self.tab_module_ids[definition.title] = module_id
        if not self.module_definitions:
            messagebox.showerror("Configuración", "No hay módulos válidos habilitados en config.json.")
            return
        first_module = next(iter(self.module_definitions))
        self.tabs.set(self.module_definitions[first_module].title)
        self._load_module(first_module)

    def _on_tab_changed(self) -> None:
        module_id = self.tab_module_ids.get(self.tabs.get())
        if module_id:
            self._load_module(module_id)

    def _load_module(self, module_id: str) -> None:
        if module_id in self.module_controllers:
            return
        definition = self.module_definitions[module_id]
        tab = self.tabs.tab(definition.title)
        self.module_controllers[module_id] = None
        try:
            definition.builder(tab, self)
            self.module_controllers[module_id] = getattr(tab, "_controller", None)
        except Exception as exc:
            ctk.CTkLabel(
                tab, text=f"No se pudo cargar este módulo:\n{exc}", text_color="#FF6B6B"
            ).pack(pady=40)

    def _toggle_theme(self) -> None:
        ctk.set_appearance_mode("Dark" if self.theme_switch.get() else "Light")

    def _refresh_branding(self) -> None:
        name = app_name()
        self.title(f"{name} - Control operativo")
        self.title_label.configure(text=name)
        path = logo_path()
        if path and path.is_file():
            try:
                image = Image.open(path)
                image.thumbnail((64, 64), Image.Resampling.LANCZOS)
                self._logo_image = ctk.CTkImage(
                    light_image=image, dark_image=image, size=image.size,
                )
                self.logo_label.configure(image=self._logo_image)
                if not self.logo_label.winfo_manager():
                    self.logo_label.pack(side="left", padx=(15, 0), pady=8, before=self.titles)
                return
            except OSError:
                pass
        self.logo_label.configure(image=None)
        self.logo_label.pack_forget()

    def _open_settings(self) -> None:
        window = ctk.CTkToplevel(self)
        window.title(f"Ajustes de {app_name()}")
        window.geometry("760x650")
        window.resizable(False, False)
        window.transient(self)
        window.grab_set()
        ctk.CTkLabel(window, text="Ajustes", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(18, 8))
        body = ctk.CTkScrollableFrame(window, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18)
        current = load_settings()

        ctk.CTkLabel(body, text="Identidad de la aplicación", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(8, 5))
        name_value = ctk.StringVar(value=app_name())
        ctk.CTkEntry(body, textvariable=name_value, placeholder_text="Nombre de la aplicación").pack(fill="x", pady=(0, 10))

        logo_value = ctk.StringVar(value=str(logo_path() or ""))
        logo_row = ctk.CTkFrame(body, fg_color="transparent")
        logo_row.pack(fill="x", pady=(0, 10))
        ctk.CTkEntry(logo_row, textvariable=logo_value, placeholder_text="Logo opcional (recomendado: 512 × 512)").pack(side="left", fill="x", expand=True, padx=(0, 8))

        def choose_logo():
            selected = filedialog.askopenfilename(
                parent=window, title="Seleccionar logo",
                filetypes=(("Imágenes", "*.png *.jpg *.jpeg *.webp"), ("Todos los archivos", "*.*")),
            )
            if selected:
                logo_value.set(selected)

        ctk.CTkButton(logo_row, text="Elegir…", width=90, command=choose_logo).pack(side="left", padx=(0, 6))
        ctk.CTkButton(logo_row, text="Quitar", width=75, fg_color="#8B3A3A", command=lambda: logo_value.set("")).pack(side="left")

        font_row = ctk.CTkFrame(body, fg_color="transparent")
        font_row.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(font_row, text="Tamaño de fuente:").pack(side="left")
        font_values = ["80 %", "90 %", "100 %", "110 %", "120 %", "130 %", "140 %", "150 %"]
        font_value = ctk.StringVar(value=f"{round(font_scale() * 100):d} %")
        ctk.CTkOptionMenu(font_row, values=font_values, variable=font_value, width=110).pack(side="right")

        ctk.CTkLabel(body, text="Exportación de informes", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))
        report_value = ctk.StringVar(value=str(reports_directory()))
        report_row = ctk.CTkFrame(body, fg_color="transparent")
        report_row.pack(fill="x", pady=(0, 16))
        ctk.CTkEntry(report_row, textvariable=report_value).pack(side="left", fill="x", expand=True, padx=(0, 8))

        def choose_report_directory():
            selected = filedialog.askdirectory(parent=window, initialdir=report_value.get())
            if selected:
                report_value.set(selected)

        ctk.CTkButton(report_row, text="Examinar…", width=95, command=choose_report_directory).pack(side="right")

        ctk.CTkLabel(body, text="Copias de seguridad en OneDrive", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 5))
        backup_enabled = ctk.BooleanVar(value=bool(current.get("backup_on_start", False)))
        ctk.CTkSwitch(body, text="Crear una copia de la base de datos al iniciar", variable=backup_enabled).pack(anchor="w", pady=(0, 8))
        backup_value = ctk.StringVar(value=str(backup_directory() or ""))
        backup_row = ctk.CTkFrame(body, fg_color="transparent")
        backup_row.pack(fill="x", pady=(0, 5))
        ctk.CTkEntry(backup_row, textvariable=backup_value, placeholder_text="Carpeta sincronizada con OneDrive").pack(side="left", fill="x", expand=True, padx=(0, 8))

        def choose_backup_directory():
            initial = backup_value.get() or str(detected_onedrive_directory() or APP_DIR)
            selected = filedialog.askdirectory(parent=window, initialdir=initial)
            if selected:
                backup_value.set(selected)

        def detect_onedrive():
            detected = detected_onedrive_directory()
            if detected:
                backup_value.set(str(detected / "Mesa Clara" / "Backups"))
            else:
                messagebox.showwarning("OneDrive", "Windows no ha indicado ninguna carpeta local de OneDrive.", parent=window)

        ctk.CTkButton(backup_row, text="Examinar…", width=95, command=choose_backup_directory).pack(side="right")
        ctk.CTkButton(body, text="Detectar OneDrive", width=145, command=detect_onedrive).pack(anchor="e", pady=(0, 12))
        backup_status = "Todavía no se ha creado una copia en esta sesión."
        if self.last_backup_path:
            backup_status = f"Última copia: {self.last_backup_path}"
        ctk.CTkLabel(body, text=backup_status, text_color="gray", wraplength=680, justify="left").pack(anchor="w")

        def save():
            selected_reports = report_value.get().strip()
            selected_name = name_value.get().strip()
            selected_logo = logo_value.get().strip()
            selected_backup = backup_value.get().strip()
            if not selected_name:
                messagebox.showerror("Ajustes", "Escribe un nombre para la aplicación.", parent=window)
                return
            if not selected_reports:
                messagebox.showerror("Ajustes", "Selecciona una carpeta para los informes.", parent=window)
                return
            if selected_logo:
                try:
                    with Image.open(selected_logo) as image:
                        image.verify()
                except (OSError, ValueError):
                    messagebox.showerror("Ajustes", "El archivo elegido no es una imagen válida.", parent=window)
                    return
            if backup_enabled.get() and not selected_backup:
                messagebox.showerror("Ajustes", "Selecciona una carpeta de OneDrive para las copias.", parent=window)
                return
            try:
                scale = int(font_value.get().split()[0]) / 100
                save_settings({
                    **load_settings(),
                    "reports_directory": selected_reports,
                    "app_name": selected_name,
                    "font_scale": scale,
                    "logo_path": selected_logo,
                    "backup_on_start": backup_enabled.get(),
                    "backup_directory": selected_backup,
                })
                reports_directory().mkdir(parents=True, exist_ok=True)
                if backup_enabled.get():
                    backup_directory().mkdir(parents=True, exist_ok=True)
                ctk.set_widget_scaling(scale)
                self._refresh_branding()
                reports = self.module_controllers.get("informes")
                if reports is not None:
                    reports.refresh_output_path()
                window.destroy()
                messagebox.showinfo("Ajustes", "Los ajustes se han guardado correctamente.", parent=self)
            except OSError as exc:
                messagebox.showerror("Ajustes", f"No se pudo guardar la configuración:\n{exc}", parent=window)

        ctk.CTkButton(window, text="Guardar ajustes", command=save).pack(fill="x", padx=24, pady=16)


if __name__ == "__main__":
    MesaClaraApp().mainloop()
