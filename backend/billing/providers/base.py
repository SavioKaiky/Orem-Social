import hmac
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime


@dataclass(frozen=True)
class Charge:
    """Cobrança criada no banco."""

    txid: str
    copy_paste: str


@dataclass(frozen=True)
class PixEvent:
    """Um PIX recebido (vindo do webhook ou da consulta ao banco)."""

    txid: str
    end_to_end_id: str
    amount: Decimal
    paid_at: datetime


class PixProvider(ABC):
    """Contrato que o provedor de PIX (simulado ou Banco do Brasil) precisa cumprir."""

    @abstractmethod
    def create_charge(self, *, txid: str, amount: Decimal, description: str, expires_at: datetime) -> Charge:
        """Cria a cobrança imediata e devolve o código copia e cola."""

    @abstractmethod
    def get_payment(self, txid: str) -> PixEvent | None:
        """Consulta o banco: devolve o pagamento se a cobrança já foi paga (usado se o webhook falhar)."""

    def verify_webhook(self, request) -> bool:
        """Confere o segredo enviado pelo banco. Sem segredo configurado, só aceita em desenvolvimento."""
        secret = settings.PIX_WEBHOOK_SECRET
        if not secret:
            return settings.DEBUG
        given = request.query_params.get("hmac") or request.headers.get("X-Webhook-Secret", "")
        return hmac.compare_digest(given, secret)

    def parse_webhook(self, payload) -> list[PixEvent]:
        """Lê o corpo do webhook no formato padrão do Banco Central: {"pix": [{...}]}."""
        items = payload.get("pix", []) if isinstance(payload, dict) else []
        events = []
        for item in items:
            try:
                paid_at = parse_datetime(item.get("horario") or "") or timezone.now()
                if timezone.is_naive(paid_at):
                    paid_at = timezone.make_aware(paid_at)
                events.append(
                    PixEvent(
                        txid=item.get("txid") or "",
                        end_to_end_id=item["endToEndId"],
                        amount=Decimal(str(item["valor"])),
                        paid_at=paid_at,
                    )
                )
            except (KeyError, InvalidOperation, TypeError, AttributeError):
                continue  # item malformado não derruba o processamento dos demais
        return events