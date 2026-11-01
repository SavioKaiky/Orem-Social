"""Textos exibidos no app para escolher a forma de pagamento da mensalidade."""

PAYMENT_METHODS = [
    {
        "code": "pix_automatic",
        "title": "Pix Automático",
        "recommended": True,
        "description": (
            "Você autoriza uma única vez e, todo mês, a mensalidade é paga sozinha no vencimento. "
            "Sem esquecimento, sem risco de ficar inativo e com a carência sempre em dia. "
            "É a melhor opção para a mensalidade, e você pode cancelar quando quiser."
        ),
    },
    {
        "code": "pix_manual",
        "title": "PIX manual",
        "recommended": False,
        "description": (
            "Todo mês você gera o QR Code (ou copia o código) e paga pelo aplicativo do seu banco. "
            "Funciona em qualquer banco, mas exige lembrar de pagar até o vencimento (há 5 dias de tolerância). "
            "Passou do prazo, os benefícios são suspensos e a carência recomeça."
        ),
    },
]