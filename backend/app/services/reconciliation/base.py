from __future__ import annotations

import csv
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path

from pydantic import BaseModel, Field


MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10000
REQUIRED = ("order_id", "sku", "settled_at", "currency", "gross_revenue")


class SettlementLine(BaseModel):
    order_id: str
    sku: str
    settled_at: datetime
    currency: str
    gross_revenue: Decimal
    quantity: int = Field(default=1, ge=1, strict=True)
    fee_items: dict[str, Decimal] = Field(default_factory=dict)
    refund_amount: Decimal = Decimal("0")
    subsidy_amount: Decimal = Decimal("0")
    raw_row: dict[str, str] = Field(default_factory=dict)


class SettlementParseError(ValueError):
    pass


def amount(value: str, row_number: int, column: str) -> Decimal:
    stripped = value.strip().replace(",", "")
    if not stripped:
        return Decimal("0")
    if stripped.startswith("(") and stripped.endswith(")"):
        stripped = "-" + stripped[1:-1]
    try:
        number = Decimal(stripped)
        if not number.is_finite():
            raise InvalidOperation
        return number
    except InvalidOperation as exc:
        raise SettlementParseError(f"第 {row_number} 行，列 {column} 的金额无效：{value}") from exc


class SettlementParser(ABC):
    @property
    @abstractmethod
    def platform(self) -> str:
        """Platform key used to load the configured column template."""

    def template(self) -> dict:
        return json.loads((Path(__file__).parent / "column_templates.json").read_text(encoding="utf-8"))[self.platform]

    def parse(self, content: bytes, mapping: dict) -> tuple[list[SettlementLine], list[str]]:
        if len(content) > MAX_BYTES:
            raise SettlementParseError("CSV 超过 5 MB 上限")
        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                decoded = content.decode("gbk")
            except UnicodeDecodeError as exc:
                raise SettlementParseError("CSV 编码无法识别；请使用 UTF-8 BOM 或 GBK") from exc
        reader = csv.DictReader(StringIO(decoded, newline=""), strict=True)
        headers = reader.fieldnames or []
        if any(not name for name in headers):
            raise SettlementParseError("CSV 表头存在空列名")
        if len(headers) != len(set(headers)):
            raise SettlementParseError("CSV 存在重复列名")
        template = self.template()
        if any(not isinstance(mapping.get(key, {}), dict) for key in ("fields", "fee_columns", "fee_signs")):
            raise SettlementParseError("列映射 fields、fee_columns、fee_signs 必须是对象")
        fields = {**template["fields"], **mapping.get("fields", {})}
        fee_columns = {**template["fee_columns"], **mapping.get("fee_columns", {})}
        fee_signs = mapping.get("fee_signs", {})
        ignored = mapping.get("ignored_columns", [])
        if not isinstance(ignored, list) or any(not isinstance(name, str) or name not in headers for name in ignored):
            raise SettlementParseError("ignored_columns 必须是 CSV 中已确认的列名列表")
        if any(value not in (-1, 1) for value in fee_signs.values()):
            raise SettlementParseError("fee_signs 仅允许 1 或 -1")
        missing = [key for key in REQUIRED if not fields.get(key) or fields[key] not in headers]
        if missing:
            raise SettlementParseError(f"缺少必要列映射：{', '.join(missing)}；未识别的列：{', '.join(headers)}")
        if fields.get("quantity") and fields["quantity"] not in headers:
            raise SettlementParseError(f"件数列不存在：{fields['quantity']}；未识别的列：{', '.join(headers)}")
        absent_fees = [name for name in fee_columns if name not in headers]
        if absent_fees:
            raise SettlementParseError(f"费项列不存在：{', '.join(absent_fees)}；未识别的列：{', '.join(headers)}")
        if any(not isinstance(name, str) for name in [*fields.values(), *fee_columns.values()]):
            raise SettlementParseError("列名和费项名称必须是文本")
        used = set(fields.values()) | set(fee_columns) | set(ignored)
        unknown = [name for name in headers if name not in used]
        lines: list[SettlementLine] = []
        def checked_rows():
            while True:
                try:
                    yield next(reader)
                except StopIteration:
                    return
                except csv.Error as exc:
                    raise SettlementParseError(f"第 {reader.line_num} 行 CSV 格式错误：{exc}") from exc

        for row_number, row in enumerate(checked_rows(), start=2):
            if row_number > MAX_ROWS + 1:
                raise SettlementParseError(f"CSV 超过 {MAX_ROWS} 行上限")
            if None in row:
                raise SettlementParseError(f"第 {row_number} 行列数多于表头")
            try:
                order_id = (row[fields["order_id"]] or "").strip()
                sku = (row[fields["sku"]] or "").strip()
                currency = (row[fields["currency"]] or "").strip().upper()
                if not order_id or not sku or not currency:
                    raise ValueError("订单 ID、SKU 和币种不能为空")
                raw_date = (row[fields["settled_at"]] or "").strip()
                timestamp = datetime.strptime(raw_date, mapping["date_format"]) if mapping.get("date_format") else datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                quantity = 1
                if fields.get("quantity"):
                    raw_quantity = (row[fields["quantity"]] or "").strip()
                    if not re.fullmatch(r"[0-9]+", raw_quantity) or int(raw_quantity) < 1:
                        raise SettlementParseError(f"第 {row_number} 行，列 {fields['quantity']} 的件数必须是正整数：{raw_quantity}")
                    quantity = int(raw_quantity)
                fees: dict[str, Decimal] = {}
                for column, name in fee_columns.items():
                    fees[name] = fees.get(name, Decimal("0")) + amount(row[column] or "", row_number, column) * Decimal(fee_signs.get(column, 1))
                lines.append(SettlementLine(order_id=order_id, sku=sku, settled_at=timestamp, currency=currency,
                    gross_revenue=amount(row[fields["gross_revenue"]] or "", row_number, fields["gross_revenue"]), quantity=quantity,
                    fee_items=fees,
                    refund_amount=abs(amount(row[fields["refund_amount"]] or "", row_number, fields["refund_amount"])) if fields.get("refund_amount") in headers else Decimal("0"),
                    subsidy_amount=amount(row[fields["subsidy_amount"]] or "", row_number, fields["subsidy_amount"]) if fields.get("subsidy_amount") in headers else Decimal("0"),
                    raw_row={key: value or "" for key, value in row.items()}))
            except (ValueError, KeyError) as exc:
                if isinstance(exc, SettlementParseError):
                    raise
                raise SettlementParseError(f"第 {row_number} 行解析失败：{exc}") from exc
        if not lines:
            raise SettlementParseError("CSV 没有数据行")
        return lines, unknown
