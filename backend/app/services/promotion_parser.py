from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any

from ..schemas.domain import ParsedPromotion, PromotionActivityInput
from .llm import get_llm_provider
from .scraper import GenericScraper, ScraperError


MISSING_HELP = {
    "platform_commission_rate": ("平台佣金率", "用于计算平台从活动成交额中扣除的基础佣金。"),
    "extra_commission_rate": ("平台额外佣金率", "用于计算参加活动新增的扣费。"),
    "creator_commission_rate": ("达人佣金", "若通过联盟达人销售，需要计入真实成本。"),
    "estimated_sales": ("活动预计销量", "用于计算活动总营业额和总利润。"),
    "return_rate_override": ("活动退货率", "用于评估退货造成的不可回收成本风险。"),
    "seller_shipping_cost": ("卖家物流成本", "用于计算单件履约费用；可采用商品平台配置。"),
}


class PromotionParserService:
    def __init__(self, scraper: GenericScraper | None = None):
        self.scraper = scraper or GenericScraper()
        self.llm = get_llm_provider()

    def parse(self, url: str | None = None, raw_text: str = "", platform_hint: str | None = None) -> ParsedPromotion:
        warning = None
        text = raw_text.strip()
        if url:
            try:
                page = self.fetch_url(url)
                text = f"{self.extract_page_content(page)}\n{text}".strip()
            except ScraperError as exc:
                warning = f"{exc}。你仍然可以粘贴活动规则文本，系统会继续帮你识别。"
        fields = self.normalize_fields(self.extract_rule_candidates(text))
        if platform_hint:
            fields["platform"] = platform_hint
        if not fields.get("platform"):
            fields["platform"] = self.detect_platform(f"{url or ''} {text}")
        try:
            llm_fields = self.llm.extract(text) if text else {}
            for key, value in llm_fields.items():
                fields.setdefault(key, value)
        except Exception:
            warning = (warning + " " if warning else "") + "AI 辅助暂不可用，已自动切换到规则分析模式。"
        recognized = {k: v for k, v in fields.items() if v not in (None, "")}
        defaults: dict[str, Any] = {"platform": fields.get("platform", "unknown"), "activity_name": fields.get("activity_name", "未命名活动"), "raw_text": text, "source_url": url}
        defaults.update(fields)
        activity = PromotionActivityInput.model_validate(defaults)
        self.validate_fields(activity)
        missing = [item["field"] for item in self.generate_missing_field_suggestions(recognized)]
        activity.missing_fields = missing
        activity.parse_confidence = self.calculate_confidence(recognized)
        suggestions = self.generate_missing_field_suggestions(recognized)
        return ParsedPromotion(activity=activity, recognized_fields=recognized, missing_suggestions=suggestions, fetch_warning=warning)

    def fetch_url(self, url: str):
        return self.scraper.fetch(url)

    @staticmethod
    def extract_page_content(page) -> str:
        return page.text

    @staticmethod
    def normalize_fields(fields: dict[str, Any]) -> dict[str, Any]:
        if fields.get("platform"):
            fields["platform"] = str(fields["platform"]).strip().lower().replace(" ", "_")
        return fields

    @staticmethod
    def validate_fields(activity: PromotionActivityInput) -> list[str]:
        warnings: list[str] = []
        if activity.platform == "unknown":
            warnings.append("未识别平台")
        if activity.discount_type == "none":
            warnings.append("未识别折扣")
        return warnings

    @staticmethod
    def calculate_confidence(recognized: dict[str, Any]) -> Decimal:
        key_fields = ["platform", "activity_name", "discount_value", "estimated_sales", "extra_commission_rate", "creator_commission_rate"]
        hit = sum(1 for key in key_fields if key in recognized and recognized[key] != "unknown")
        return (Decimal(hit) / Decimal(len(key_fields))).quantize(Decimal("0.01"))

    @staticmethod
    def generate_missing_field_suggestions(recognized: dict[str, Any]) -> list[dict[str, str]]:
        return [{"field": key, "label": label, "reason": reason, "default_action": "采用商品平台配置或 0"} for key, (label, reason) in MISSING_HELP.items() if key not in recognized]

    def detect_platform(self, text: str) -> str:
        lower = text.lower()
        if "tiktok" in lower or "抖音" in lower:
            return "tiktok_shop"
        if "amazon" in lower or "prime" in lower or "亚马逊" in lower:
            return "amazon"
        if "temu" in lower:
            return "temu"
        if "shein" in lower:
            return "shein"
        return "unknown"

    def extract_rule_candidates(self, text: str) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        if not text:
            return fields
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title_match = re.search(r"(?:活动名称|promotion(?: name)?|campaign)\s*[:：-]\s*([^\n]+)", text, re.I)
        fields["activity_name"] = title_match.group(1).strip() if title_match else (lines[0][:120] if lines else "未命名活动")
        discount = re.search(r"(?:折扣|discount|off)\D{0,20}(\d+(?:\.\d+)?)\s*%", text, re.I)
        if not discount:
            discount = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:折扣|discount|off)", text, re.I)
        if discount:
            fields.update(discount_type="percentage", discount_value=Decimal(discount.group(1)) / 100)
        patterns = {
            "extra_commission_rate": r"(?:额外|extra|additional)[^\n%]{0,30}(?:佣金|commission|fee)[^\d]{0,10}(\d+(?:\.\d+)?)\s*%",
            "creator_commission_rate": r"(?:达人|creator|affiliate)[^\n%]{0,30}(?:佣金|commission)[^\d]{0,10}(\d+(?:\.\d+)?)\s*%",
            "platform_commission_rate": r"(?:平台|platform|referral)[^\n%]{0,30}(?:佣金|commission|fee)[^\d]{0,10}(\d+(?:\.\d+)?)\s*%",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.I)
            if match:
                fields[key] = Decimal(match.group(1)) / 100
        sales = re.search(r"(?:预计销量|estimated sales|sales forecast)\D{0,10}(\d+)", text, re.I)
        if sales:
            fields["estimated_sales"] = int(sales.group(1))
        date_range = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\s*(?:至|to|~|—|-)\s*(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", text, re.I)
        if date_range:
            nums = [int(x) for x in date_range.groups()]
            fields["start_date"] = date(*nums[:3])
            fields["end_date"] = date(*nums[3:])
        fields["platform"] = self.detect_platform(text)
        return fields
