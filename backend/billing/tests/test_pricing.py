from datetime import date
from decimal import Decimal

from billing.models import PricingConfig


def test_default_pricing_matches_report(db):
    pricing = PricingConfig.current()
    assert pricing.holder_amount == Decimal("32.42")
    assert pricing.dependent_amount == Decimal("16.21")


def test_family_totals_match_report_table(db):
    pricing = PricingConfig.current()
    totals = [pricing.total_for(n) for n in range(5)]
    assert totals == [
        Decimal("32.42"), Decimal("48.63"), Decimal("64.84"), Decimal("81.05"), Decimal("97.26"),
    ]


def test_new_minimum_wage_applies_only_from_its_date(db):
    PricingConfig.objects.create(valid_from=date(2027, 1, 1), minimum_wage=Decimal("1700.00"))
    assert PricingConfig.current(on=date(2026, 12, 31)).holder_amount == Decimal("32.42")
    assert PricingConfig.current(on=date(2027, 1, 1)).holder_amount == Decimal("34.00")


def test_pricing_endpoint_is_public(api_client, db):
    response = api_client.get("/api/billing/pricing/")
    assert response.status_code == 200
    assert response.data["holder_amount"] == Decimal("32.42")