from decimal import Decimal

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models import User, WithdrawalRequest
from conftest import activate_package


def test_public_stats_are_database_backed_and_require_no_login(client):
    response = client.get("/api/v1/public/stats")

    assert response.status_code == 200
    stats = response.json()
    assert stats["registered_users"] > 0
    assert Decimal(stats["total_payouts_bdt"]) == Decimal("0")
    assert stats["active_packages"] == 0
    assert stats["offer_approval_rate"] is None
    assert "email" not in stats

    activate_package(client, "PUBLICSTATS001")
    updated = client.get("/api/v1/public/stats").json()
    assert updated["active_packages"] == 1


def test_public_stats_include_only_paid_bdt_withdrawals(client):
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "workbit-user@example.com"))
        assert user is not None
        db.add_all(
            [
                WithdrawalRequest(
                    user_id=user.id,
                    amount=Decimal("5.00"),
                    currency="USD",
                    payout_amount=Decimal("600.00"),
                    payout_currency="BDT",
                    exchange_rate=Decimal("120.00"),
                    method="BKASH",
                    destination_ciphertext="encrypted-test-value",
                    destination_hint="••••1234",
                    status="PAID",
                ),
                WithdrawalRequest(
                    user_id=user.id,
                    amount=Decimal("10.00"),
                    currency="USD",
                    payout_amount=Decimal("1200.00"),
                    payout_currency="BDT",
                    exchange_rate=Decimal("120.00"),
                    method="NAGAD",
                    destination_ciphertext="encrypted-test-value",
                    destination_hint="••••5678",
                    status="PROCESSING",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    stats = client.get("/api/v1/public/stats").json()
    assert Decimal(stats["total_payouts_bdt"]) == Decimal("600")
