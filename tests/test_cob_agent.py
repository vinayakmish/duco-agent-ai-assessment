"""Tests for COB Agent — financial calculation accuracy."""
import pytest
from agents.cob_agent import COBAgent
from models.claim import Claim, ClaimLine
from models.policy import PatientRole


class TestCOBDetermination:
    """Test primary/secondary plan determination."""

    def setup_method(self):
        self.agent = COBAgent()

    def test_aarav_primary_is_plan_b(self):
        """Aarav is employee on Plan B, so Plan B is primary."""
        primary, secondary, rule = self.agent.determine_primary_secondary(
            "Aarav Sen",
            PatientRole.DEPENDENT,
            PatientRole.PRIMARY_HOLDER
        )
        assert primary == "PLAN_B"
        assert secondary == "PLAN_A"
        assert "Employee-First" in rule

    def test_priya_primary_is_plan_a(self):
        """Priya is employee on Plan A, so Plan A is primary."""
        primary, secondary, rule = self.agent.determine_primary_secondary(
            "Priya Sen",
            PatientRole.PRIMARY_HOLDER,
            PatientRole.DEPENDENT
        )
        assert primary == "PLAN_A"
        assert secondary == "PLAN_B"


class TestAaravSurgeryCOB:
    """Test COB calculations for Aarav's ACL surgery (₹4,50,000)."""

    def setup_method(self):
        self.agent = COBAgent()
        self.claim = Claim(
            claim_id="AARAV-SURGERY-001",
            patient_name="Aarav Sen",
            claim_type="surgery",
            line_items=[
                ClaimLine("29888", "ACL Reconstruction", 350000.0, ["S83.511A"]),
                ClaimLine("29881", "Meniscectomy", 100000.0, ["S83.211A"]),
            ],
            total_charge=450000.0,
            icd_codes=["S83.511A", "S83.211A"],
            requires_preauth=True
        )

    def test_primary_plan_b_payment(self):
        """Plan B (primary): Deductible ₹15,000 + 70% coinsurance."""
        eob = self.agent.calculate_primary_claim("PLAN_B", 450000.0)
        assert eob.deductible_applied == 15000.0
        assert eob.amount_after_deductible == 435000.0
        assert eob.plan_pays == 304500.0  # 70% of 435000
        assert eob.patient_coinsurance == 130500.0  # 30% of 435000

    def test_secondary_plan_a_payment(self):
        """Plan A (secondary): Pays on remaining ₹1,45,500."""
        primary_eob = self.agent.calculate_primary_claim("PLAN_B", 450000.0)
        secondary_eob = self.agent.calculate_secondary_claim(
            "PLAN_A", 450000.0, primary_eob.plan_pays
        )
        assert secondary_eob.deductible_applied == 10000.0
        remaining_after_primary = 450000.0 - 304500.0  # = 145500
        after_secondary_deductible = remaining_after_primary - 10000.0  # = 135500
        expected_plan_a_pays = round(after_secondary_deductible * 0.80, 2)
        assert secondary_eob.plan_pays == expected_plan_a_pays

    def test_full_cob_aarav_surgery(self):
        """Full COB: Total OOP should be ₹27,100."""
        result = self.agent.process_claim_with_cob(
            self.claim,
            PatientRole.DEPENDENT,
            PatientRole.PRIMARY_HOLDER
        )
        assert result.primary_plan_id == "PLAN_B"
        assert result.secondary_plan_id == "PLAN_A"
        assert result.primary_eob.plan_pays == 304500.0
        assert result.secondary_eob.plan_pays == 108400.0

        # Verify: primary + secondary + OOP = total
        total = result.primary_eob.plan_pays + result.secondary_eob.plan_pays + result.final_patient_oop
        assert abs(total - 450000.0) < 0.01, f"Total mismatch: {total} != 450000"

        # OOP = deductible_B(15K) + coinsurance_B(130500) → remainder 145500
        # Secondary: deductible_A(10K) + coinsurance_A(20% of 135500 = 27100) = 37100
        assert result.final_patient_oop == 37100.0

    def test_savings_vs_single_coverage(self):
        """Savings should be significant with dual coverage."""
        result = self.agent.process_claim_with_cob(
            self.claim,
            PatientRole.DEPENDENT,
            PatientRole.PRIMARY_HOLDER
        )
        assert result.single_plan_oop == 145500.0
        assert result.savings_vs_single == 145500.0 - 37100.0


class TestPriyaPTCOB:
    """Test COB calculations for Priya's PT sessions (₹30,000)."""

    def setup_method(self):
        self.agent = COBAgent()
        self.claim = Claim(
            claim_id="PRIYA-PT-001",
            patient_name="Priya Sen",
            claim_type="therapy",
            line_items=[
                ClaimLine("97161", "PT Evaluation", 5000.0, ["M54.50"]),
                ClaimLine("97110", "Therapeutic Exercise x6", 25000.0, ["M54.50"]),
            ],
            total_charge=30000.0,
            icd_codes=["M54.50"]
        )

    def test_primary_plan_a_payment(self):
        """Plan A (primary): Deductible ₹10,000 + 80% coinsurance."""
        eob = self.agent.calculate_primary_claim("PLAN_A", 30000.0)
        assert eob.deductible_applied == 10000.0
        assert eob.amount_after_deductible == 20000.0
        assert eob.plan_pays == 16000.0

    def test_secondary_plan_b_deductible_blocks(self):
        """Plan B secondary: ₹15,000 deductible exceeds ₹14,000 remainder."""
        primary_eob = self.agent.calculate_primary_claim("PLAN_A", 30000.0)
        secondary_eob = self.agent.calculate_secondary_claim(
            "PLAN_B", 30000.0, primary_eob.plan_pays
        )
        assert secondary_eob.plan_pays == 0.0

    def test_full_cob_priya_pt(self):
        """Full COB: Priya's OOP is ₹14,000."""
        result = self.agent.process_claim_with_cob(
            self.claim,
            PatientRole.PRIMARY_HOLDER,
            PatientRole.DEPENDENT
        )
        assert result.primary_plan_id == "PLAN_A"
        assert result.primary_eob.plan_pays == 16000.0
        assert result.secondary_eob.plan_pays == 0.0
        assert result.final_patient_oop == 14000.0

        # Verify total adds up
        total = result.primary_eob.plan_pays + result.secondary_eob.plan_pays + result.final_patient_oop
        assert abs(total - 30000.0) < 0.01


class TestMathematicalValidation:
    """Verify that all calculations satisfy: primary + secondary + OOP = total."""

    def setup_method(self):
        self.agent = COBAgent()

    def test_invariant_aarav(self):
        claim = Claim("C1", "Aarav Sen", "surgery", total_charge=450000.0)
        result = self.agent.process_claim_with_cob(
            claim, PatientRole.DEPENDENT, PatientRole.PRIMARY_HOLDER
        )
        total = result.primary_eob.plan_pays + result.secondary_eob.plan_pays + result.final_patient_oop
        assert abs(total - 450000.0) < 0.01

    def test_invariant_priya(self):
        claim = Claim("C2", "Priya Sen", "therapy", total_charge=30000.0)
        result = self.agent.process_claim_with_cob(
            claim, PatientRole.PRIMARY_HOLDER, PatientRole.DEPENDENT
        )
        total = result.primary_eob.plan_pays + result.secondary_eob.plan_pays + result.final_patient_oop
        assert abs(total - 30000.0) < 0.01

    def test_no_profit_from_cob(self):
        """IRDAI compliance: Total payouts never exceed total charges."""
        claim = Claim("S1", "Aarav Sen", "surgery", total_charge=450000.0)
        result = self.agent.process_claim_with_cob(
            claim, PatientRole.DEPENDENT, PatientRole.PRIMARY_HOLDER
        )
        total_paid = result.primary_eob.plan_pays + result.secondary_eob.plan_pays
        assert total_paid <= 450000.0

    def test_oop_never_negative(self):
        """Patient OOP should never be negative."""
        claim = Claim("S1", "Aarav Sen", "surgery", total_charge=450000.0)
        result = self.agent.process_claim_with_cob(
            claim, PatientRole.DEPENDENT, PatientRole.PRIMARY_HOLDER
        )
        assert result.final_patient_oop >= 0

    def test_total_family_savings(self):
        """Verify total family savings with COB."""
        surgery = Claim("S1", "Aarav Sen", "surgery", total_charge=450000.0)
        surgery_result = self.agent.process_claim_with_cob(
            surgery, PatientRole.DEPENDENT, PatientRole.PRIMARY_HOLDER
        )

        agent2 = COBAgent()
        pt = Claim("P1", "Priya Sen", "therapy", total_charge=30000.0)
        pt_result = agent2.process_claim_with_cob(
            pt, PatientRole.PRIMARY_HOLDER, PatientRole.DEPENDENT
        )

        total_oop = surgery_result.final_patient_oop + pt_result.final_patient_oop
        assert total_oop == 51100.0  # 37100 + 14000

        total_savings = surgery_result.savings_vs_single + pt_result.savings_vs_single
        assert total_savings == 108400.0  # 108400 + 0
