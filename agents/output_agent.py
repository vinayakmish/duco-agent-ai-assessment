"""Output Agent: Orchestrates generation of all output artifacts."""
import os
from models.claim import COBResult
from outputs.cost_flow_visualizer import CostFlowVisualizer
from outputs.financial_report import FinancialReportGenerator
from outputs.patient_briefing import PatientBriefingGenerator


class OutputAgent:
    """Agent responsible for generating all multi-modal outputs."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.visualizer = CostFlowVisualizer(output_dir)
        self.report_gen = FinancialReportGenerator(output_dir)
        self.briefing_gen = PatientBriefingGenerator(output_dir)

    def generate_all_outputs(self, cob_results: list[COBResult]) -> dict[str, str]:
        """Generate all output artifacts from COB results.

        Returns dict mapping output name to file path.
        """
        outputs = {}

        # 1. Cost flow visualizations
        try:
            viz_paths = self.visualizer.generate_all(cob_results)
            outputs.update(viz_paths)
        except Exception as e:
            outputs["visualization_error"] = str(e)

        # 2. Financial breakdown report
        try:
            report_path = self.report_gen.generate(cob_results)
            outputs["financial_report"] = report_path
        except Exception as e:
            outputs["report_error"] = str(e)

        # 3. Patient briefing
        try:
            briefing_path = self.briefing_gen.generate(cob_results)
            outputs["patient_briefing"] = briefing_path
        except Exception as e:
            outputs["briefing_error"] = str(e)

        return outputs
