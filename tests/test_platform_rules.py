from backend.app.services.platforms import get_adapter


def test_platform_defaults_are_distinct_and_disclaimed():
    tik = get_adapter("tiktok_shop").get_default_fee_rules()
    amazon = get_adapter("amazon").get_default_fee_rules()
    assert tik["platform_commission_rate"] != amazon["platform_commission_rate"]
    assert tik["demo_default"] and "DEMO DEFAULT" in tik["disclaimer"]


def test_future_platform_adapters_exist():
    assert get_adapter("temu").name == "temu"
    assert get_adapter("shein").name == "shein"

