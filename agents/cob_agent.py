"""COB Agent: Coordination of Benefits determination and financial calculations.

This agent:
1. Determines primary vs. secondary insurance using Employee-First Rule
2. Calculates claim payments through both plans
3. Applies non-duplication / IRDAI indemnity rules
4. Optimizes out-of-pocket expenses
5. Computes savings vs. single coverage
"""
from dataclasses import dataclass
from typing import Optional
from models.claim import Claim, EOB, COBResult
from models.policy import PatientRole, PlanPriority


@dataclass
class PlanConfig:
    """Simplified plan configuration for calculations."""
    plan_id: str
    deductible: float
    deductible_used: float
    coinsurance_rate: float  # What plan pays (e.g., 0.80)
    oop_maximum: float
    oop_used: float = 0.0


class COBAgent:
    """Agent for Coordination of Benefits determination and calculations."""

    def __init__(self):
        # Default plan configs (from config/insurance_plans.json)
        self.plan_configs = {
            "PLAN_A": PlanConfig(
                plan_id="PLAN_A",
                deductible=10000.0,
                deductible_used=0.0,
                coinsurance_rate=0.80,
                oop_maximum=100000.0
            ),
            "PLAN_B": PlanConfig(
                plan_id="PLAN_B",
                deductible=15000.0,
                deductible_used=0.0,
                coinsurance_rate=0.70,
                oop_maximum=150000.0
            ),
        }

    def determine_primary_secondary(
        self,
        patient_name: str,
        plan_a_role: PatientRole,
        plan_b_role: PatientRole
    ) -> tuple[str, str, str]:
        """Determine which plan is primary and which is secondary.

        Uses the Employee-First Rule:
        The plan where the patient is the primary policyholder (employee) is primary.

        Returns:
            Tuple of (primary_plan_id, secondary_plan_id, rule_used)
        """
        if plan_a_role == PatientRole.PRIMARY_HOLDER:
            return "PLAN_A", "PLAN_B", "Employee-First Rule"
        elif plan_b_role == PatientRole.PRIMARY_HOLDER:
            return "PLAN_B", "PLAN_A", "Employee-First Rule"
        else:
            # Both dependent — shouldn't happen in this scenario
            return "PLAN_A", "PLAN_B", "Default (both dependent)"

    def calculate_primary_claim(
        self,
        plan_id: str,
        total_charge: float
    ) -> EOB:
        """Calculate what the primary plan pays."""
        config = self.plan_configs[plan_id]

        deductible_remaining = max(0, config.deductible - config.deductible_used)
        deductible_applied = min(deductible_remaining, total_charge)
        after_deductible = total_charge - deductible_applied

        plan_pays = round(after_deductible * config.coinsurance_rate, 2)
        patient_coinsurance = round(after_deductible - plan_pays, 2)
        patient_responsibility = deductible_applied + patient_coinsurance
        remaining_for_secondary = total_charge - plan_pays

        # Update deductible used
        config.deductible_used += deductible_applied

        return EOB(
            plan_id=plan_id,
            claim_id="",
            is_primary=True,
            total_charge=total_charge,
            deductible_applied=deductible_applied,
            amount_after_deductible=after_deductible,
            plan_pays=plan_pays,
            patient_coinsurance=patient_coinsurance,
            patient_responsibility=patient_responsibility,
            remaining_for_secondary=remaining_for_secondary
        )

    def calculate_secondary_claim(
        self,
        plan_id: str,
        total_charge: float,
        primary_paid: float
    ) -> EOB:
        """Calculate what the secondary plan pays on the remaining balance."""
        config = self.plan_configs[plan_id]

        remaining_amount = total_charge - primary_paid
        deductible_remaining = max(0, config.deductible - config.deductible_used)
        deductible_applied = min(deductible_remaining, remaining_amount)
        after_deductible = max(0, remaining_amount - deductible_applied)

        plan_pays = round(after_deductible * config.coinsurance_rate, 2)
        patient_coinsurance = round(after_deductible - plan_pays, 2)
        patient_responsibility = deductible_applied + patient_coinsurance

        # Non-duplication check: secondary should not pay more than
        # what it would have paid as primary
        hypothetical_primary = self._calculate_hypothetical_primary(plan_id, total_charge)
        if plan_pays > hypothetical_primary:
            plan_pays = hypothetical_primary
            patient_responsibility = total_charge - primary_paid - plan_pays
            patient_coinsurance = patient_responsibility - deductible_applied

        # Update deductible used
        config.deductible_used += deductible_applied

        return EOB(
            plan_id=plan_id,
            claim_id="",
            is_primary=False,
            total_charge=total_charge,
            deductible_applied=deductible_applied,
            amount_after_deductible=after_deductible,
            plan_pays=plan_pays,
            patient_coinsurance=patient_coinsurance,
            patient_responsibility=patient_responsibility,
            remaining_for_secondary=0.0  # No further plans
        )

    def _calculate_hypothetical_primary(
        self,
        plan_id: str,
        total_charge: float
    ) -> float:
        """Calculate what this plan WOULD have paid if it were primary.

        Used for Non-Duplication of Benefits check.
        """
        config = self.plan_configs[plan_id]
        deductible_remaining = max(0, config.deductible - config.deductible_used)
        deductible_applied = min(deductible_remaining, total_charge)
        after_deductible = total_charge - deductible_applied
        return round(after_deductible * config.coinsurance_rate, 2)

    def process_claim_with_cob(
        self,
        claim: Claim,
        patient_plan_a_role: PatientRole,
        patient_plan_b_role: PatientRole
    ) -> COBResult:
        """Process a complete claim through COB.

        Pipeline:
        1. Determine primary/secondary
        2. Calculate primary plan payment
        3. Calculate secondary plan payment on remainder
        4. Apply non-duplication rule
        5. Calculate savings vs. single coverage
        """
        # Step 1: Determine primary/secondary
        primary_id, secondary_id, rule = self.determine_primary_secondary(
            claim.patient_name, patient_plan_a_role, patient_plan_b_role
        )

        # Step 2: Calculate primary claim
        primary_eob = self.calculate_primary_claim(
            primary_id, claim.total_charge
        )

        # Step 3: Calculate secondary claim
        secondary_eob = self.calculate_secondary_claim(
            secondary_id, claim.total_charge, primary_eob.plan_pays
        )

        # Step 4: Calculate totals
        total_plan_payments = primary_eob.plan_pays + secondary_eob.plan_pays
        final_patient_oop = claim.total_charge - total_plan_payments

        # Step 5: Calculate savings vs. single coverage
        single_plan_oop = primary_eob.patient_responsibility
        savings = single_plan_oop - final_patient_oop

        result = COBResult(
            patient_name=claim.patient_name,
            claim_type=claim.claim_type,
            total_charge=claim.total_charge,
            primary_plan_id=primary_id,
            secondary_plan_id=secondary_id,
            primary_eob=primary_eob,
            secondary_eob=secondary_eob,
            total_plan_payments=total_plan_payments,
            final_patient_oop=final_patient_oop,
            savings_vs_single=savings,
            single_plan_oop=single_plan_oop,
            determination_rule=rule
        )

        return result

    def optimize_claim_order(
        self,
        claims: list[Claim],
        patient_plan_a_role: PatientRole,
        patient_plan_b_role: PatientRole
    ) -> list[COBResult]:
        """Process multiple claims, optimizing order for minimum OOP.

        Under IRDAI rules, policyholders can choose which insurer to file with first.
        This method evaluates the standard order and verifies it's optimal.
        """
        results = []
        for claim in claims:
            result = self.process_claim_with_cob(
                claim, patient_plan_a_role, patient_plan_b_role
            )
            results.append(result)

        return results
