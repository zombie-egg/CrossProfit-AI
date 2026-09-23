from types import SimpleNamespace

from backend.app.services.llm.deepseek_provider import DeepSeekProvider


def _client(content: str, finish_reason: str = "stop"):
    message = SimpleNamespace(content=content)
    response = SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)])
    create = lambda **kwargs: response
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_deepseek_adds_only_qualitative_advice():
    provider = DeepSeekProvider("test-key", client=_client('{"suggestions":["先小规模验证退货与物流波动。","利润率可提升到30%。"]}'))
    original = ["按确定性公式得出的建议"]
    assert provider.enhance_recommendations({"unit_profit": "5.00"}, original) == original + ["先小规模验证退货与物流波动。"]
    assert provider.extract("活动额外佣金 5%") == {}


def test_deepseek_truncated_response_keeps_rules():
    provider = DeepSeekProvider("test-key", client=_client('{"suggestions":["建议"]}', "length"))
    assert provider.enhance_recommendations({}, ["原有建议"]) == ["原有建议"]
