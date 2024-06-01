from src.constants import SOLAMI_UNIT


def to_solami(price: float) -> int:
    return int(price * SOLAMI_UNIT)


def from_solami(price):
    return float(price) / SOLAMI_UNIT
