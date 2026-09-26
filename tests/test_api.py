from __future__ import annotations

import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.api import auth
from backend.app.database import get_db, install_snapshot_guards, register_snapshot_cleanup
from backend.app.main import app
from backend.app.models import Base, CalibratedParameter, CaptchaChallenge, ForecastSnapshot, PlatformConnection, ReconciliationReport, SettlementImport, VerificationCode


@pytest.fixture
def clients(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    register_snapshot_cleanup(engine)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        install_snapshot_guards(connection)
    def test_db():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_db] = test_db
    sent: dict[str, str] = {}
    monkeypatch.setattr(auth, "_send_code", lambda email, code, purpose: sent.__setitem__(email, code))
    monkeypatch.setattr(auth.secrets, "choice", lambda alphabet: "A")
    try:
        with TestClient(app) as first, TestClient(app) as second:
            yield first, second, sent, engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def register(client: TestClient, sent: dict[str, str], email: str):
    assert client.post("/auth/code", json={"email": email, "purpose": "register"}).status_code == 200
    response = client.post("/auth/register", json={"email": email, "code": sent[email], "password": "strong-pass-123"})
    assert response.status_code == 200
    assert response.cookies.get(auth.COOKIE_NAME)
    return response.json()


def password_login(client: TestClient, email: str, password: str, answer: str = "AAAAA"):
    challenge = client.get("/auth/captcha")
    assert challenge.status_code == 200
    assert challenge.json()["image"].startswith("data:image/png;base64,")
    return client.post("/auth/login", json={"email": email, "password": password,
                                             "captcha_token": challenge.json()["token"], "captcha_answer": answer})


def test_auth_and_password_recovery(clients):
    first, _, sent, engine = clients
    assert first.get("/health").status_code == 200
    assert first.get("/products").status_code == 401
    account = register(first, sent, "a@example.com")
    assert first.get("/auth/me").json()["id"] == account["id"]
    assert first.put("/auth/locale", json={"locale": "en"}).json()["locale"] == "en"
    assert first.post("/auth/logout").status_code == 200
    assert first.get("/products").status_code == 401
    assert password_login(first, "a@example.com", "wrong").status_code == 401
    assert password_login(first, "a@example.com", "strong-pass-123").status_code == 200
    with Session(engine) as db:
        row = db.scalar(select(VerificationCode).where(VerificationCode.email == "a@example.com"))
        assert row
        row.sent_at -= timedelta(seconds=61)
        db.commit()
    assert first.post("/auth/code", json={"email": "a@example.com", "purpose": "reset"}).status_code == 200
    assert first.post("/auth/reset-password", json={"email": "a@example.com", "code": sent["a@example.com"], "password": "new-password-456"}).status_code == 200
    assert password_login(first, "a@example.com", "strong-pass-123").status_code == 401
    assert password_login(first, "a@example.com", "new-password-456").status_code == 200


def test_merchant_isolation_and_multiple_platform_connections(clients):
    first, second, sent, engine = clients
    register(first, sent, "a@example.com")
    register(second, sent, "b@example.com")
    product = {"name": "同款商品", "sku": "SKU-1", "purchase_cost": "8", "packaging_cost": "1", "weight_kg": "0", "volume_cm3": "0", "currency": "USD"}
    a_product = first.post("/products", json=product)
    b_product = second.post("/products", json=product)
    assert a_product.status_code == b_product.status_code == 201
    a_id, b_id = a_product.json()["id"], b_product.json()["id"]
    assert a_id != b_id
    assert first.get(f"/products/{b_id}").status_code == 404
    assert first.put(f"/products/{b_id}", json=product).status_code == 404
    assert first.delete(f"/products/{b_id}").status_code == 404
    assert [x["id"] for x in first.get("/ui/bootstrap").json()["products"]] == [a_id]
    assert [x["id"] for x in second.get("/ui/bootstrap").json()["products"]] == [b_id]

    credentials = {"platform": "tiktok_shop", "label": "旗舰店", "shop_id": "shop-1", "app_key": "private-key", "app_secret": "private-secret"}
    connection = first.post("/connections", json=credentials)
    assert connection.status_code == 201
    assert "private-key" not in connection.text
    assert second.get("/connections").json() == []
    assert first.post("/connections", json={**credentials, "platform": "amazon"}).status_code == 201
    assert first.post("/connections", json={**credentials, "platform": "douyin"}).status_code == 422
    assert len(first.get("/connections").json()) == 2
    with Session(engine) as db:
        stored = db.scalar(select(PlatformConnection).where(PlatformConnection.id == connection.json()["id"]))
        assert stored and stored.app_key_encrypted != "private-key"
    assert second.delete(f"/connections/{connection.json()['id']}").status_code == 404


def test_password_login_rate_limit(clients):
    first, _, sent, _ = clients
    register(first, sent, "limited@example.com")
    first.post("/auth/logout")
    for _ in range(10):
        assert password_login(first, "limited@example.com", "wrong").status_code == 401
    assert password_login(first, "limited@example.com", "strong-pass-123").status_code == 429


def test_image_captcha_expires_and_cannot_be_reused(clients):
    first, _, sent, engine = clients
    register(first, sent, "captcha@example.com")
    first.post("/auth/logout")
    challenge = first.get("/auth/captcha").json()
    payload = {"email": "captcha@example.com", "password": "strong-pass-123",
               "captcha_token": challenge["token"], "captcha_answer": "WRONG"}
    assert first.post("/auth/login", json=payload).status_code == 400
    payload["captcha_answer"] = "AAAAA"
    assert first.post("/auth/login", json=payload).status_code == 200
    assert first.post("/auth/login", json=payload).status_code == 400
    challenge = first.get("/auth/captcha").json()
    with Session(engine) as db:
        row = db.scalar(select(CaptchaChallenge).where(CaptchaChallenge.token_hash == auth.hashlib.sha256(challenge["token"].encode()).hexdigest()))
        assert row
        row.expires_at -= timedelta(minutes=6)
        db.commit()
    assert first.post("/auth/login", json={**payload, "captcha_token": challenge["token"]}).status_code == 400


def test_one_time_code_login_requires_image_captcha(clients):
    first, _, sent, engine = clients
    register(first, sent, "otp@example.com")
    first.post("/auth/logout")
    with Session(engine) as db:
        row = db.scalar(select(VerificationCode).where(VerificationCode.email == "otp@example.com"))
        assert row
        row.sent_at -= timedelta(seconds=61)
        db.commit()
    assert first.post("/auth/code", json={"email": "otp@example.com", "purpose": "login"}).status_code == 200
    assert first.post("/auth/login/code", json={"email": "otp@example.com", "code": sent["otp@example.com"]}).status_code == 422
    challenge = first.get("/auth/captcha").json()
    payload = {"email": "otp@example.com", "code": sent["otp@example.com"],
               "captcha_token": challenge["token"], "captcha_answer": "AAAAA"}
    assert first.post("/auth/login/code", json=payload).status_code == 200
    assert first.post("/auth/login/code", json=payload).status_code == 400


def test_archive_and_export_require_owner(clients):
    first, second, sent, _ = clients
    register(first, sent, "a@example.com")
    register(second, sent, "b@example.com")
    product = {"name": "测试商品", "sku": "TEST", "purchase_cost": "8", "packaging_cost": "0", "weight_kg": "0", "volume_cm3": "0", "currency": "USD"}
    product_id = first.post("/products", json=product).json()["id"]
    config = {"platform": "taobao", "original_price": "20", "shipping_cost": "2", "platform_commission_rate": "0.05", "return_rate": "0.08"}
    assert first.post(f"/products/{product_id}/platform-configs", json=config).status_code == 201
    request = {"product": product, "platform_config": config, "activity": {"platform": "taobao", "activity_name": "测试活动", "estimated_sales": 20}}
    archived = first.post(f"/analysis/archive?product_id={product_id}", json=request)
    assert archived.status_code == 200
    record_id = archived.json()["analysis_id"]
    assert first.get(f"/analysis/{record_id}").status_code == 200
    assert first.get(f"/export/{record_id}").status_code == 200
    assert second.get(f"/analysis/{record_id}").status_code == 404
    assert second.get(f"/export/{record_id}").status_code == 404
    assert second.post(f"/analysis/archive?product_id={product_id}", json=request).status_code == 404


def test_snapshot_import_reconciliation_and_isolation(clients):
    import json
    from pathlib import Path

    first, second, sent, engine = clients
    register(first, sent, "owner@example.com")
    register(second, sent, "other@example.com")
    product = {"name": "Test", "sku": "PB-001", "category": "blenders", "purchase_cost": "8", "packaging_cost": "1", "currency": "USD"}
    product_id = first.post("/products", json=product).json()["id"]
    config = {"platform": "tiktok_shop", "original_price": "100", "platform_commission_rate": "0.10", "demo_default": False}
    request = {"product": product, "platform_config": config, "activity": {"platform": "tiktok_shop", "activity_name": "Sale", "estimated_sales": 10}, "rate_source": "seller agreement", "rate_effective_date": "2026-09-01"}
    archived = first.post(f"/analysis/archive?product_id={product_id}", json=request)
    assert archived.status_code == 200
    snapshot_id = archived.json()["snapshot_id"]
    assert archived.json()["revision"] == 1
    revised = first.post(f"/analysis/archive?product_id={product_id}&activity_id={archived.json()['activity_id']}", json=request)
    assert revised.json()["revision"] == 2
    with Session(engine) as db:
        snapshots = db.scalars(select(ForecastSnapshot).order_by(ForecastSnapshot.id)).all()
        assert len(snapshots) == 2 and snapshots[0].rate_source == "seller agreement"
        assert snapshots[0].snapshot_data == snapshots[1].snapshot_data
        snapshots[0].rate_source = "changed"
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
        db.rollback()
        with pytest.raises(IntegrityError, match="immutable"):
            db.execute(delete(ForecastSnapshot).where(ForecastSnapshot.id == snapshot_id))
        db.rollback()
    mapping = {"fields": {"order_id": "Order", "sku": "SKU", "settled_at": "Settled", "currency": "Currency", "gross_revenue": "Gross", "refund_amount": "Refund", "subsidy_amount": "Subsidy"}, "fee_columns": {"Commission": "Commission"}}
    content = (Path(__file__).parent / "fixtures" / "settlement_sample.csv").read_bytes()
    fields = {"platform": "tiktok_shop", "column_mapping": json.dumps(mapping), "fee_mapping": json.dumps({"Commission": "平台佣金"})}
    preview = first.post("/settlements/import", data=fields, files={"file": ("sample.csv", content, "text/csv")})
    assert preview.status_code == 200 and preview.json()["row_count"] == 2
    assert preview.json()["unrecognized_columns"] == ["Other"]
    assert second.get("/reconciliation").json() == []
    confirmed = first.post("/settlements/confirm", data=fields, files={"file": ("sample.csv", content, "text/csv")})
    assert confirmed.status_code == 200
    import_id = confirmed.json()["import_id"]
    assert second.post(f"/reconciliation/run?snapshot_id={snapshot_id}&import_id={import_id}").status_code == 404
    report = first.post(f"/reconciliation/run?snapshot_id={snapshot_id}&import_id={import_id}")
    assert report.status_code == 200
    report_id = report.json()["id"]
    assert report.json()["formula_verdict"] == "PARTIAL"
    assert report.json()["forecast_diff"]["actual_sales"] == 1
    assert first.get(f"/reconciliation/{report_id}/export").status_code == 200
    assert second.get(f"/reconciliation/{report_id}").status_code == 404
    with Session(engine) as db:
        parameter = db.scalar(select(CalibratedParameter).where(CalibratedParameter.parameter == "return_rate"))
        assert parameter and parameter.sample_size == 1 and parameter.category == "blenders"
    assert first.delete(f"/products/{product_id}").status_code == 204
    assert first.get("/forecasts").json() == []
    assert first.get(f"/reconciliation/{report_id}").status_code == 404
    with Session(engine) as db:
        assert db.scalars(select(ForecastSnapshot)).all() == []
        assert db.scalars(select(ReconciliationReport)).all() == []
        assert db.scalar(select(SettlementImport).where(SettlementImport.id == import_id)) is not None
        assert db.scalars(select(CalibratedParameter)).all() == []
