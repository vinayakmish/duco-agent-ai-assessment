"""Pre-Authorization Agent: Generates IRDAI-compliant pre-auth letters.

This agent creates pre-authorization request letters for insurance claims,
following the IRDAI (Insurance Regulatory and Development Authority of India)
format with three mandatory sections.
"""
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from jinja2 import Environment, FileSystemLoader, BaseLoader

from models.claim import Claim, COBResult


@dataclass
class PreAuthRequest:
    """Data required to generate a pre-authorization letter."""
    patient_name: str
    patient_dob: str
    patient_gender: str
    policy_number: str
    employee_id: str
    plan_id: str
    insurer_name: str
    plan_name: str
    is_primary: bool
    # Medical details
    diagnosis: str
    icd_codes: list[str] = field(default_factory=list)
    proposed_treatment: str = ""
    cpt_codes: list[str] = field(default_factory=list)
    procedure_descriptions: list[str] = field(default_factory=list)
    clinical_findings: str = ""
    admission_type: str = "Planned"
    # Financial
    estimated_cost: float = 0.0
    # Provider
    hospital_name: str = "Mumbai Ortho Center"
    hospital_address: str = "15, Turner Road, Bandra West, Mumbai - 400050"
    treating_doctor: str = ""
    doctor_registration: str = ""
    # COB
    has_dual_coverage: bool = True
    other_insurer_name: str = ""
    other_policy_number: str = ""
    # Dates
    proposed_admission_date: str = ""
    expected_stay_days: int = 0


PREAUTH_TEMPLATE = """
================================================================================
                    PRE-AUTHORIZATION REQUEST FORM
================================================================================
To: {{ insurer_name }} ({{ plan_name }})
Date: {{ current_date }}
Reference: PA/{{ plan_id }}/{{ reference_year }}/{{ reference_number }}

================================================================================
SECTION 1: PATIENT / INSURED DETAILS
================================================================================

Patient Name           : {{ patient_name }}
Date of Birth          : {{ patient_dob }}
Gender                 : {{ patient_gender }}
Policy Number          : {{ policy_number }}
Employee ID            : {{ employee_id }}
Plan                   : {{ plan_name }}
Role on Plan           : {{ "Primary Policyholder" if is_primary else "Dependent (Spouse)" }}

DUAL COVERAGE DISCLOSURE (IRDAI Mandate):
  Other Insurance      : {{ other_insurer_name }}
  Other Policy No.     : {{ other_policy_number }}
  This plan is         : {{ "PRIMARY" if is_primary else "SECONDARY" }} for this claim

Authorization: The undersigned hereby authorizes {{ insurer_name }} and its
designated TPA to access relevant medical records for the purpose of
processing this pre-authorization request.

================================================================================
SECTION 2: MEDICAL DETAILS
================================================================================

Clinical Presentation  : {{ diagnosis }}
ICD-10 Diagnosis Code(s): {{ icd_codes | join(", ") }}

Clinical Findings:
{{ clinical_findings }}

Proposed Treatment     : {{ proposed_treatment }}
Admission Type         : {{ admission_type }}
{% if proposed_admission_date %}Proposed Admission Date: {{ proposed_admission_date }}
Expected Stay          : {{ expected_stay_days }} days{% endif %}

Procedures Requested:
{% for i in range(cpt_codes | length) %}  {{ i + 1 }}. CPT {{ cpt_codes[i] }} — {{ procedure_descriptions[i] }}
{% endfor %}
Treating Physician     : {{ treating_doctor }}
Registration No.       : {{ doctor_registration }}

MEDICAL NECESSITY JUSTIFICATION:
{{ medical_necessity }}

Past Medical History   : No significant chronic conditions reported.

================================================================================
SECTION 3: FINANCIAL & ADMINISTRATIVE DETAILS
================================================================================

Estimated Total Cost   : Rs. {{ "{:,.0f}".format(estimated_cost) }}/-
Hospital Name          : {{ hospital_name }}
Hospital Address       : {{ hospital_address }}

Cost Breakdown:
  Surgical Procedure(s): Rs. {{ "{:,.0f}".format(estimated_cost) }}/-
  (Additional costs for anaesthesia, hospital stay, and post-operative
   care will be billed separately as per actuals.)

================================================================================
COMPLIANCE NOTE
================================================================================
This pre-authorization request is submitted {{ compliance_timeline }}.
As per IRDAI guidelines, the insurer is requested to provide approval or
communicate reasons for denial in writing within the stipulated timeframe.

Pre-authorization approval is acknowledged as a preliminary approval and
does not constitute an unconditional guarantee of payment. Final settlement
is subject to review of the discharge summary and final hospital bill.

================================================================================

Submitted by: {{ treating_doctor }}
Designation : Consultant Orthopaedic Surgeon
Hospital    : {{ hospital_name }}
Date        : {{ current_date }}

Patient Signature: _________________________
Date             : {{ current_date }}
================================================================================
"""

COB_COVER_LETTER_TEMPLATE = """
================================================================================
              COORDINATION OF BENEFITS (COB) COVER LETTER
================================================================================
To: {{ secondary_insurer_name }}
Date: {{ current_date }}
Re: Secondary Claim — COB Processing

Dear Claims Department,

This letter accompanies the secondary claim submission for the following patient
under the Coordination of Benefits provision:

Patient Name           : {{ patient_name }}
Your Policy Number     : {{ secondary_policy_number }}
Role on Your Plan      : Dependent (Spouse)

PRIMARY INSURER DETAILS:
  Primary Insurer      : {{ primary_insurer_name }}
  Primary Policy No.   : {{ primary_policy_number }}
  Primary Plan Payment : Rs. {{ "{:,.0f}".format(primary_paid) }}/-
  Primary EOB Attached : Yes

CLAIM SUMMARY:
  Total Charge         : Rs. {{ "{:,.0f}".format(total_charge) }}/-
  Primary Plan Paid    : Rs. {{ "{:,.0f}".format(primary_paid) }}/-
  Remaining Balance    : Rs. {{ "{:,.0f}".format(remaining_balance) }}/-

As per COB guidelines and IRDAI regulations, we request processing of the
remaining balance of Rs. {{ "{:,.0f}".format(remaining_balance) }}/- under
the secondary coverage.

The primary insurer's Explanation of Benefits (EOB) is attached for reference.

Thank you for your prompt attention to this matter.

Sincerely,
{{ patient_name }}

Enclosures:
  1. Primary Insurer EOB
  2. Original claim documents
  3. Pre-authorization approval (if applicable)
================================================================================
"""


class PreAuthAgent:
    """Agent responsible for generating pre-authorization letters."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.env = Environment(loader=BaseLoader())
        os.makedirs(output_dir, exist_ok=True)

    def generate_preauth_letter(self, request: PreAuthRequest) -> str:
        """Generate a pre-authorization letter from the request data."""
        template = self.env.from_string(PREAUTH_TEMPLATE)

        # Build medical necessity justification
        medical_necessity = self._build_medical_necessity(request)

        # Compliance timeline
        if request.admission_type == "Planned":
            compliance_timeline = (
                "at least 48 hours prior to the planned admission date, "
                "in compliance with IRDAI pre-authorization timelines"
            )
        else:
            compliance_timeline = (
                "within 24 hours of emergency admission, "
                "in compliance with IRDAI emergency pre-authorization timelines"
            )

        now = datetime.now()
        letter = template.render(
            current_date=now.strftime("%d-%b-%Y"),
            reference_year=now.strftime("%Y"),
            reference_number=f"{hash(request.patient_name + request.plan_id) % 10000:04d}",
            compliance_timeline=compliance_timeline,
            medical_necessity=medical_necessity,
            **request.__dict__
        )

        return letter

    def generate_cob_cover_letter(
        self,
        patient_name: str,
        primary_insurer_name: str,
        primary_policy_number: str,
        secondary_insurer_name: str,
        secondary_policy_number: str,
        total_charge: float,
        primary_paid: float
    ) -> str:
        """Generate a COB cover letter for secondary insurer submission."""
        template = self.env.from_string(COB_COVER_LETTER_TEMPLATE)

        letter = template.render(
            current_date=datetime.now().strftime("%d-%b-%Y"),
            patient_name=patient_name,
            primary_insurer_name=primary_insurer_name,
            primary_policy_number=primary_policy_number,
            secondary_insurer_name=secondary_insurer_name,
            secondary_policy_number=secondary_policy_number,
            total_charge=total_charge,
            primary_paid=primary_paid,
            remaining_balance=total_charge - primary_paid
        )

        return letter

    def _build_medical_necessity(self, request: PreAuthRequest) -> str:
        """Build the medical necessity justification section."""
        if "ACL" in request.diagnosis or "S83.511A" in request.icd_codes:
            return (
                "  The patient sustained a sports injury resulting in a complete tear of the\n"
                "  anterior cruciate ligament (ACL) and complex medial meniscus tear, confirmed\n"
                "  by MRI imaging. The MRI findings demonstrate full-thickness disruption of ACL\n"
                "  fibers near the femoral attachment with associated bone marrow edema pattern\n"
                "  consistent with a pivot-shift mechanism.\n\n"
                "  Conservative management is not indicated for a complete ACL tear in an active\n"
                "  patient, as it would lead to chronic knee instability, recurrent giving way\n"
                "  episodes, and accelerated progression of osteoarthritis.\n\n"
                "  Arthroscopic ACL reconstruction (CPT 29888) with concurrent meniscal surgery\n"
                "  (CPT 29881) is the standard of care and is medically necessary to restore\n"
                "  knee stability and prevent further joint deterioration.\n\n"
                "  Supporting Documents:\n"
                "    - MRI Right Knee Report (dated April 2024)\n"
                "    - Orthopaedic consultation notes\n"
                "    - Clinical examination findings (positive Lachman, anterior drawer)"
            )
        elif "M54.50" in request.icd_codes:
            return (
                "  The patient presents with chronic lower back pain (ICD-10: M54.50) that\n"
                "  has been ongoing since January 2024. Physical therapy evaluation and\n"
                "  therapeutic exercises are medically necessary to:\n"
                "    - Reduce pain and improve functional mobility\n"
                "    - Strengthen core musculature and improve spinal stability\n"
                "    - Prevent progression to more invasive interventions\n\n"
                "  The prescribed treatment plan includes initial evaluation (CPT 97161)\n"
                "  followed by supervised therapeutic exercise sessions (CPT 97110) targeting\n"
                "  strength, flexibility, and range of motion.\n\n"
                "  Supporting Documents:\n"
                "    - Referring physician's prescription\n"
                "    - Clinical examination findings"
            )
        return "  Medical necessity justification based on clinical findings."

    def generate_all_letters(self, cob_results: list) -> dict[str, str]:
        """Generate all required pre-auth and COB letters.

        Returns dict mapping filename to letter content.
        """
        letters = {}

        for result in cob_results:
            if result.claim_type == "surgery":
                # Pre-auth for primary (Plan B for Aarav)
                primary_req = PreAuthRequest(
                    patient_name=result.patient_name,
                    patient_dob="22/07/1986",
                    patient_gender="Male",
                    policy_number="INS2-2024-HLT-91205",
                    employee_id="EMP-B-55891",
                    plan_id=result.primary_plan_id,
                    insurer_name="Insurer2",
                    plan_name="Premium Health Plus - Plan B",
                    is_primary=True,
                    diagnosis="Complete ACL Tear + Medial Meniscus Tear, Right Knee",
                    icd_codes=["S83.511A", "S83.211A"],
                    proposed_treatment="ACL Reconstruction with Meniscal Repair",
                    cpt_codes=["29888", "29881"],
                    procedure_descriptions=[
                        "Arthroscopically Aided ACL Reconstruction",
                        "Arthroscopy, Knee, Surgical; with Meniscectomy"
                    ],
                    clinical_findings=(
                        "MRI confirms complete ACL tear with femoral attachment disruption.\n"
                        "Complex medial meniscus tear involving the posterior horn.\n"
                        "Bone marrow contusion consistent with pivot-shift injury.\n"
                        "Positive Lachman test and anterior drawer sign on clinical exam."
                    ),
                    estimated_cost=result.total_charge,
                    treating_doctor="Dr. Vikram Mehta, MS Ortho, Sports Medicine",
                    doctor_registration="MMC/2008/12345",
                    proposed_admission_date=(datetime.now() + timedelta(days=14)).strftime("%d-%b-%Y"),
                    expected_stay_days=3,
                    other_insurer_name="Insurer1",
                    other_policy_number="INS1-2024-HLT-78432-D1"
                )
                letters["preauth_aarav_planB.txt"] = self.generate_preauth_letter(primary_req)

                # Pre-auth for secondary (Plan A for Aarav as dependent)
                secondary_req = PreAuthRequest(
                    patient_name=result.patient_name,
                    patient_dob="22/07/1986",
                    patient_gender="Male",
                    policy_number="INS1-2024-HLT-78432-D1",
                    employee_id="EMP-A-10234 (Spouse: Priya Sen)",
                    plan_id=result.secondary_plan_id,
                    insurer_name="Insurer1",
                    plan_name="Corporate Health Shield - Plan A",
                    is_primary=False,
                    diagnosis="Complete ACL Tear + Medial Meniscus Tear, Right Knee",
                    icd_codes=["S83.511A", "S83.211A"],
                    proposed_treatment="ACL Reconstruction with Meniscal Repair",
                    cpt_codes=["29888", "29881"],
                    procedure_descriptions=[
                        "Arthroscopically Aided ACL Reconstruction",
                        "Arthroscopy, Knee, Surgical; with Meniscectomy"
                    ],
                    clinical_findings=(
                        "MRI confirms complete ACL tear with femoral attachment disruption.\n"
                        "Complex medial meniscus tear involving the posterior horn.\n"
                        "Primary insurer (Insurer2) pre-authorization obtained."
                    ),
                    estimated_cost=result.total_charge,
                    treating_doctor="Dr. Vikram Mehta, MS Ortho, Sports Medicine",
                    doctor_registration="MMC/2008/12345",
                    proposed_admission_date=(datetime.now() + timedelta(days=14)).strftime("%d-%b-%Y"),
                    expected_stay_days=3,
                    other_insurer_name="Insurer2",
                    other_policy_number="INS2-2024-HLT-91205"
                )
                letters["preauth_aarav_planA.txt"] = self.generate_preauth_letter(secondary_req)

                # COB cover letter
                letters["cob_cover_aarav.txt"] = self.generate_cob_cover_letter(
                    patient_name="Aarav Sen",
                    primary_insurer_name="Insurer2",
                    primary_policy_number="INS2-2024-HLT-91205",
                    secondary_insurer_name="Insurer1",
                    secondary_policy_number="INS1-2024-HLT-78432-D1",
                    total_charge=result.total_charge,
                    primary_paid=result.primary_eob.plan_pays
                )

            elif result.claim_type == "therapy":
                # Pre-auth for Priya's PT (Plan A primary)
                pt_req = PreAuthRequest(
                    patient_name=result.patient_name,
                    patient_dob="15/03/1988",
                    patient_gender="Female",
                    policy_number="INS1-2024-HLT-78432",
                    employee_id="EMP-A-10234",
                    plan_id=result.primary_plan_id,
                    insurer_name="Insurer1",
                    plan_name="Corporate Health Shield - Plan A",
                    is_primary=True,
                    diagnosis="Chronic Lower Back Pain",
                    icd_codes=["M54.50"],
                    proposed_treatment="Physical Therapy — Evaluation and Therapeutic Exercise",
                    cpt_codes=["97161", "97110"],
                    procedure_descriptions=[
                        "Physical Therapy Evaluation, Low Complexity",
                        "Therapeutic Exercise (6 sessions)"
                    ],
                    clinical_findings=(
                        "Patient presents with chronic lower back pain ongoing since January 2024.\n"
                        "Referred by Dr. Ananya Sharma, MD (PMR) for physical therapy."
                    ),
                    admission_type="Outpatient / Day Care",
                    estimated_cost=result.total_charge,
                    treating_doctor="Dr. Ananya Sharma, MBBS, MD (PMR)",
                    doctor_registration="MMC/2012/56789",
                    other_insurer_name="Insurer2",
                    other_policy_number="INS2-2024-HLT-91205-D1"
                )
                letters["preauth_priya_planA.txt"] = self.generate_preauth_letter(pt_req)

        # Save all letters
        for filename, content in letters.items():
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        return letters
