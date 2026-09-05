from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import Base, Product, PromotionActivity
from backend.app.services.demo_data import seed_demo_data
from backend.app.services.factories import request_from_models
from backend.app.services.profit_engine import ProfitEngine


def test_demo_cases_cover_healthy_caution_and_loss():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_demo_data(session)
        product = session.scalar(select(Product).where(Product.sku == "PB-001").options(selectinload(Product.platform_configs)))
        activities = session.scalars(select(PromotionActivity).where(PromotionActivity.product_id == product.id)).all()
        results = {}
        for activity in activities:
            config = next(c for c in product.platform_configs if c.platform == activity.platform)
            results[activity.activity_name] = ProfitEngine().calculate(request_from_models(product, config, activity))
    assert results["Amazon Prime Promotion"].profit_margin >= 0.20
    assert 0.03 <= results["TikTok Summer Mega Sale"].profit_margin < 0.10
    assert results["TikTok Creator Flash Sale"].unit_profit < 0
