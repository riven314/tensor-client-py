from solders.keypair import Keypair


def get_keypair_from_private_key(private_key: str) -> Keypair:
    return Keypair.from_base58_string(private_key)
