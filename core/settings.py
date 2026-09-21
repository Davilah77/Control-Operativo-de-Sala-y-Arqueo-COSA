import json
from pathlib import Path

from core.paths import APP_DIR, SETTINGS_PATH


DEFAULT_SETTINGS = {
    "reports_directory": "informes",
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

