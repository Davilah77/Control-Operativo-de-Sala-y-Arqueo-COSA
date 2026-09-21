from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from core.database import connect, transaction
from core.settings import reports_directory
from inventario_pdf import generar_pdf_botellas, generar_pdf_inventario


MONTHS = [
    "01 - Enero", "02 - Febrero", "03 - Marzo", "04 - Abril", "05 - Mayo", "06 - Junio",
    "07 - Julio", "08 - Agosto", "09 - Septiembre", "10 - Octubre", "11 - Noviembre", "12 - Diciembre",
]
FORM_TYPES = ("Inventario de bodega", "Inventario de desayunos", "Recaudación de botellas")
TABLE_SURFACE = ("gray86", "gray17")


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
        self.form_type = ctk.CTkOptionMenu(toolbar, values=list(FORM_TYPES), width=205, command=lambda _value: self._change_form())
        self.form_type.set(FORM_TYPES[0])
        self.form_type.pack(side="left", padx=8)
        self.manage_button = ctk.CTkButton(toolbar, text="Gestionar productos", width=145, command=self.manage_products)
        self.manage_button.pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Exportar vacío", width=115, fg_color="#606A73", command=lambda: self.export(True)).pack(side="right", padx=(5, 15))
        ctk.CTkButton(toolbar, text="Exportar datos", width=120, command=lambda: self.export(False)).pack(side="right", padx=5)

        self.form = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        self.form.pack(fill="both", expand=True, padx=12, pady=(5, 10))
        self._render_form()

    def _clear_form(self):
        for widget in self.form.winfo_children():
            widget.destroy()
        self.entries = {}

    def _change_form(self):
        self._render_form()

    def _inventory_kind(self):
        if self.form_type.get() == FORM_TYPES[0]:
            return "bodega"
        if self.form_type.get() == FORM_TYPES[1]:
            return "desayunos"
        return None

    @staticmethod
    def _load_catalogue(inventory_type):
        with connect() as conn:
            categories = conn.execute(
                "SELECT id,nombre FROM inventario_categorias WHERE tipo=? ORDER BY orden,nombre",
                (inventory_type,),
            ).fetchall()
            catalogue = []
            for category in categories:
                products = conn.execute(
                    """SELECT id,codigo,nombre,unidad FROM inventario_productos
                    WHERE categoria_id=? AND activo=1 ORDER BY orden,nombre""",
                    (category["id"],),
                ).fetchall()
                if products:
                    catalogue.append((category["nombre"], [
                        (row["id"], row["codigo"], row["nombre"], row["unidad"]) for row in products
                    ]))
        return catalogue

    def _render_form(self, preserved_values=None):
        self._clear_form()
        selected = self.form_type.get()
        if selected == FORM_TYPES[2]:
            self.manage_button.configure(state="disabled")
            self.current_catalogue = None
            self._render_bottles()
        else:
            self.manage_button.configure(state="normal")
            self.current_catalogue = self._load_catalogue(self._inventory_kind())
            self._render_inventory(self.current_catalogue, preserved_values or {})

    def _render_inventory(self, catalogue, preserved_values):
        self.form.grid_columnconfigure(1, weight=1)
        headers = ("Código", "Artículo", "Cantidad", "Unidad")
        for column, label in enumerate(headers):
            ctk.CTkLabel(
                self.form, text=label, font=ctk.CTkFont(weight="bold"),
                anchor="w", fg_color=TABLE_SURFACE,
            ).grid(row=0, column=column, sticky="ew", padx=5, pady=(4, 8))
        row = 1
        for category, items in catalogue:
            ctk.CTkLabel(
                self.form, text=category, font=ctk.CTkFont(weight="bold"),
                fg_color=("#DCE6F1", "#263C52"), corner_radius=5,
            ).grid(row=row, column=0, columnspan=4, sticky="ew", padx=3, pady=(9, 4), ipady=4)
            row += 1
            for product_id, code, item, unit in items:
                ctk.CTkLabel(
                    self.form, text=code or "—", width=90, fg_color=TABLE_SURFACE,
                ).grid(row=row, column=0, padx=5, pady=2)
                ctk.CTkLabel(
                    self.form, text=item, anchor="w", fg_color=TABLE_SURFACE,
                ).grid(row=row, column=1, sticky="ew", padx=5, pady=2)
                variable = ctk.StringVar(value=preserved_values.get(product_id, ""))
                ctk.CTkEntry(self.form, textvariable=variable, width=105, justify="center").grid(row=row, column=2, padx=5, pady=2)
                ctk.CTkLabel(
                    self.form, text=unit, width=95, anchor="w", fg_color=TABLE_SURFACE,
                ).grid(row=row, column=3, padx=5, pady=2)
                self.entries[product_id] = variable
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
                slug = "inventario_bodega" if is_warehouse else "inventario_desayunos"
                title = "INVENTARIO DE BODEGA" if is_warehouse else "INVENTARIO DE DESAYUNOS Y VARIOS"
                values = {key: variable.get() for key, variable in self.entries.items()}
                path = output_directory / f"{slug}{suffix}.pdf"
                result = generar_pdf_inventario(title, self.current_catalogue, values, path, empty=empty)
            messagebox.showinfo("Inventario", f"Se ha creado:\n\n{result}")
        except Exception as exc:
            messagebox.showerror("No se pudo exportar", str(exc))

    def manage_products(self):
        inventory_type = self._inventory_kind()
        if inventory_type is None:
            return
        window = ctk.CTkToplevel(self.parent)
        window.title("Gestionar productos")
        window.geometry("900x650")
        window.transient(self.parent.winfo_toplevel())
        window.grab_set()

        header = ctk.CTkFrame(window, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkLabel(header, text=f"Productos de {inventory_type}", font=ctk.CTkFont(size=19, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="Añadir producto", command=lambda: self._edit_product(window, inventory_type, None, refresh)).pack(side="right")
        listing = ctk.CTkScrollableFrame(window)
        listing.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        listing.grid_columnconfigure(1, weight=1)

        def refresh():
            for widget in listing.winfo_children():
                widget.destroy()
            with connect() as conn:
                products = conn.execute(
                    """SELECT p.id,p.codigo,p.nombre,p.unidad,c.nombre AS categoria
                    FROM inventario_productos p JOIN inventario_categorias c ON c.id=p.categoria_id
                    WHERE c.tipo=? AND p.activo=1 ORDER BY c.orden,p.orden,p.nombre""",
                    (inventory_type,),
                ).fetchall()
            for column, text in enumerate(("Código", "Producto", "Categoría", "Unidad", "")):
                ctk.CTkLabel(listing, text=text, font=ctk.CTkFont(weight="bold"), anchor="w").grid(row=0, column=column, sticky="ew", padx=5, pady=5)
            for row_index, product in enumerate(products, start=1):
                ctk.CTkLabel(listing, text=product["codigo"] or "—", width=90).grid(row=row_index, column=0, padx=5, pady=3)
                ctk.CTkLabel(listing, text=product["nombre"], anchor="w").grid(row=row_index, column=1, sticky="ew", padx=5, pady=3)
                ctk.CTkLabel(listing, text=product["categoria"], width=175, anchor="w").grid(row=row_index, column=2, padx=5, pady=3)
                ctk.CTkLabel(listing, text=product["unidad"], width=90, anchor="w").grid(row=row_index, column=3, padx=5, pady=3)
                actions = ctk.CTkFrame(listing, fg_color="transparent")
                actions.grid(row=row_index, column=4, padx=4, pady=2)
                ctk.CTkButton(actions, text="Editar", width=62, command=lambda product_id=product["id"]: self._edit_product(window, inventory_type, product_id, refresh)).pack(side="left", padx=2)
                ctk.CTkButton(actions, text="×", width=34, fg_color="#B33A3A", command=lambda product_id=product["id"], name=product["nombre"]: self._delete_product(window, product_id, name, refresh)).pack(side="left", padx=2)

        refresh()
        return window

    def _edit_product(self, manager, inventory_type, product_id, refresh_manager):
        with connect() as conn:
            product = None if product_id is None else conn.execute(
                """SELECT p.codigo,p.nombre,p.unidad,c.nombre AS categoria
                FROM inventario_productos p JOIN inventario_categorias c ON c.id=p.categoria_id
                WHERE p.id=?""", (product_id,),
            ).fetchone()
        dialog = ctk.CTkToplevel(manager)
        dialog.title("Añadir producto" if product is None else "Modificar producto")
        dialog.geometry("540x420")
        dialog.resizable(False, False)
        dialog.transient(manager)
        dialog.grab_set()
        values = {
            "category": ctk.StringVar(value="" if product is None else product["categoria"]),
            "code": ctk.StringVar(value="" if product is None else product["codigo"]),
            "name": ctk.StringVar(value="" if product is None else product["nombre"]),
            "unit": ctk.StringVar(value="UNIDADES" if product is None else product["unidad"]),
        }
        for label, key in (("Categoría", "category"), ("Código", "code"), ("Producto", "name"), ("Unidad", "unit")):
            ctk.CTkLabel(dialog, text=label).pack(anchor="w", padx=24, pady=(10, 3))
            ctk.CTkEntry(dialog, textvariable=values[key]).pack(fill="x", padx=24)

        def save_product():
            category = values["category"].get().strip()
            name = values["name"].get().strip()
            unit = values["unit"].get().strip()
            if not category or not name or not unit:
                messagebox.showerror("Producto", "Categoría, producto y unidad son obligatorios.", parent=dialog)
                return
            with transaction() as conn:
                category_row = conn.execute(
                    "SELECT id FROM inventario_categorias WHERE tipo=? AND nombre=?",
                    (inventory_type, category),
                ).fetchone()
                if category_row is None:
                    order = conn.execute(
                        "SELECT COALESCE(MAX(orden),-1)+1 FROM inventario_categorias WHERE tipo=?",
                        (inventory_type,),
                    ).fetchone()[0]
                    cursor = conn.execute(
                        "INSERT INTO inventario_categorias(tipo,nombre,orden) VALUES (?,?,?)",
                        (inventory_type, category, order),
                    )
                    category_id = cursor.lastrowid
                else:
                    category_id = category_row["id"]
                if product_id is None:
                    order = conn.execute(
                        "SELECT COALESCE(MAX(orden),-1)+1 FROM inventario_productos WHERE categoria_id=?",
                        (category_id,),
                    ).fetchone()[0]
                    conn.execute(
                        """INSERT INTO inventario_productos(categoria_id,codigo,nombre,unidad,orden)
                        VALUES (?,?,?,?,?)""",
                        (category_id, values["code"].get().strip(), name, unit, order),
                    )
                else:
                    conn.execute(
                        """UPDATE inventario_productos SET categoria_id=?,codigo=?,nombre=?,unidad=?
                        WHERE id=?""",
                        (category_id, values["code"].get().strip(), name, unit, product_id),
                    )
            preserved = {key: variable.get() for key, variable in self.entries.items()}
            self._render_form(preserved)
            refresh_manager()
            dialog.destroy()

        ctk.CTkButton(dialog, text="Guardar producto", command=save_product).pack(fill="x", padx=24, pady=22)

    def _delete_product(self, manager, product_id, name, refresh_manager):
        if not messagebox.askyesno("Eliminar producto", f"¿Eliminar «{name}» del inventario?", parent=manager):
            return
        with transaction() as conn:
            conn.execute("DELETE FROM inventario_productos WHERE id=?", (product_id,))
        preserved = {key: variable.get() for key, variable in self.entries.items() if key != product_id}
        self._render_form(preserved)
        refresh_manager()
