"""Cost Flow Visualizer: Generates Sankey diagrams and comparison charts.

Produces professional visualizations showing money flow through the
COB pipeline: Total Charges → Primary Plan → Secondary Plan → Patient OOP.
"""
import os
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.sankey import Sankey

from models.claim import COBResult


class CostFlowVisualizer:
    """Generates cost flow visualizations for COB results."""

    # Professional color palette
    COLORS = {
        "primary": "#2563EB",     # Blue
        "secondary": "#7C3AED",   # Purple
        "patient": "#DC2626",     # Red
        "savings": "#059669",     # Green
        "total": "#1E293B",       # Dark slate
        "bg": "#F8FAFC",          # Light background
    }

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_all(self, cob_results: list[COBResult]) -> dict[str, str]:
        """Generate all visualizations."""
        outputs = {}

        # 1. Cost flow bar chart for each claim
        path = self._generate_cost_breakdown(cob_results)
        outputs["cost_breakdown"] = path

        # 2. Savings comparison chart
        path = self._generate_savings_comparison(cob_results)
        outputs["savings_comparison"] = path

        # 3. Combined Sankey-style flow diagram
        path = self._generate_flow_diagram(cob_results)
        outputs["cost_flow"] = path

        return outputs

    def _generate_cost_breakdown(self, results: list[COBResult]) -> str:
        """Generate stacked bar chart showing payment breakdown per claim."""
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor(self.COLORS["bg"])
        ax.set_facecolor(self.COLORS["bg"])

        labels = []
        primary_vals = []
        secondary_vals = []
        patient_vals = []

        for r in results:
            label = f"{r.patient_name}\n({r.claim_type.title()})\n₹{r.total_charge:,.0f}"
            labels.append(label)
            primary_vals.append(r.primary_eob.plan_pays)
            secondary_vals.append(r.secondary_eob.plan_pays)
            patient_vals.append(r.final_patient_oop)

        x = range(len(labels))
        bar_width = 0.5

        bars1 = ax.bar(x, primary_vals, bar_width,
                       label="Primary Plan Pays", color=self.COLORS["primary"], alpha=0.9)
        bars2 = ax.bar(x, secondary_vals, bar_width, bottom=primary_vals,
                       label="Secondary Plan Pays", color=self.COLORS["secondary"], alpha=0.9)
        bars3 = ax.bar(x, patient_vals, bar_width,
                       bottom=[p + s for p, s in zip(primary_vals, secondary_vals)],
                       label="Patient OOP", color=self.COLORS["patient"], alpha=0.9)

        # Add value labels on bars
        for bars, vals in [(bars1, primary_vals), (bars2, secondary_vals), (bars3, patient_vals)]:
            for bar, val in zip(bars, vals):
                if val > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                            f"₹{val:,.0f}", ha="center", va="center",
                            fontsize=9, fontweight="bold", color="white")

        ax.set_xlabel("Claim", fontsize=12, fontweight="bold")
        ax.set_ylabel("Amount (₹)", fontsize=12, fontweight="bold")
        ax.set_title("COB Payment Breakdown by Claim",
                     fontsize=14, fontweight="bold", pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.legend(loc="upper right", fontsize=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"₹{x:,.0f}"))

        plt.tight_layout()
        path = os.path.join(self.output_dir, "cost_breakdown.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def _generate_savings_comparison(self, results: list[COBResult]) -> str:
        """Generate comparison chart: With COB vs Without COB."""
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor(self.COLORS["bg"])
        ax.set_facecolor(self.COLORS["bg"])

        labels = [f"{r.patient_name}\n({r.claim_type.title()})" for r in results]
        labels.append("Family Total")

        without_cob = [r.single_plan_oop for r in results]
        without_cob.append(sum(without_cob))

        with_cob = [r.final_patient_oop for r in results]
        with_cob.append(sum(with_cob))

        savings = [w - c for w, c in zip(without_cob, with_cob)]

        x = range(len(labels))
        bar_width = 0.3

        bars1 = ax.bar([i - bar_width / 2 for i in x], without_cob, bar_width,
                       label="Without COB (Single Plan)", color="#EF4444", alpha=0.85)
        bars2 = ax.bar([i + bar_width / 2 for i in x], with_cob, bar_width,
                       label="With COB (Dual Coverage)", color="#22C55E", alpha=0.85)

        # Add savings annotations
        for i, (wo, wi, sav) in enumerate(zip(without_cob, with_cob, savings)):
            if sav > 0:
                ax.annotate(f"Save ₹{sav:,.0f}",
                           xy=(i, max(wo, wi) + 5000),
                           ha="center", fontsize=9, fontweight="bold",
                           color=self.COLORS["savings"])

        # Add value labels
        for bars, vals in [(bars1, without_cob), (bars2, with_cob)]:
            for bar, val in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1500,
                        f"₹{val:,.0f}", ha="center", va="bottom", fontsize=8)

        ax.set_ylabel("Out-of-Pocket Cost (₹)", fontsize=12, fontweight="bold")
        ax.set_title("COB Savings: Dual Coverage vs Single Plan",
                     fontsize=14, fontweight="bold", pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.legend(loc="upper left", fontsize=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"₹{x:,.0f}"))

        plt.tight_layout()
        path = os.path.join(self.output_dir, "savings_comparison.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def _generate_flow_diagram(self, results: list[COBResult]) -> str:
        """Generate a horizontal flow diagram showing money distribution."""
        fig, axes = plt.subplots(len(results), 1, figsize=(12, 5 * len(results)))
        fig.patch.set_facecolor(self.COLORS["bg"])

        if len(results) == 1:
            axes = [axes]

        for ax, result in zip(axes, results):
            ax.set_facecolor(self.COLORS["bg"])
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 4)
            ax.axis("off")

            total = result.total_charge
            primary_pct = result.primary_eob.plan_pays / total
            secondary_pct = result.secondary_eob.plan_pays / total
            patient_pct = result.final_patient_oop / total

            # Title
            ax.text(5, 3.7, f"{result.patient_name} — {result.claim_type.title()} (₹{total:,.0f})",
                    ha="center", fontsize=13, fontweight="bold")

            # Total box
            box_total = mpatches.FancyBboxPatch((0.2, 1.5), 2, 1.2,
                                                 boxstyle="round,pad=0.1",
                                                 facecolor=self.COLORS["total"], alpha=0.9)
            ax.add_patch(box_total)
            ax.text(1.2, 2.1, f"Total Charge\n₹{total:,.0f}",
                    ha="center", va="center", color="white", fontsize=10, fontweight="bold")

            # Primary box
            box_primary = mpatches.FancyBboxPatch((3.2, 2.3), 2.2, 0.9,
                                                   boxstyle="round,pad=0.1",
                                                   facecolor=self.COLORS["primary"], alpha=0.9)
            ax.add_patch(box_primary)
            ax.text(4.3, 2.75, f"Primary ({result.primary_plan_id})\n₹{result.primary_eob.plan_pays:,.0f} ({primary_pct:.0%})",
                    ha="center", va="center", color="white", fontsize=9, fontweight="bold")

            # Secondary box
            box_secondary = mpatches.FancyBboxPatch((3.2, 1.0), 2.2, 0.9,
                                                     boxstyle="round,pad=0.1",
                                                     facecolor=self.COLORS["secondary"], alpha=0.9)
            ax.add_patch(box_secondary)
            ax.text(4.3, 1.45, f"Secondary ({result.secondary_plan_id})\n₹{result.secondary_eob.plan_pays:,.0f} ({secondary_pct:.0%})",
                    ha="center", va="center", color="white", fontsize=9, fontweight="bold")

            # Patient box
            box_patient = mpatches.FancyBboxPatch((6.5, 1.5), 2.5, 1.2,
                                                   boxstyle="round,pad=0.1",
                                                   facecolor=self.COLORS["patient"], alpha=0.9)
            ax.add_patch(box_patient)
            ax.text(7.75, 2.1, f"Patient OOP\n₹{result.final_patient_oop:,.0f} ({patient_pct:.0%})",
                    ha="center", va="center", color="white", fontsize=10, fontweight="bold")

            # Arrows
            ax.annotate("", xy=(3.1, 2.7), xytext=(2.3, 2.2),
                        arrowprops=dict(arrowstyle="->", lw=2, color=self.COLORS["primary"]))
            ax.annotate("", xy=(3.1, 1.5), xytext=(2.3, 1.9),
                        arrowprops=dict(arrowstyle="->", lw=2, color=self.COLORS["secondary"]))
            ax.annotate("", xy=(6.4, 2.1), xytext=(5.5, 2.1),
                        arrowprops=dict(arrowstyle="->", lw=2, color=self.COLORS["patient"]))

        plt.tight_layout()
        path = os.path.join(self.output_dir, "cost_flow_diagram.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path
