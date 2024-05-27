SOL_UNIT = 1_000_000_000


def to_solami(price: float) -> int:
    return int(price * SOL_UNIT)


def from_solami(price):
    return float(price) / SOL_UNIT
