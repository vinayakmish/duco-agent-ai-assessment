"""Tests for Mock Insurance API endpoints."""
import pytest
from fastapi.testclient import TestClient
from api.mock_insurance_api import app


client = TestClient(app)


class TestPlanDetails:
    def test_get_plan_a_details(self):
        response = client.get("/api/v1/plans/PLAN_A/details")
        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == "PLAN_A"
        assert data["primary_holder"] == "Priya Sen"
        assert data["coverage"]["annual_deductible"] == 10000

    def test_get_plan_b_details(self):
        response = client.get("/api/v1/plans/PLAN_B/details")
        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == "PLAN_B"
        assert data["primary_holder"] == "Aarav Sen"
        assert data["coverage"]["annual_deductible"] == 15000

    def test_get_unknown_plan(self):
        response = client.get("/api/v1/plans/PLAN_X/details")
        assert response.status_code == 404


class TestCoverageVerification:
    def test_verify_aarav_surgery_plan_b(self):
        """Aarav is primary holder on Plan B."""
        response = client.post("/api/v1/plans/PLAN_B/verify-coverage", json={
            "patient_name": "Aarav Sen",
            "cpt_codes": ["29888", "29881"],
            "estimated_cost": 450000
        })
        assert response.status_code == 200
        data = response.json()
        assert data["is_covered"] is True
        assert data["patient_role"] == "primary_holder"
        assert data["coinsurance_rate"] == 0.70

    def test_verify_priya_pt_plan_a(self):
        """Priya is primary holder on Plan A."""
        response = client.post("/api/v1/plans/PLAN_A/verify-coverage", json={
            "patient_name": "Priya Sen",
            "cpt_codes": ["97161", "97110"],
            "estimated_cost": 30000
        })
        assert response.status_code == 200
        data = response.json()
        assert data["is_covered"] is True
        assert data["patient_role"] == "primary_holder"


class TestPreAuthCheck:
    def test_aarav_surgery_requires_preauth_plan_b(self):
        """Plan B requires pre-auth for ALL surgeries."""
        response = client.post("/api/v1/plans/PLAN_B/check-preauth-requirement", json={
            "patient_name": "Aarav Sen",
            "cpt_codes": ["29888", "29881"],
            "estimated_cost": 450000,
            "procedure_type": "surgery"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["requires_preauth"] is True

    def test_aarav_surgery_requires_preauth_plan_a(self):
        """Plan A requires pre-auth for surgery > ₹1,00,000."""
        response = client.post("/api/v1/plans/PLAN_A/check-preauth-requirement", json={
            "patient_name": "Aarav Sen",
            "cpt_codes": ["29888", "29881"],
            "estimated_cost": 450000,
            "procedure_type": "surgery"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["requires_preauth"] is True


class TestCOBDetermination:
    def test_aarav_cob_determination(self):
        """Aarav is employee on Plan B, so Plan B is primary for him."""
        response = client.post("/api/v1/plans/PLAN_A/cob-determination", json={
            "patient_name": "Aarav Sen",
            "plan_a_id": "PLAN_A",
            "plan_b_id": "PLAN_B"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["primary_plan_id"] == "PLAN_B"
        assert data["secondary_plan_id"] == "PLAN_A"

    def test_priya_cob_determination(self):
        """Priya is employee on Plan A, so Plan A is primary for her."""
        response = client.post("/api/v1/plans/PLAN_A/cob-determination", json={
            "patient_name": "Priya Sen",
            "plan_a_id": "PLAN_A",
            "plan_b_id": "PLAN_B"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["primary_plan_id"] == "PLAN_A"
        assert data["secondary_plan_id"] == "PLAN_B"
