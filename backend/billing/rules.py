"""Regras de negócio da cobrança. Mudou a regra, muda aqui."""

CYCLE_DAYS = 30  # cada pagamento cobre 30 dias corridos
GRACE_DAYS = 5  # prazo máximo após o vencimento antes de ficar inativo
CARENCE_DAYS = 120  # carência de 4 meses de adimplência contínua
RENEWAL_WINDOW_DAYS = 10  # a nova cobrança só pode ser gerada nos últimos 10 dias do ciclo
CHARGE_EXPIRATION_HOURS = 24  # validade do QR Code gerado
DUE_SOON_DAYS = 3  # lembrete de vencimento