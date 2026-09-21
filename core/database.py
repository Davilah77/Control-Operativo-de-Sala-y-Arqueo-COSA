import sqlite3
from contextlib import contextmanager

from core.paths import DB_PATH


DEFAULT_CLEANING_TASKS = (
    ("Limpieza máquina refrescos", "BARES"),
    ("Limpieza máquina cerveza", "BARES"),
    ("Limpieza máquina de vino", "BARES"),
    ("Limpieza cámaras de hielo", "BARES"),
    ("Limpieza cámaras bar", "BARES"),
    ("Limpieza cafeteras", "DESAYUNOS"),
    ("Limpieza máquina de zumo", "DESAYUNOS"),
    ("Limpieza jarras de leche", "DESAYUNOS"),
    ("Limpieza y retirada de tostadoras", "DESAYUNOS"),
    ("Desinfección de microondas", "CIERRES"),
    ("Limpieza de carros", "CARRERO, BUFFETIERS"),
    ("Retirada residuos orgánicos", "CARRERO, BUFFETIERS"),
    ("Retirada de residuos reciclables", "CARRERO, BUFFETIERS"),
    ("Limpieza de almacenes", "CIERRES"),
    ("Vaciado y limpieza lavavajillas", "CIERRES"),
    ("Toma de temperaturas", "MAITRE"),
)

DEFAULT_ALL_INCLUSIVE_ITEMS = (
    "Vino tinto", "Vino blanco", "Vino rosado", "Agua con gas",
    "Cerveza", "Cerveza 0,0", "Casera", "Nestea", "Aquarius",
    "Refrescos", "Tinto de verano", "Tónica", "Zumos", "Botella de agua",
)


class ClosingConnection(sqlite3.Connection):
    """Conexión que también se cierra al salir de un bloque ``with``."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def transaction():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database() -> None:
    with transaction() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS arqueo_caja (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                total_efectivo REAL NOT NULL,
                fondo_fijo REAL NOT NULL,
                almuerzo_efectivo REAL DEFAULT 0.0,
                cena_efectivo REAL DEFAULT 0.0,
                total_visa REAL DEFAULT 0.0,
                creditos TEXT,
                total_diario REAL NOT NULL,
                diferencia REAL NOT NULL,
                desglose_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS temperaturas_lavavajillas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                servicio TEXT NOT NULL,
                temp_lavado REAL NOT NULL,
                temp_aclarado REAL NOT NULL,
                correcto INTEGER DEFAULT 1,
                observaciones TEXT,
                responsable TEXT
            );

            CREATE TABLE IF NOT EXISTS recaudacion_diaria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL UNIQUE,
                efectivo_bodega REAL NOT NULL DEFAULT 0,
                efectivo_menu REAL NOT NULL DEFAULT 0,
                visa_bodega REAL NOT NULL DEFAULT 0,
                visa_menu REAL NOT NULL DEFAULT 0,
                credito_habitacion REAL NOT NULL DEFAULT 0,
                credito_menu REAL NOT NULL DEFAULT 0,
                precio_menu REAL NOT NULL DEFAULT 20,
                observaciones TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS app_metadata (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS articulos_todo_incluido (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                activo INTEGER NOT NULL DEFAULT 1,
                orden INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS consumos_todo_incluido (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                articulo_id INTEGER NOT NULL REFERENCES articulos_todo_incluido(id),
                cantidad INTEGER NOT NULL DEFAULT 0 CHECK(cantidad >= 0),
                UNIQUE(fecha, articulo_id)
            );

            CREATE TABLE IF NOT EXISTS tareas_limpieza (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                turno TEXT NOT NULL DEFAULT '',
                activo INTEGER NOT NULL DEFAULT 1,
                orden INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS asignaciones_limpieza (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                tarea_id INTEGER NOT NULL REFERENCES tareas_limpieza(id),
                responsable TEXT NOT NULL DEFAULT '',
                completado INTEGER NOT NULL DEFAULT 0,
                observaciones TEXT DEFAULT '',
                UNIQUE(fecha, tarea_id)
            );

            CREATE TABLE IF NOT EXISTS notas_limpieza (
                semana_inicio TEXT PRIMARY KEY,
                observaciones TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS temperaturas_buffet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                servicio TEXT NOT NULL,
                producto_caliente TEXT DEFAULT '',
                caliente_t1 REAL,
                caliente_t2 REAL,
                producto_frio TEXT DEFAULT '',
                frio_t1 REAL,
                frio_t2 REAL,
                producto_postre TEXT DEFAULT '',
                postre_t1 REAL,
                postre_t2 REAL,
                correcto INTEGER NOT NULL DEFAULT 1,
                responsable TEXT DEFAULT '',
                observaciones TEXT DEFAULT '',
                UNIQUE(fecha, servicio)
            );
            """
        )
        _ensure_column(conn, "temperaturas_lavavajillas", "responsable", "TEXT")
        revenue_columns = (
            ("efectivo_desayunos", "REAL NOT NULL DEFAULT 0"),
            ("efectivo_almuerzos", "REAL NOT NULL DEFAULT 0"),
            ("efectivo_cenas", "REAL NOT NULL DEFAULT 0"),
            ("visa_desayunos", "REAL NOT NULL DEFAULT 0"),
            ("visa_almuerzos", "REAL NOT NULL DEFAULT 0"),
            ("visa_cenas", "REAL NOT NULL DEFAULT 0"),
            ("credito_desayunos", "REAL NOT NULL DEFAULT 0"),
            ("credito_almuerzos", "REAL NOT NULL DEFAULT 0"),
            ("credito_cenas", "REAL NOT NULL DEFAULT 0"),
            ("precio_desayuno", "REAL NOT NULL DEFAULT 12"),
            ("precio_almuerzo", "REAL NOT NULL DEFAULT 25"),
            ("precio_cena", "REAL NOT NULL DEFAULT 25"),
        )
        for column, definition in revenue_columns:
            _ensure_column(conn, "recaudacion_diaria", column, definition)
        _migrate_revenue_v2(conn)
        conn.executemany(
            "INSERT OR IGNORE INTO articulos_todo_incluido(nombre, orden) VALUES (?, ?)",
            ((name, index) for index, name in enumerate(DEFAULT_ALL_INCLUSIVE_ITEMS)),
        )
        conn.executemany(
            "INSERT OR IGNORE INTO tareas_limpieza(nombre, turno, orden) VALUES (?, ?, ?)",
            ((name, shift, index) for index, (name, shift) in enumerate(DEFAULT_CLEANING_TASKS)),
        )


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _migrate_revenue_v2(conn: sqlite3.Connection) -> None:
    migrated = conn.execute(
        "SELECT 1 FROM app_metadata WHERE clave='revenue_v2_migrated'"
    ).fetchone()
    if migrated:
        return
    conn.execute(
        """UPDATE recaudacion_diaria SET
        efectivo_almuerzos = CASE WHEN precio_menu > 0 THEN efectivo_menu / precio_menu ELSE 0 END,
        visa_almuerzos = CASE WHEN precio_menu > 0 THEN visa_menu / precio_menu ELSE 0 END,
        credito_almuerzos = CASE WHEN precio_menu > 0 THEN credito_menu / precio_menu ELSE 0 END,
        precio_almuerzo = CASE WHEN precio_menu > 0 THEN precio_menu ELSE 25 END,
        precio_cena = CASE WHEN precio_menu > 0 THEN precio_menu ELSE 25 END"""
    )
    conn.execute(
        "INSERT INTO app_metadata(clave,valor) VALUES ('revenue_v2_migrated','1')"
    )
