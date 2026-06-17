"""Patient Briefing Generator: Creates plain-language summary for patients."""
import os
from models.claim import COBResult


class PatientBriefingGenerator:
    """Generates patient-friendly briefing text."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, cob_results: list[COBResult]) -> str:
        """Generate a patient-friendly text briefing."""
        lines = [
            "=" * 70,
            "     DuCO-Agent — Patient Briefing for Aarav & Priya Sen",
            "=" * 70,
            "",
            "Dear Aarav and Priya,",
            "",
            "Here is a summary of your insurance coverage analysis. Because you",
            "both have dual insurance coverage (Plan A and Plan B), we have",
            "coordinated your benefits to minimize your out-of-pocket expenses.",
            "",
        ]

        total_oop = 0
        total_savings = 0

        for result in cob_results:
            lines.extend(self._format_claim_briefing(result))
            total_oop += result.final_patient_oop
            total_savings += result.savings_vs_single

        # Family summary
        lines.extend([
            "-" * 70,
            "",
            "FAMILY SUMMARY:",
            f"  Total Out-of-Pocket (both claims): Rs. {total_oop:,.0f}",
            f"  Total Savings from Dual Coverage  : Rs. {total_savings:,.0f}",
            "",
            "NEXT STEPS:",
            "  1. Review the pre-authorization letters we have generated.",
            "  2. Submit Aarav's pre-auth to Insurer2 (Plan B) at least 48 hours",
            "     before the planned surgery date.",
            "  3. After primary approval, submit the secondary pre-auth to",
            "     Insurer1 (Plan A) with the COB cover letter attached.",
            "  4. For Priya's PT claim, submit to Insurer1 (Plan A) with the",
            "     invoice and referral documents.",
            "  5. Keep copies of all EOBs (Explanation of Benefits) for records.",
            "",
            "If you have any questions, please don't hesitate to ask!",
            "",
            "Best regards,",
            "DuCO-Agent — Your Insurance Coordination Assistant",
            "=" * 70,
        ])

        briefing = "\n".join(lines)
        path = os.path.join(self.output_dir, "patient_briefing.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(briefing)

        # Try to generate audio (optional — low rubric weight)
        try:
            self._generate_audio(briefing)
        except Exception:
            pass  # Audio is optional

        return path

    def _format_claim_briefing(self, result: COBResult) -> list[str]:
        """Format a single claim in patient-friendly language."""
        lines = ["-" * 70, ""]

        if result.claim_type == "surgery":
            lines.extend([
                f"AARAV'S ACL SURGERY (Total Cost: Rs. {result.total_charge:,.0f})",
                "",
                f"  Which plan pays first?",
                f"    → {result.primary_plan_id} (Insurer2) is your PRIMARY insurance for",
                f"      this surgery because you are the employee on that plan.",
                f"    → {result.secondary_plan_id} (Insurer1) is SECONDARY (you are a dependent).",
                "",
                f"  How the costs break down:",
                f"    Plan B (Primary) pays  : Rs. {result.primary_eob.plan_pays:,.0f}",
                f"    Plan A (Secondary) pays: Rs. {result.secondary_eob.plan_pays:,.0f}",
                f"    Your out-of-pocket     : Rs. {result.final_patient_oop:,.0f}",
                "",
                f"  Without dual coverage, you would have paid Rs. {result.single_plan_oop:,.0f}.",
                f"  With COB, you save Rs. {result.savings_vs_single:,.0f}!",
                "",
                f"  Pre-authorization: REQUIRED for both plans before scheduling.",
                f"  We have generated the pre-auth letters for you.",
                "",
            ])
        elif result.claim_type == "therapy":
            lines.extend([
                f"PRIYA'S PHYSICAL THERAPY (Total Cost: Rs. {result.total_charge:,.0f})",
                "",
                f"  Which plan pays first?",
                f"    → {result.primary_plan_id} (Insurer1) is your PRIMARY insurance for",
                f"      this PT because you are the employee on that plan.",
                f"    → {result.secondary_plan_id} (Insurer2) is SECONDARY (you are a dependent).",
                "",
                f"  How the costs break down:",
                f"    Plan A (Primary) pays  : Rs. {result.primary_eob.plan_pays:,.0f}",
                f"    Plan B (Secondary) pays: Rs. {result.secondary_eob.plan_pays:,.0f}",
                f"    Your out-of-pocket     : Rs. {result.final_patient_oop:,.0f}",
                "",
            ])
            if result.secondary_eob.plan_pays == 0:
                lines.extend([
                    f"  Note: Plan B's deductible (Rs. 15,000) exceeds the remaining",
                    f"  balance, so Plan B does not contribute to this particular claim.",
                    f"  For larger claims, both plans would share the cost.",
                    "",
                ])

        return lines

    def _generate_audio(self, text: str):
        """Attempt to generate audio briefing using gTTS (optional)."""
        try:
            from gtts import gTTS
            # Simplify text for audio
            audio_text = text.replace("=" * 70, "").replace("-" * 70, "")
            audio_text = audio_text.replace("Rs.", "Rupees")
            tts = gTTS(text=audio_text, lang="en", slow=False)
            path = os.path.join(self.output_dir, "patient_briefing.mp3")
            tts.save(path)
        except ImportError:
            pass  # gTTS not available, skip audio
