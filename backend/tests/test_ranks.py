from decimal import Decimal

from sqlalchemy import select

from app.models import User, WalletTransaction


def add_transaction(db, user, transaction_type, amount, status):
    wallet = user.wallet
    db.add(
        WalletTransaction(
            wallet_id=wallet.id,
            user_id=user.id,
            type=transaction_type,
            amount=Decimal(amount),
            currency="USD",
            status=status,
            description="Ranks test transaction",
            balance_before=Decimal("0"),
            balance_after=Decimal("0"),
        )
    )


def test_ranks_requires_auth_and_scores_only_approved_ads_and_completed_packages(client):
    assert client.get("/api/v1/ranks").status_code == 401
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    )
    assert login.status_code == 200

    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "workbit-user@example.com"))
        admin = db.scalar(select(User).where(User.email == "workbit-admin@example.com"))
        assert user is not None and admin is not None
        user_name = user.full_name
        admin_name = admin.full_name
        add_transaction(db, user, "OFFER_REWARD_APPROVAL", "20", "APPROVED")
        add_transaction(db, user, "PACKAGE_PURCHASE", "-30", "COMPLETED")
        add_transaction(db, user, "OFFER_REWARD_APPROVAL", "100", "PENDING")
        add_transaction(db, user, "REFERRAL_REWARD_APPROVAL", "100", "APPROVED")
        add_transaction(db, user, "PACKAGE_PURCHASE", "-100", "PENDING")
        add_transaction(db, admin, "PACKAGE_PURCHASE", "-200", "COMPLETED")
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/ranks")
    assert response.status_code == 200
    result = response.json()
    current = result["current_user"]
    assert result["currency"] == "USD"
    assert [(tier["name"], Decimal(tier["threshold"])) for tier in result["tiers"]] == [
        ("Starter", Decimal("0")),
        ("Bronze", Decimal("50")),
        ("Silver", Decimal("200")),
        ("Gold", Decimal("500")),
    ]
    assert Decimal(current["qualifying_value"]) == Decimal("50")
    assert current["rank"] == "Bronze"
    assert current["next_rank"] == "Silver"
    assert Decimal(current["amount_to_next"]) == Decimal("150")

    leaderboard = result["leaderboard"]
    assert leaderboard[0]["full_name"] == admin_name
    assert Decimal(leaderboard[0]["qualifying_value"]) == Decimal("200")
    assert leaderboard[0]["rank"] == "Silver"
    assert leaderboard[-1]["full_name"] == user_name
    assert leaderboard[-1]["position"] == 2
