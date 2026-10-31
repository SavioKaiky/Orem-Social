import datetime

import pytest

from accounts.models import Role
from members.models import BeneficiaryProfile, State, TermsVersion


@pytest.fixture
def current_terms(db):
    return TermsVersion.objects.create(version="teste-1.0", content="Termos de teste", is_current=True)


@pytest.fixture
def make_beneficiary(make_user):
    """Cria um beneficiário já com perfil; sem obreiro informado, cria um novo."""

    def _make(worker=None, state=State.GO, **extra):
        if worker is None:
            worker = make_user(Role.WORKER).worker_profile
        user = make_user(Role.BENEFICIARY)
        return BeneficiaryProfile.objects.create(
            user=user,
            worker=worker,
            birth_date=datetime.date(1990, 1, 1),
            city="Goiânia",
            state=state,
            **extra,
        )

    return _make