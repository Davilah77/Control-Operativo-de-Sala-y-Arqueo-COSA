import unittest
from pathlib import Path
from unittest.mock import patch

from core import database
from core.settings import appearance_mode
from core.dates import parse_date, to_display, to_iso
from core.numbers import money, parse_decimal
from modules.recaudacion import RevenueModule
from modules.inventario_data import BODEGA, DESAYUNOS


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.original_path = database.DB_PATH
        database.DB_PATH = Path(__file__).parent / "_test_restaurante.db"
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(database.DB_PATH) + suffix)
            if candidate.exists():
                candidate.unlink()
        database.initialize_database()

    def tearDown(self):
        database.DB_PATH = self.original_path
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(Path(__file__).parent / "_test_restaurante.db") + suffix)
            if candidate.exists():
                candidate.unlink()

    def test_dates_accept_display_and_iso_formats(self):
        self.assertEqual(to_iso("21/09/2026"), "2026-09-21")
        self.assertEqual(to_display("2026-09-21"), "21/09/2026")
        self.assertEqual(parse_date("21/09/26").year, 2026)

    def test_spanish_decimal_input(self):
        self.assertEqual(parse_decimal("12,50 €"), parse_decimal("12.50"))
        self.assertEqual(str(money("4,2")), "4.20")
        with self.assertRaises(ValueError):
            parse_decimal("-1")

    def test_database_creates_catalogues_without_duplicates(self):
        database.initialize_database()
        with database.connect() as conn:
            article_count = conn.execute("SELECT COUNT(*) FROM articulos_todo_incluido").fetchone()[0]
            task_count = conn.execute("SELECT COUNT(*) FROM tareas_limpieza").fetchone()[0]
            inventory_count = conn.execute("SELECT COUNT(*) FROM inventario_productos").fetchone()[0]
        self.assertEqual(article_count, len(database.DEFAULT_ALL_INCLUSIVE_ITEMS))
        self.assertEqual(task_count, len(database.DEFAULT_CLEANING_TASKS))
        self.assertEqual(inventory_count, sum(len(items) for _category, items in BODEGA + DESAYUNOS))

    def test_revenue_uses_each_service_price_and_counts_menus(self):
        bases = {
            "efectivo_bodega": parse_decimal("10"),
            "visa_bodega": parse_decimal("20"),
            "credito_habitacion": parse_decimal("5"),
        }
        counts = {
            "efectivo_desayunos": 2, "efectivo_almuerzos": 1, "efectivo_cenas": 0,
            "visa_desayunos": 0, "visa_almuerzos": 1, "visa_cenas": 1,
            "credito_desayunos": 0, "credito_almuerzos": 0, "credito_cenas": 1,
        }
        prices = {
            "desayunos": parse_decimal("12"),
            "almuerzos": parse_decimal("25"),
            "cenas": parse_decimal("30"),
        }
        total, menus = RevenueModule._totals(bases, counts, prices)
        self.assertEqual(total, parse_decimal("169"))
        self.assertEqual(menus, 6)

    def test_buffet_table_is_available(self):
        with database.connect() as conn:
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(temperaturas_buffet)")}
        self.assertIn("producto_caliente", columns)
        self.assertIn("postre_t2", columns)

    def test_inventory_catalogues_are_loaded(self):
        warehouse_items = sum(len(items) for _category, items in BODEGA)
        breakfast_items = sum(len(items) for _category, items in DESAYUNOS)
        self.assertEqual(warehouse_items, 56)
        self.assertEqual(breakfast_items, 57)

    def test_appearance_mode_accepts_only_light_or_dark(self):
        with patch("core.settings.load_settings", return_value={"appearance_mode": "Light"}):
            self.assertEqual(appearance_mode(), "Light")
        with patch("core.settings.load_settings", return_value={"appearance_mode": "unexpected"}):
            self.assertEqual(appearance_mode(), "Dark")


if __name__ == "__main__":
    unittest.main()
