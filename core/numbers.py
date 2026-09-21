from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def parse_decimal(value, *, minimum: Decimal | None = Decimal("0")) -> Decimal:
    text = str(value).strip().replace("€", "").replace(" ", "").replace(",", ".")
    if not text:
        number = Decimal("0")
    else:
        try:
            number = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"'{value}' no es un número válido.") from exc
    if minimum is not None and number < minimum:
        raise ValueError(f"El valor no puede ser menor que {minimum}.")
    return number


def money(value) -> Decimal:
    return parse_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_money(value) -> str:
    return f"{Decimal(str(value)):.2f} €"

