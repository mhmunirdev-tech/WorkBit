"""Development seed. Never run these credentials in a production environment."""
from sqlalchemy import select
from app.database.session import SessionLocal
from decimal import Decimal
from app.models import AdNetwork, OfferNetwork, Permission, RewardPolicy, Role, User, Wallet
from app.security.passwords import hash_password
PERMISSIONS = ["users.view", "users.edit", "users.suspend", "wallets.view", "withdrawals.view", "withdrawals.review", "offers.view", "offers.manage", "settings.manage", "admins.manage"]
OFFER_PROVIDERS = (
    ("Lootably", "lootably", 10),
    ("AdGem", "adgem", 20),
    ("CPAlead", "cpalead", 30),
    ("Offerwall.GG", "offerwall-gg", 40),
    ("Monlix", "monlix", 50),
    ("BitLabs", "bitlabs", 60),
    ("AdGate Media", "adgate", 70),
    ("Torox", "torox", 80),
    ("AdswedMedia", "adswedmedia", 90),
    ("RevU", "revu", 100),
)
AD_NETWORKS = (
    ("WorkBit Ad Manager", "workbit-ad-manager", "AD_MANAGER", 10),
    ("Other Ads", "other-ads", "DISPLAY", 100),
)


def seed() -> None:
    db = SessionLocal()
    try:
        permissions = {}
        for name in PERMISSIONS:
            item = db.scalar(select(Permission).where(Permission.name == name)) or Permission(name=name)
            db.add(item); permissions[name] = item
        roles = {}
        for name in ("USER", "MODERATOR", "ADMIN", "SUPER_ADMIN"):
            item = db.scalar(select(Role).where(Role.name == name)) or Role(name=name, description=f"{name.title()} role")
            db.add(item); roles[name] = item
        db.flush(); roles["ADMIN"].permissions = list(permissions.values()); roles["SUPER_ADMIN"].permissions = list(permissions.values())
        for name, slug, priority in OFFER_PROVIDERS:
            if not db.scalar(select(OfferNetwork).where(OfferNetwork.slug == slug)):
                env_prefix = slug.upper().replace("-", "_")
                db.add(OfferNetwork(
                    name=name,
                    provider=env_prefix,
                    slug=slug,
                    enabled=False,
                    api_key_env=f"{env_prefix}_API_KEY",
                    secret_key_env=f"{env_prefix}_POSTBACK_SECRET",
                    postback_url=f"/api/v1/postbacks/{slug}",
                    integration_type="OFFERWALL",
                    country_support="[]",
                    device_support="[]",
                    priority=priority,
                    status="NOT_CONFIGURED",
                ))
        for name, slug, integration_type, priority in AD_NETWORKS:
            if not db.scalar(select(AdNetwork).where(AdNetwork.slug == slug)):
                db.add(AdNetwork(
                    name=name,
                    slug=slug,
                    enabled=False,
                    integration_type=integration_type,
                    country_support="[]",
                    device_support="[]",
                    priority=priority,
                    status="NOT_CONFIGURED",
                ))
        existing_policy = db.scalar(select(RewardPolicy).where(RewardPolicy.name == "default_offer_reward"))
        if not existing_policy:
            db.add(RewardPolicy(name="default_offer_reward", description="Default offer reward policy", enabled=True, user_reward_percentage=Decimal("70.00"), platform_share_percentage=Decimal("30.00"), minimum_reward=Decimal("0.10"), maximum_reward=Decimal("25.00"), pending_period_days=0, rounding_precision=2, country_code=None, network_id=None, offer_id=None))
        for email, role in (("workbit-admin@example.com", roles["ADMIN"]), ("workbit-user@example.com", roles["USER"])):
            if not db.scalar(select(User).where(User.email == email)):
                user = User(email=email, password_hash=hash_password("WorkBitDev123!"), full_name="Development " + role.name.title(), country="US", referral_code=("WBADMIN01" if role.name == "ADMIN" else "WBUSER001"), status="ACTIVE", email_verified=True)
                user.roles.append(role); user.wallet = Wallet(); db.add(user)
        db.commit()
    finally: db.close()
if __name__ == "__main__": seed()
