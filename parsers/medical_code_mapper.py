"""Medical Code Mapper: Maps clinical descriptions to CPT and ICD-10 codes.

This module infers standardized medical codes from free-text clinical descriptions
extracted via OCR or PDF parsing. This is critical for insurance claim processing.
"""
import re
from dataclasses import dataclass


@dataclass
class MedicalCode:
    """A standardized medical code with its description."""
    code: str
    code_type: str  # "CPT" or "ICD-10"
    description: str
    category: str  # e.g., "surgery", "therapy", "diagnosis"


# Valid CPT codes used in this system
VALID_CPT_CODES = {
    "29888": MedicalCode(
        code="29888",
        code_type="CPT",
        description="Arthroscopically aided anterior cruciate ligament repair/augmentation/reconstruction",
        category="surgery"
    ),
    "29881": MedicalCode(
        code="29881",
        code_type="CPT",
        description="Arthroscopy, knee, surgical; with meniscectomy including any meniscal shaving",
        category="surgery"
    ),
    "97161": MedicalCode(
        code="97161",
        code_type="CPT",
        description="Physical therapy evaluation, low complexity",
        category="therapy"
    ),
    "97110": MedicalCode(
        code="97110",
        code_type="CPT",
        description="Therapeutic procedure, therapeutic exercises to develop strength and endurance, flexibility and range of motion",
        category="therapy"
    ),
}

# Valid ICD-10 codes used in this system
VALID_ICD10_CODES = {
    "S83.511A": MedicalCode(
        code="S83.511A",
        code_type="ICD-10",
        description="Sprain of anterior cruciate ligament of right knee, initial encounter",
        category="diagnosis"
    ),
    "S83.211A": MedicalCode(
        code="S83.211A",
        code_type="ICD-10",
        description="Bucket-handle tear of medial meniscus, current injury, right knee, initial encounter",
        category="diagnosis"
    ),
    "M54.50": MedicalCode(
        code="M54.50",
        code_type="ICD-10",
        description="Low back pain, unspecified",
        category="diagnosis"
    ),
}


class MedicalCodeMapper:
    """Maps clinical text descriptions to standardized CPT and ICD-10 codes."""

    # Mapping patterns: description keywords → CPT code
    CPT_PATTERNS = {
        "29888": [
            r"acl.*(?:reconstruction|repair|augmentation)",
            r"anterior cruciate.*(?:reconstruction|repair)",
            r"arthroscop.*acl",
        ],
        "29881": [
            r"meniscectomy",
            r"meniscal.*(?:shaving|repair)",
            r"arthroscopy.*knee.*surgical",
            r"knee.*arthroscopy.*meniscus",
        ],
        "97161": [
            r"physical therapy.*evaluation",
            r"pt.*evaluation",
            r"physiotherapy.*(?:evaluation|assessment|initial)",
            r"initial.*(?:assessment|evaluation).*(?:physio|therapy|pt)",
        ],
        "97110": [
            r"therapeutic.*exercise",
            r"therapy.*exercise",
            r"exercise.*therapy",
            r"(?:strength|flexibility|range of motion).*exercise",
        ],
    }

    # Mapping patterns: clinical findings → ICD-10 code
    ICD10_PATTERNS = {
        "S83.511A": [
            r"(?:complete|full).*(?:tear|rupture|disruption).*(?:acl|anterior cruciate)",
            r"(?:acl|anterior cruciate).*(?:tear|rupture|disruption)",
            r"sprain.*anterior cruciate",
        ],
        "S83.211A": [
            r"medial meniscus.*tear",
            r"meniscal.*tear.*medial",
            r"tear.*medial meniscus",
            r"meniscus.*(?:tear|damage).*medial",
        ],
        "M54.50": [
            r"low(?:er)? back pain",
            r"chronic.*back.*pain",
            r"lumbar.*pain",
            r"lumbago",
        ],
    }

    def map_description_to_cpt(self, description: str) -> list[MedicalCode]:
        """Map a clinical description to CPT procedure codes."""
        lower_desc = description.lower()
        matched_codes = []

        for code, patterns in self.CPT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, lower_desc):
                    matched_codes.append(VALID_CPT_CODES[code])
                    break

        return matched_codes

    def map_findings_to_icd10(self, clinical_text: str) -> list[MedicalCode]:
        """Map clinical findings text to ICD-10 diagnosis codes."""
        lower_text = clinical_text.lower()
        matched_codes = []

        for code, patterns in self.ICD10_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, lower_text):
                    matched_codes.append(VALID_ICD10_CODES[code])
                    break

        return matched_codes

    def extract_cpt_from_text(self, text: str) -> list[MedicalCode]:
        """Extract CPT codes directly mentioned in text (e.g., 'CPT 29888')."""
        found = []
        # Match patterns like: CPT 29888, CPT-29888, CPT: 29888, code 29888
        cpt_pattern = r"(?:CPT|cpt|Code|code)[\s:\-]*?(\d{5})"
        matches = re.findall(cpt_pattern, text)

        for code in matches:
            if code in VALID_CPT_CODES:
                found.append(VALID_CPT_CODES[code])

        return found

    def validate_code(self, code: str) -> bool:
        """Check if a code exists in our valid code sets."""
        return code in VALID_CPT_CODES or code in VALID_ICD10_CODES
