"""Development seed. Never run these credentials in a production environment."""
from sqlalchemy import select
from app.database.session import SessionLocal
from decimal import Decimal
from app.core.config import settings
from app.models import AdNetwork, Offer, OfferNetwork, Permission, RankTier, RewardPolicy, Role, User, Wallet
from app.services.packages import seed_earning_packages
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
RANK_TIERS = (
    ("Starter", Decimal("0"), 0),
    ("Bronze", Decimal("50"), 1),
    ("Silver", Decimal("200"), 2),
    ("Gold", Decimal("500"), 3),
)
DEMO_OFFER_APIS = (
    ("Demo Games API", "workbit-development-mock", '["WEB","MOBILE"]', 10),
    ("Demo Surveys API", "workbit-demo-surveys", '["WEB","MOBILE"]', 20),
    ("Demo Apps API", "workbit-demo-apps", '["WEB","IOS","ANDROID"]', 30),
)
DEVELOPMENT_OFFERS = (
    ("workbit-development-mock", "mock-game", "mock-game", "Install Demo Game", "A development-only example offer.", "GAME", "MOBILE", Decimal("0.60"), Decimal("0.50"), 20, "Medium", True),
    ("workbit-demo-surveys", "mock-survey", "mock-survey", "Complete Demo Survey", "A development-only feedback survey.", "SURVEY", "WEB", Decimal("0.30"), Decimal("0.25"), 8, "Easy", False),
    ("workbit-demo-apps", "mock-signup", "mock-signup", "Create Demo Account", "A development-only registration example.", "SIGNUP", "WEB", Decimal("0.90"), Decimal("0.75"), 5, "Easy", True),
    ("workbit-development-mock", "mock-game-puzzle", "mock-game-puzzle", "Play the Puzzle Challenge", "Try a sample browser and mobile game offer from the demo feed.", "GAME", "WEB", Decimal("0.80"), Decimal("0.65"), 15, "Easy", False),
    ("workbit-demo-surveys", "mock-survey-feedback", "mock-survey-feedback", "Share Your Shopping Feedback", "Answer a sample product feedback survey from the demo feed.", "SURVEY", "MOBILE", Decimal("0.55"), Decimal("0.45"), 10, "Easy", True),
    ("workbit-demo-apps", "mock-app-fitness", "mock-app-fitness", "Try a Fitness App", "Explore a sample app discovery offer from the demo feed.", "APP", "ANDROID", Decimal("1.20"), Decimal("1.00"), 25, "Medium", True),
)

def seed_demo_offers(db) -> None:
    demo_networks = {}
    for name, slug, device_support, priority in DEMO_OFFER_APIS:
        network = db.scalar(
            select(OfferNetwork).where(OfferNetwork.slug == slug)
        )
        if network is None:
            network = OfferNetwork(
                name=name,
                provider="MOCK",
                slug=slug,
                enabled=False,
                integration_type="MOCK",
                country_support='["US"]',
                device_support=device_support,
                priority=priority,
                status="DEVELOPMENT_ONLY",
            )
            db.add(network)
        else:
            network.name = name
            network.provider = "MOCK"
            network.enabled = False
            network.integration_type = "MOCK"
            network.device_support = device_support
            network.priority = priority
            network.status = "DEVELOPMENT_ONLY"
        demo_networks[slug] = network
    db.flush()
    for (
        network_slug,
        offer_id,
        external_offer_id,
        title,
        short_description,
        category,
        device_type,
        payout,
        user_reward,
        estimated_time,
        difficulty,
        featured,
    ) in DEVELOPMENT_OFFERS:
        offer = db.scalar(select(Offer).where(Offer.id == offer_id))
        if offer is None:
            offer = Offer(id=offer_id)
            db.add(offer)
        offer.network_id = demo_networks[network_slug].id
        offer.external_offer_id = external_offer_id
        offer.title = title
        offer.description = short_description
        offer.short_description = short_description
        offer.category = category
        offer.country = "US"
        offer.device_type = device_type
        offer.payout = payout
        offer.user_reward = user_reward
        offer.currency = "USD"
        offer.estimated_time_minutes = estimated_time
        offer.difficulty = difficulty
        offer.status = "PUBLISHED"
        offer.featured = featured


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
        if settings.environment == "development":
            seed_demo_offers(db)
        seed_earning_packages(db)
        existing_policy = db.scalar(select(RewardPolicy).where(RewardPolicy.name == "default_offer_reward"))
        if not existing_policy:
            db.add(RewardPolicy(name="default_offer_reward", description="Default offer reward policy", enabled=True, user_reward_percentage=Decimal("80.00"), platform_share_percentage=Decimal("20.00"), minimum_reward=Decimal("0.00"), maximum_reward=Decimal("0.00"), pending_period_days=0, rounding_precision=2, country_code=None, network_id=None, offer_id=None))
        if not db.scalar(select(RankTier.id).limit(1)):
            db.add_all(
                RankTier(name=name, threshold=threshold, sort_order=sort_order)
                for name, threshold, sort_order in RANK_TIERS
            )
        for email, role in (("workbit-admin@example.com", roles["ADMIN"]), ("workbit-user@example.com", roles["USER"])):
            if not db.scalar(select(User).where(User.email == email)):
                user = User(email=email, password_hash=hash_password("WorkBitDev123!"), full_name="Development " + role.name.title(), country="US", referral_code=("WBADMIN01" if role.name == "ADMIN" else "WBUSER001"), status="ACTIVE", email_verified=True)
                user.roles.append(role); user.wallet = Wallet(); db.add(user)
        db.commit()
    finally: db.close()
if __name__ == "__main__": seed()
