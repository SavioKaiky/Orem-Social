def generate_cpf(base: str) -> str:
    """Gera um CPF válido a partir de 9 dígitos (uso exclusivo em testes)."""
    digits = [int(c) for c in base]
    for _ in range(2):
        weight = len(digits) + 1
        total = sum(d * w for d, w in zip(digits, range(weight, 1, -1)))
        digits.append((total * 10) % 11 % 10)
    return "".join(map(str, digits))