"""Critic Agent: Validates results at each pipeline stage.

The Critic runs after each major step and checks:
1. validate_calculations() — primary + secondary + OOP == total_charges?
2. validate_codes()        — All CPT/ICD-10 codes in valid set?
3. validate_preauth()      — All required pre-auths generated?
4. validate_compliance()   — Non-duplication rule held? Secondary ≤ primary hypothetical?

If any check fails → returns an action for the Planner to loop back.
"""
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional

from models.claim import COBResult
from parsers.medical_code_mapper import VALID_CPT_CODES, VALID_ICD10_CODES

logger = logging.getLogger("duco_agent.critic")


class CriticAction(Enum):
    """Actions the Critic can request."""
    PASS = auto()           # All checks passed
    RECALCULATE = auto()    # Financial calculations are wrong
    REMAP_CODE = auto()     # Invalid medical code found
    GENERATE_PREAUTH = auto()  # Missing pre-auth letter
    FIX_COMPLIANCE = auto()    # COB compliance issue


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    passed: bool
    action: CriticAction = CriticAction.PASS
    message: str = ""
    details: dict = field(default_factory=dict)


class CriticAgent:
    """Agent that validates pipeline outputs and triggers corrections."""

    def __init__(self):
        self.validation_log: list[ValidationResult] = []

    def validate_all(
        self,
        cob_results: list[COBResult],
        extracted_codes: list[str],
        generated_preauth_ids: list[str],
        claims_requiring_preauth: list[str]
    ) -> list[ValidationResult]:
        """Run all validation checks.

        Returns list of ValidationResult — if any failed, Planner should loop back.
        """
        results = []

        # Check 1: Mathematical validation for each COB result
        for cob_result in cob_results:
            result = self.validate_calculations(cob_result)
            results.append(result)
            self.validation_log.append(result)

        # Check 2: Medical code validation
        for code in extracted_codes:
            result = self.validate_codes(code)
            results.append(result)
            self.validation_log.append(result)

        # Check 3: Pre-auth completeness
        preauth_result = self.validate_preauth(
            claims_requiring_preauth, generated_preauth_ids
        )
        results.append(preauth_result)
        self.validation_log.append(preauth_result)

        # Check 4: COB compliance
        for cob_result in cob_results:
            compliance = self.validate_compliance(cob_result)
            results.append(compliance)
            self.validation_log.append(compliance)

        return results

    def validate_calculations(self, cob_result: COBResult) -> ValidationResult:
        """Reflection Loop 1: Verify primary + secondary + OOP == total_charges."""
        total = cob_result.total_charge
        primary = cob_result.primary_eob.plan_pays
        secondary = cob_result.secondary_eob.plan_pays
        patient = cob_result.final_patient_oop

        computed_total = primary + secondary + patient

        if abs(computed_total - total) > 0.01:
            logger.warning(
                f"CALCULATION MISMATCH for {cob_result.patient_name}: "
                f"{primary} + {secondary} + {patient} = {computed_total} ≠ {total}"
            )
            return ValidationResult(
                check_name="mathematical_validation",
                passed=False,
                action=CriticAction.RECALCULATE,
                message=(
                    f"Total mismatch: {primary:,.2f} + {secondary:,.2f} + "
                    f"{patient:,.2f} = {computed_total:,.2f} ≠ {total:,.2f}"
                ),
                details={
                    "patient": cob_result.patient_name,
                    "expected": total,
                    "computed": computed_total,
                    "diff": abs(computed_total - total)
                }
            )

        logger.info(
            f"✓ Calculation validated for {cob_result.patient_name}: "
            f"{primary:,.0f} + {secondary:,.0f} + {patient:,.0f} = {total:,.0f}"
        )
        return ValidationResult(
            check_name="mathematical_validation",
            passed=True,
            message=f"Verified: {primary:,.0f} + {secondary:,.0f} + {patient:,.0f} = {total:,.0f}"
        )

    def validate_codes(self, code: str) -> ValidationResult:
        """Reflection Loop 2: Verify all CPT/ICD-10 codes are valid."""
        is_valid = code in VALID_CPT_CODES or code in VALID_ICD10_CODES

        if not is_valid:
            logger.warning(f"INVALID CODE: {code} not found in valid code sets")
            return ValidationResult(
                check_name="code_validation",
                passed=False,
                action=CriticAction.REMAP_CODE,
                message=f"Invalid code: {code}. Must remap to a valid CPT/ICD-10 code.",
                details={"invalid_code": code}
            )

        logger.info(f"✓ Code validated: {code}")
        return ValidationResult(
            check_name="code_validation",
            passed=True,
            message=f"Code {code} is valid"
        )

    def validate_preauth(
        self,
        required: list[str],
        generated: list[str]
    ) -> ValidationResult:
        """Reflection Loop 3: Check all required pre-auths exist."""
        missing = [r for r in required if r not in generated]

        if missing:
            logger.warning(f"MISSING PRE-AUTH letters: {missing}")
            return ValidationResult(
                check_name="preauth_completeness",
                passed=False,
                action=CriticAction.GENERATE_PREAUTH,
                message=f"Missing pre-auth letters for: {', '.join(missing)}",
                details={"missing_preauths": missing}
            )

        logger.info(f"✓ All {len(required)} pre-auth letters generated")
        return ValidationResult(
            check_name="preauth_completeness",
            passed=True,
            message=f"All {len(required)} required pre-auth letters generated"
        )

    def validate_compliance(self, cob_result: COBResult) -> ValidationResult:
        """Check IRDAI compliance: total payouts ≤ total charges."""
        total_paid = (
            cob_result.primary_eob.plan_pays +
            cob_result.secondary_eob.plan_pays
        )

        if total_paid > cob_result.total_charge + 0.01:
            logger.warning(
                f"COMPLIANCE VIOLATION: Plans paid ₹{total_paid:,.0f} > "
                f"total charge ₹{cob_result.total_charge:,.0f}"
            )
            return ValidationResult(
                check_name="irdai_compliance",
                passed=False,
                action=CriticAction.FIX_COMPLIANCE,
                message=(
                    f"IRDAI violation: Total payouts (₹{total_paid:,.0f}) exceed "
                    f"total charges (₹{cob_result.total_charge:,.0f})"
                )
            )

        # Check OOP is non-negative
        if cob_result.final_patient_oop < -0.01:
            return ValidationResult(
                check_name="irdai_compliance",
                passed=False,
                action=CriticAction.RECALCULATE,
                message=f"Negative OOP detected: ₹{cob_result.final_patient_oop:,.2f}"
            )

        logger.info(f"✓ IRDAI compliance verified for {cob_result.patient_name}")
        return ValidationResult(
            check_name="irdai_compliance",
            passed=True,
            message=f"Payouts (₹{total_paid:,.0f}) ≤ total charges (₹{cob_result.total_charge:,.0f})"
        )

    def has_failures(self, results: list[ValidationResult]) -> bool:
        """Check if any validations failed."""
        return any(not r.passed for r in results)

    def get_required_actions(self, results: list[ValidationResult]) -> list[CriticAction]:
        """Get list of corrective actions needed."""
        return [r.action for r in results if not r.passed]

    def get_summary(self) -> dict:
        """Get validation summary."""
        total = len(self.validation_log)
        passed = sum(1 for v in self.validation_log if v.passed)
        failed = total - passed
        return {
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "all_passed": failed == 0,
            "failures": [
                {"check": v.check_name, "message": v.message}
                for v in self.validation_log if not v.passed
            ]
        }
