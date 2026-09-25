"""Normalización explícita: nunca adivinar fechas, moneda ni precio."""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def normalize(value, field):
    if value is None or str(value).strip() == "":
        return None
    value = str(value).strip()
    if field.kind == "bool":
        if value not in ("0", "1"):
            raise ValueError("invalid_boolean")
    elif field.kind == "integer":
        if not re.fullmatch(r"\d+", value):
            raise ValueError("invalid_integer")
        value = str(int(value))
    elif field.kind == "decimal":
        if not re.fullmatch(r"-?\d+(\.\d+)?", value):
            raise ValueError("invalid_decimal")
        try:
            number = Decimal(value)
            if not number.is_finite():
                raise ValueError("invalid_decimal")
            # Decimal.normalize applies context precision and can silently round large inputs.
            value = format(number, "f")
            if "." in value:
                value = value.rstrip("0").rstrip(".")
            if number == 0:
                value = "0"
        except InvalidOperation as exc:
            raise ValueError("invalid_decimal") from exc
    elif field.kind in ("date", "time"):
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                date.fromisoformat(value)
            elif field.kind == "time" and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?", value):
                datetime.fromisoformat(value)
            else:
                raise ValueError()
        except ValueError as exc:
            raise ValueError("invalid_iso_date") from exc
    if field.choices and value not in field.choices:
        raise ValueError("invalid_category")
    return value


def on_or_before(known, score):
    """Same-day precision mismatch cannot establish intraday ordering."""
    if not known or not score:
        return False
    if known[:10] < score[:10]:
        # Offsets may cross calendar days: compare aware instants when possible.
        if "T" not in known or "T" not in score:
            return True
    if "T" not in known or "T" not in score:
        return known == score and "T" not in known and "T" not in score
    a, b = datetime.fromisoformat(known), datetime.fromisoformat(score)
    if a.tzinfo is None or b.tzinfo is None:
        return False
    return a <= b
