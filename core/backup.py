import sqlite3
from datetime import datetime
from pathlib import Path

from core.paths import DB_PATH
from core.settings import backup_directory, load_settings


def create_database_backup(destination: Path | None = None) -> Path:
    target_directory = destination or backup_directory()
    if target_directory is None:
        raise RuntimeError("No se ha encontrado ni configurado una carpeta de OneDrive.")
    target_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = target_directory / f"mesa_clara_{timestamp}.db"
    with sqlite3.connect(DB_PATH) as source, sqlite3.connect(target) as output:
        source.backup(output)
    return target


def backup_on_start_if_enabled() -> Path | None:
    if not bool(load_settings().get("backup_on_start", False)):
        return None
    return create_database_backup()
