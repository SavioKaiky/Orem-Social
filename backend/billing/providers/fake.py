from .base import Charge, PixProvider


class FakePixProvider(PixProvider):
    """Provedor simulado para desenvolvimento e testes. Não fala com nenhum banco."""

    def create_charge(self, *, txid, amount, description, expires_at):
        return Charge(txid=txid, copy_paste=f"FAKE-PIX|{txid}|{amount}")

    def get_payment(self, txid):
        return None