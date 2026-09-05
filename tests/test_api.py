from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from backend.app.database import SessionLocal
from backend.app.models import AnalysisResult

from backend.app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_products_seeded():
    with TestClient(app) as client:
        response = client.get("/products")
    assert response.status_code == 200
    assert len(response.json()) >= 3


def test_modern_ui_bootstrap_and_combined_analysis():
    with TestClient(app) as client:
        bootstrap = client.get("/ui/bootstrap")
        assert bootstrap.status_code == 200
        data = bootstrap.json()
        assert len(data["products"]) >= 3
        assert len(data["cases"]) >= 3
        case = data["cases"][0]
        response = client.post(
            f"/analysis/run?product_id={case['product_id']}&activity_id={case['id']}",
            json=case["request"],
        )
        analysis_id = response.json()["analysis_id"]
        exported = client.get(f"/export/{analysis_id}?format=xlsx")
    assert response.status_code == 200
    result = response.json()
    assert result["result"]["unit_profit"] == case["result"]["unit_profit"]
    assert len(result["scenarios"]) == 3
    assert result["recommendations"]
    assert result["analysis_id"] is not None
    assert exported.status_code == 200
    workbook = load_workbook(BytesIO(exported.content), read_only=True)
    assert workbook.sheetnames == ["Summary", "Cost Breakdown", "Scenario Analysis", "Recommendations"]
    # This integration test persists briefly to verify history/export, then cleans up
    # so repeated test runs never distort real Dashboard statistics.
    with SessionLocal() as session:
        record = session.get(AnalysisResult, analysis_id)
        if record:
            session.delete(record)
            session.commit()
