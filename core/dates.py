from datetime import date, datetime


DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y")


def parse_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("La fecha debe tener el formato DD/MM/AAAA.")


def to_iso(value: str | date | datetime) -> str:
    return parse_date(value).isoformat()


def to_display(value: str | date | datetime) -> str:
    return parse_date(value).strftime("%d/%m/%Y")


def today_display() -> str:
    return date.today().strftime("%d/%m/%Y")

