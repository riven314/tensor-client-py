from src.constants import SOL_UNIT


def to_solami(price: float) -> int:
    return int(price * SOL_UNIT)


def from_solami(price):
    return float(price) / SOL_UNIT
