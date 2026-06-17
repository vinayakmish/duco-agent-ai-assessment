"""DuCO-Agent: Dual Coverage Orchestration Agent for Health Insurance COB.

Main entry point. Runs the full agentic pipeline:
  INTAKE → EXTRACTION → COB_REASONING → DOCUMENT_GENERATION → VALIDATION → COMPLETE

Usage:
    python main.py                    # Full pipeline
    python main.py --generate-data    # Generate mock data first, then run pipeline
    python main.py --data-only        # Only generate mock data
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.logging import RichHandler

console = Console()


def setup_logging(verbose: bool = False):
    """Configure structured logging with rich output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, show_path=False, markup=True)]
    )


def generate_mock_data():
    """Generate mock medical documents."""
    console.print(Panel("Generating Mock Medical Documents", style="bold blue"))
    from scripts.generate_mock_data import (
        generate_pt_invoice,
        generate_mri_report,
        generate_surgeon_estimate,
    )
    generate_pt_invoice()
    generate_mri_report()
    generate_surgeon_estimate()
    console.print("[green]✓ Mock data generated in data/ directory[/green]\n")


def print_banner():
    """Print the DuCO-Agent banner."""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   ██████╗ ██╗   ██╗ ██████╗ ██████╗                         ║
    ║   ██╔══██╗██║   ██║██╔════╝██╔═══██╗                        ║
    ║   ██║  ██║██║   ██║██║     ██║   ██║  Agent                 ║
    ║   ██║  ██║██║   ██║██║     ██║   ██║                        ║
    ║   ██████╔╝╚██████╔╝╚██████╗╚██████╔╝                       ║
    ║   ╚═════╝  ╚═════╝  ╚═════╝ ╚═════╝                        ║
    ║                                                              ║
    ║   Dual Coverage Orchestration Agent                          ║
    ║   Health Insurance Coordination of Benefits (COB)            ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_results(result: dict):
    """Pretty-print pipeline results."""
    console.print("\n")
    console.print(Panel("Pipeline Results", style="bold green"))

    # Pipeline Summary
    pipeline = result["pipeline_summary"]
    console.print(f"\n[bold]Pipeline States Traversed:[/bold] {pipeline['total_transitions']}")
    console.print(f"[bold]Validation Loops:[/bold] {pipeline['validation_loops']}")

    # COB Results Table
    table = Table(title="COB Payment Breakdown", show_header=True,
                  header_style="bold magenta")
    table.add_column("Patient", style="cyan")
    table.add_column("Claim Type", style="white")
    table.add_column("Total Charge", justify="right", style="white")
    table.add_column("Primary Pays", justify="right", style="green")
    table.add_column("Secondary Pays", justify="right", style="blue")
    table.add_column("Patient OOP", justify="right", style="red")
    table.add_column("Savings", justify="right", style="bold green")

    total_oop = 0
    total_savings = 0
    for cob in result["cob_results"]:
        table.add_row(
            cob["patient"],
            cob["claim_type"].title(),
            f"₹{cob['total_charge']:,.0f}",
            f"₹{cob['primary_pays']:,.0f}",
            f"₹{cob['secondary_pays']:,.0f}",
            f"₹{cob['patient_oop']:,.0f}",
            f"₹{cob['savings']:,.0f}",
        )
        total_oop += cob["patient_oop"]
        total_savings += cob["savings"]

    table.add_section()
    table.add_row(
        "FAMILY TOTAL", "", "",
        "", "", f"₹{total_oop:,.0f}", f"₹{total_savings:,.0f}",
        style="bold"
    )
    console.print(table)

    # Validation Summary
    validation = result["validation_summary"]
    style = "green" if validation["all_passed"] else "red"
    console.print(
        f"\n[bold]Validation:[/bold] [{style}]{validation['passed']}/{validation['total_checks']} "
        f"checks passed[/{style}]"
    )
    if validation["failures"]:
        for f in validation["failures"]:
            console.print(f"  [red]✗ {f['check']}: {f['message']}[/red]")

    # Generated Files
    console.print(f"\n[bold]Generated Documents:[/bold]")
    for name in result.get("letters", []):
        console.print(f"  [green]✓[/green] output/{name}")
    for name, path in result.get("outputs", {}).items():
        if "error" not in name:
            console.print(f"  [green]✓[/green] {path}")

    console.print(f"\n[bold cyan]Family saves ₹{total_savings:,.0f} with dual coverage![/bold cyan]\n")


def main():
    parser = argparse.ArgumentParser(
        description="DuCO-Agent: Dual Coverage Orchestration for Health Insurance COB"
    )
    parser.add_argument("--generate-data", action="store_true",
                        help="Generate mock medical documents before running pipeline")
    parser.add_argument("--data-only", action="store_true",
                        help="Only generate mock data, don't run pipeline")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--output-dir", default="output",
                        help="Output directory (default: output)")
    parser.add_argument("--data-dir", default="data",
                        help="Data directory (default: data)")
    args = parser.parse_args()

    setup_logging(args.verbose)
    print_banner()

    # Generate mock data if requested
    if args.generate_data or args.data_only:
        generate_mock_data()
        if args.data_only:
            console.print("[green]Done! Mock data generated.[/green]")
            return

    # Check input files
    required_files = [
        os.path.join(args.data_dir, "user_query.txt"),
    ]
    for f in required_files:
        if not os.path.exists(f):
            console.print(f"[red]Missing required file: {f}[/red]")
            console.print("[yellow]Run with --generate-data to create mock inputs.[/yellow]")
            sys.exit(1)

    # Run pipeline
    console.print(Panel("Running DuCO-Agent Pipeline", style="bold blue"))
    from orchestrator.planner import PlannerAgent

    planner = PlannerAgent(data_dir=args.data_dir, output_dir=args.output_dir)
    result = planner.run()

    # Print results
    print_results(result)

    # Save results JSON
    os.makedirs(args.output_dir, exist_ok=True)
    result_path = os.path.join(args.output_dir, "pipeline_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    console.print(f"[dim]Full results saved to {result_path}[/dim]")


if __name__ == "__main__":
    main()
