# DuCO-Agent: Dual Coverage Orchestration Agent

An **agentic AI system** for processing health insurance claims under **Coordination of Benefits (COB)** when a patient has dual coverage. Built with a Planner/Critic architecture and a 6-state pipeline.

## Scenario

**Priya and Aarav Sen** are a married couple in Mumbai with dual health insurance:

| Plan | Insurer | Primary Holder | Dependent |
|------|---------|---------------|-----------|
| Plan A | Insurer1 (Corporate Health Shield) | Priya Sen | Aarav Sen |
| Plan B | Insurer2 (Premium Health Plus) | Aarav Sen | Priya Sen |

**Claims:**
- **Aarav**: ACL reconstruction + meniscectomy (₹4,50,000)
- **Priya**: Physical therapy for chronic lower back pain (₹30,000)

## Architecture

```
                    ┌─────────────────┐
                    │   User Query    │
                    │  (user_query.txt)│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Planner Agent  │ ◄── Decides which tools to invoke
                    │  (11 tools)     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐         ┌────▼────┐          ┌────▼────┐
   │parse_   │         │parse_   │          │parse_   │
   │image()  │         │pdf()    │          │text()   │
   │EasyOCR  │         │pdfplumber│         │Intent   │
   └────┬────┘         └────┬────┘          └────┬────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │lookup_medical_  │
                    │code()           │
                    │CPT / ICD-10 map │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │calculate_claim()│
                    │COB Engine       │
                    │Employee-First   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐         ┌────▼────┐          ┌────▼────┐
   │generate_│         │generate_│          │generate_│
   │preauth()│         │visual() │          │briefing()│
   └────┬────┘         └────┬────┘          └────┬────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Critic Agent   │ ◄── Validates all outputs
                    │  (4 checks)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Loop back?    │──── Yes ──► Re-execute failed stage
                    └────────┬────────┘
                             │ No
                    ┌────────▼────────┐
                    │    COMPLETE     │
                    └─────────────────┘
```

### Planner Agent (decides actions)

| Tool | Description |
|------|-------------|
| `parse_image()` | OCR extraction via EasyOCR / pytesseract |
| `parse_pdf()` | Clinical text extraction via pdfplumber |
| `parse_text()` | User query intent and entity parsing |
| `lookup_medical_code()` | Map descriptions to CPT/ICD-10 codes |
| `verify_coverage()` | Check coverage via mock insurance API |
| `calculate_claim()` | Run COB determination + financial calc |
| `check_preauth()` | Check pre-authorization requirements |
| `generate_preauth()` | Generate IRDAI-compliant pre-auth letters |
| `generate_visual()` | Create cost flow visualizations |
| `generate_briefing()` | Create patient-friendly summary |
| `validate_calculation()` | Trigger Critic agent checks |

### Critic Agent (validates results)

| Validation | Check | Reflection Loop |
|------------|-------|-----------------|
| `validate_calculations()` | primary + secondary + OOP == total_charges | `if total != expected: recalculate()` |
| `validate_codes()` | All CPT/ICD-10 codes in valid set | `if code invalid: remap_code()` |
| `validate_preauth()` | All required pre-auth letters generated | `if missing: generate_preauth()` |
| `validate_compliance()` | IRDAI non-duplication rule held | `if violated: fix_compliance()` |

### 6-State Pipeline

```
INTAKE → EXTRACTION → COB_REASONING → DOCUMENT_GENERATION → VALIDATION → COMPLETE
                                                                   │
                                                              (loop back on failure)
```

## Financial Results

### Aarav's ACL Surgery (₹4,50,000)

| Step | Description | Amount |
|------|-------------|--------|
| 1 | Total Charges | ₹4,50,000 |
| 2 | **Primary** (Plan B) Deductible | -₹15,000 |
| 3 | Plan B pays 70% of ₹4,35,000 | ₹3,04,500 |
| 4 | Remainder to Secondary | ₹1,45,500 |
| 5 | **Secondary** (Plan A) Deductible | -₹10,000 |
| 6 | Plan A pays 80% of ₹1,35,500 | ₹1,08,400 |
| **7** | **Patient OOP** | **₹37,100** |

### Priya's Physical Therapy (₹30,000)

| Step | Description | Amount |
|------|-------------|--------|
| 1 | Total Charges | ₹30,000 |
| 2 | **Primary** (Plan A) Deductible | -₹10,000 |
| 3 | Plan A pays 80% of ₹20,000 | ₹16,000 |
| 4 | Remainder to Secondary | ₹14,000 |
| 5 | **Secondary** (Plan B) Deductible ₹15,000 > remainder | -₹14,000 |
| 6 | Plan B pays | ₹0 |
| **7** | **Patient OOP** | **₹14,000** |

### Family Summary

| Claim | Total | Primary Pays | Secondary Pays | Patient OOP |
|-------|-------|-------------|----------------|-------------|
| Aarav (Surgery) | ₹4,50,000 | ₹3,04,500 | ₹1,08,400 | ₹37,100 |
| Priya (Therapy) | ₹30,000 | ₹16,000 | ₹0 | ₹14,000 |
| **Family Total** | **₹4,80,000** | **₹3,20,500** | **₹1,08,400** | **₹51,100** |

**Family saves ₹1,08,400** with dual coverage vs single plan!

## Medical Codes Used

| Code | Type | Description |
|------|------|-------------|
| `29888` | CPT | ACL Reconstruction (Arthroscopic) |
| `29881` | CPT | Meniscectomy (Arthroscopic) |
| `97161` | CPT | Physical Therapy Evaluation |
| `97110` | CPT | Therapeutic Exercise |
| `S83.511A` | ICD-10 | ACL Tear, Right Knee |
| `S83.211A` | ICD-10 | Medial Meniscus Tear, Right Knee |
| `M54.50` | ICD-10 | Low Back Pain, Unspecified |

> **Note**: `M54.50` is used instead of the deprecated `M54.5` per ICD-10-CM 2024 updates.

## Setup & Running

```bash
# 1. Clone and install dependencies
git clone https://github.com/vinayakmish/duco-agent-ai-assessment.git
cd duco-agent-ai-assessment
# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate      # Windows

pip install -r requirements.txt

# 2. Generate mock medical documents + run full pipeline
python main.py --generate-data

# 3. Run only mock data generation
python main.py --data-only

# 4. Run with verbose logging
python main.py --generate-data -v

# 5. Run tests
python -m pytest tests/ -v
```

## Generated Outputs

| Output | Format | Description |
|--------|--------|-------------|
| `preauth_aarav_planB.txt` | Text | Pre-auth letter for Aarav → Insurer2 (Primary) |
| `preauth_aarav_planA.txt` | Text | Pre-auth letter for Aarav → Insurer1 (Secondary) |
| `preauth_priya_planA.txt` | Text | Pre-auth letter for Priya → Insurer1 |
| `cob_cover_aarav.txt` | Text | COB cover letter for secondary insurer |
| `cost_breakdown.png` | Image | Stacked bar chart — payment breakdown |
| `savings_comparison.png` | Image | With COB vs Without COB comparison |
| `cost_flow_diagram.png` | Image | Visual money flow diagram |
| `financial_breakdown.md` | Markdown | Detailed step-by-step financial report |
| `patient_briefing.txt` | Text | Plain-language patient summary |
| `pipeline_result.json` | JSON | Full pipeline execution results |

## Project Structure

```
duco-agent-ai-assessment/
├── main.py                          # CLI entry point
├── requirements.txt                 # Python dependencies
├── config/
│   └── insurance_plans.json         # Plan A & B configuration
├── data/
│   ├── user_query.txt               # Aarav's voice-to-text query
│   ├── priya_pt_invoice.png         # (generated) PT invoice image
│   ├── aarav_mri_report.pdf         # (generated) MRI radiology report
│   └── surgeon_estimate.jpg         # (generated) Surgeon's estimate
├── agents/
│   ├── intake_agent.py              # Multi-modal document ingestion
│   ├── cob_agent.py                 # COB determination + calculations
│   ├── preauth_agent.py             # Pre-auth letter generation
│   └── output_agent.py              # Output orchestration
├── orchestrator/
│   ├── planner.py                   # Planner Agent (11 tools)
│   ├── critic.py                    # Critic Agent (4 validation loops)
│   ├── state_machine.py             # 6-state pipeline
│   └── tools.py                     # Tool registry with logging
├── parsers/
│   ├── ocr_parser.py                # EasyOCR + pytesseract fallback
│   ├── pdf_parser.py                # pdfplumber clinical extraction
│   ├── text_parser.py               # User query intent parser
│   └── medical_code_mapper.py       # CPT/ICD-10 code mapping
├── models/
│   ├── policy.py                    # Patient/role data models
│   └── claim.py                     # Claim/EOB/COBResult models
├── api/
│   ├── mock_insurance_api.py        # FastAPI mock insurance endpoints
│   └── plan_data.py                 # Insurance plan dataclasses
├── outputs/
│   ├── cost_flow_visualizer.py      # matplotlib charts
│   ├── financial_report.py          # Markdown report generator
│   └── patient_briefing.py          # Patient summary + optional audio
├── scripts/
│   └── generate_mock_data.py        # Generates realistic mock documents
└── tests/
    ├── test_intake_agent.py         # 14 parser/mapper tests
    ├── test_cob_agent.py            # 14 COB calculation tests
    └── test_mock_api.py             # 9 API integration tests
```

## Tests (37 total)

```
tests/test_intake_agent.py     — 14 tests (OCR mapping, code validation, text parsing)
tests/test_cob_agent.py        — 14 tests (COB math, invariants, IRDAI compliance)
tests/test_mock_api.py         —  9 tests (API endpoints, coverage, pre-auth)
```

All 37 tests passing ✓

## Assumptions & Disclaimers

> **Important**: The actual insurance policy values (deductibles, coinsurance percentages,
> OOP maximums) were **not provided** in the assessment problem statement. The values used
> here are **mock/assumed values** chosen to demonstrate the COB calculation engine:
>
> | Parameter | Plan A | Plan B |
> |-----------|--------|--------|
> | Deductible | ₹10,000 | ₹15,000 |
> | Coinsurance | 80/20 | 70/30 |
> | OOP Maximum | ₹1,00,000 | ₹1,50,000 |
>
> In production, these values would be fetched from the actual insurance policy documents
> or TPA (Third Party Administrator) APIs.

## Git Workflow

- **Branch Protection**: `main` branch requires Pull Requests (no direct commits)
- **Feature Branches**: `feature/intake-agent`, `feature/mock-apis`, `feature/cob-logic`, `feature/multi-modal-outputs`, `feature/orchestrator`
- **Semantic Commits**: All commits follow `feat(scope): description` convention
- **Squash Merge**: PRs merged via squash merge for clean history

## Tech Stack

- **Python 3.12+**
- **EasyOCR / pytesseract** — Image text extraction (OCR)
- **pdfplumber** — PDF clinical text parsing
- **FastAPI** — Mock insurance API
- **matplotlib** — Cost flow visualizations
- **Pillow + reportlab** — Mock document generation
- **Jinja2** — Pre-auth letter templating
- **Rich** — Terminal output formatting
- **pytest** — Test framework
