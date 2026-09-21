import json
import os
from pathlib import Path

from core.paths import APP_DIR, SETTINGS_PATH


DEFAULT_SETTINGS = {
    "reports_directory": "informes",
    "app_name": "Mesa Clara",
    "font_scale": 1.0,
    "logo_path": "",
    "backup_on_start": False,
    "backup_directory": "",
    "appearance_mode": "Dark",
}


def load_settings() -> dict:
    settings = dict(DEFAULT_SETTINGS)
    try:
        saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(saved, dict):
            settings.update(saved)
    except (OSError, TypeError, json.JSONDecodeError):
        pass
    return settings


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(
        json.dumps({**DEFAULT_SETTINGS, **settings}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def reports_directory() -> Path:
    configured = Path(str(load_settings()["reports_directory"])).expanduser()
    return configured if configured.is_absolute() else APP_DIR / configured


def app_name() -> str:
    return str(load_settings().get("app_name") or DEFAULT_SETTINGS["app_name"]).strip()


def font_scale() -> float:
    try:
        return min(1.5, max(0.8, float(load_settings().get("font_scale", 1.0))))
    except (TypeError, ValueError):
        return 1.0


def appearance_mode() -> str:
    value = str(load_settings().get("appearance_mode", "Dark")).strip().lower()
    return "Light" if value == "light" else "Dark"


def logo_path() -> Path | None:
    value = str(load_settings().get("logo_path") or "").strip()
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else APP_DIR / path


def detected_onedrive_directory() -> Path | None:
    for variable in ("OneDriveCommercial", "OneDrive", "OneDriveConsumer"):
        value = os.environ.get(variable)
        if value:
            path = Path(value)
            if path.exists():
                return path
    return None


def backup_directory() -> Path | None:
    value = str(load_settings().get("backup_directory") or "").strip()
    if value:
        path = Path(value).expanduser()
        return path if path.is_absolute() else APP_DIR / path
    onedrive = detected_onedrive_directory()
    return onedrive / "Mesa Clara" / "Backups" if onedrive else None
