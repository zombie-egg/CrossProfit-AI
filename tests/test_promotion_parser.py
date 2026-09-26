from decimal import Decimal

from backend.app.services.promotion_parser import PromotionParserService


def test_tiktok_pasted_rules_are_parsed_without_fetching():
    text = "活动名称: TikTok Summer Mega Sale\n折扣: 25%\n达人佣金: 12%\n预计销量: 500\n2026-06-01 至 2026-06-30"
    parsed = PromotionParserService().parse(raw_text=text)
    assert parsed.activity.platform == "tiktok_shop"
    assert parsed.activity.activity_name == "TikTok Summer Mega Sale"
    assert parsed.activity.discount_value == Decimal("0.25")
    assert parsed.activity.creator_commission_rate == Decimal("0.12")
    assert parsed.activity.estimated_sales == 500
    assert parsed.activity.start_date.isoformat() == "2026-06-01"
    assert parsed.activity.source_url is None


def test_platform_funded_discount_is_not_seller_discount():
    fields = PromotionParserService().extract_rule_candidates(
        "US Smart Promotion\nPlatform discount 3.5% for shoppers. Seller Give: 4.5% fee during campaign periods."
    )
    assert "discount_value" not in fields
    assert fields["activity_name"] == "US Smart Promotion"


def test_amazon_pasted_rules_and_platform_hint():
    text = "Promotion name: Prime Sale\nDiscount: 10%\nExtra commission: 1%"
    parsed = PromotionParserService().parse(raw_text=text, platform_hint="amazon")
    assert parsed.activity.platform == "amazon"
    assert parsed.activity.discount_value == Decimal("0.10")
    assert parsed.activity.extra_commission_rate == Decimal("0.01")
