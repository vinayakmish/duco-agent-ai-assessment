"""Financial Report Generator: Produces detailed markdown breakdown."""
import os
from models.claim import COBResult


class FinancialReportGenerator:
    """Generates detailed financial breakdown reports."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, cob_results: list[COBResult]) -> str:
        """Generate a detailed markdown financial report."""
        lines = [
            "# DuCO-Agent — Financial Breakdown Report",
            "",
            "## Assumptions",
            "",
            "> **Note**: Actual policy values were not provided in the assessment.",
            "> The following deductibles, coinsurance percentages, and OOP maximums",
            "> are mock values used for demonstrating the COB engine.",
            "",
            "| Parameter | Plan A (Insurer1) | Plan B (Insurer2) |",
            "|-----------|-------------------|-------------------|",
            "| Primary Holder | Priya Sen | Aarav Sen |",
            "| Annual Deductible | ₹10,000 | ₹15,000 |",
            "| Coinsurance | 80/20 | 70/30 |",
            "| OOP Maximum | ₹1,00,000 | ₹1,50,000 |",
            "",
        ]

        for result in cob_results:
            lines.extend(self._format_claim_section(result))

        # Family summary
        lines.extend(self._format_family_summary(cob_results))

        report = "\n".join(lines)
        path = os.path.join(self.output_dir, "financial_breakdown.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(report)
        return path

    def _format_claim_section(self, result: COBResult) -> list[str]:
        """Format a single claim section."""
        lines = [
            f"---",
            f"",
            f"## {result.patient_name} — {result.claim_type.title()}",
            f"",
            f"**Total Charge: ₹{result.total_charge:,.0f}**",
            f"",
            f"### COB Determination",
            f"- **Rule Applied**: {result.determination_rule}",
            f"- **Primary Plan**: {result.primary_plan_id}",
            f"- **Secondary Plan**: {result.secondary_plan_id}",
            f"",
            f"### Step-by-Step Calculation",
            f"",
            f"| Step | Description | Amount (₹) |",
            f"|------|-------------|------------|",
            f"| 1 | Total Charges | {result.total_charge:,.0f} |",
            f"| 2 | Primary ({result.primary_plan_id}) Deductible | -{result.primary_eob.deductible_applied:,.0f} |",
            f"| 3 | After Deductible | {result.primary_eob.amount_after_deductible:,.0f} |",
            f"| 4 | Primary Plan Pays ({result.primary_eob.plan_pays / result.primary_eob.amount_after_deductible * 100:.0f}%) | {result.primary_eob.plan_pays:,.0f} |" if result.primary_eob.amount_after_deductible > 0 else f"| 4 | Primary Plan Pays | {result.primary_eob.plan_pays:,.0f} |",
            f"| 5 | Remainder to Secondary | {result.primary_eob.remaining_for_secondary:,.0f} |",
            f"| 6 | Secondary ({result.secondary_plan_id}) Deductible | -{result.secondary_eob.deductible_applied:,.0f} |",
            f"| 7 | After Secondary Deductible | {result.secondary_eob.amount_after_deductible:,.0f} |",
            f"| 8 | Secondary Plan Pays | {result.secondary_eob.plan_pays:,.0f} |",
            f"| **9** | **Final Patient OOP** | **₹{result.final_patient_oop:,.0f}** |",
            f"",
        ]
        return lines

    def _format_family_summary(self, results: list[COBResult]) -> list[str]:
        """Format the family summary with savings comparison."""
        total_charges = sum(r.total_charge for r in results)
        total_primary = sum(r.primary_eob.plan_pays for r in results)
        total_secondary = sum(r.secondary_eob.plan_pays for r in results)
        total_oop = sum(r.final_patient_oop for r in results)
        total_without_cob = sum(r.single_plan_oop for r in results)
        total_savings = sum(r.savings_vs_single for r in results)

        lines = [
            "---",
            "",
            "## Family Summary",
            "",
            "| Claim | Total | Primary Pays | Secondary Pays | Patient OOP |",
            "|-------|-------|-------------|----------------|-------------|",
        ]
        for r in results:
            lines.append(
                f"| {r.patient_name} ({r.claim_type.title()}) | "
                f"₹{r.total_charge:,.0f} | "
                f"₹{r.primary_eob.plan_pays:,.0f} | "
                f"₹{r.secondary_eob.plan_pays:,.0f} | "
                f"₹{r.final_patient_oop:,.0f} |"
            )
        lines.append(
            f"| **Total** | **₹{total_charges:,.0f}** | "
            f"**₹{total_primary:,.0f}** | "
            f"**₹{total_secondary:,.0f}** | "
            f"**₹{total_oop:,.0f}** |"
        )
        lines.extend([
            "",
            "## COB Savings Analysis",
            "",
            "| Scenario | Without COB | With COB | **Savings** |",
            "|----------|-------------|----------|-------------|",
        ])
        for r in results:
            lines.append(
                f"| {r.patient_name} ({r.claim_type.title()}) | "
                f"₹{r.single_plan_oop:,.0f} | "
                f"₹{r.final_patient_oop:,.0f} | "
                f"**₹{r.savings_vs_single:,.0f}** |"
            )
        lines.append(
            f"| **Family Total** | **₹{total_without_cob:,.0f}** | "
            f"**₹{total_oop:,.0f}** | **₹{total_savings:,.0f}** |"
        )
        lines.append("")
        return lines
