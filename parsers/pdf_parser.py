"""PDF Parser for clinical medical reports using pdfplumber."""
import os
from dataclasses import dataclass, field

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


@dataclass
class PDFResult:
    """Result of PDF text extraction."""
    raw_text: str
    pages: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    tables: list[list[list[str]]] = field(default_factory=list)


class PDFParser:
    """Parser for extracting clinical text from PDF documents."""

    def parse_pdf(self, pdf_path: str) -> PDFResult:
        """Extract text and tables from a PDF file."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        if not PDFPLUMBER_AVAILABLE:
            raise RuntimeError("pdfplumber is not installed. Run: pip install pdfplumber")

        pages_text = []
        all_tables = []

        with pdfplumber.open(pdf_path) as pdf:
            metadata = pdf.metadata or {}
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)

        raw_text = "\n\n".join(pages_text)

        return PDFResult(
            raw_text=raw_text,
            pages=pages_text,
            metadata=metadata,
            tables=all_tables
        )

    def extract_clinical_findings(self, pdf_result: PDFResult) -> dict:
        """Extract key clinical findings from MRI/radiology report text."""
        text = pdf_result.raw_text.lower()
        findings = {
            "acl_tear": False,
            "meniscus_tear": False,
            "meniscus_type": None,
            "pcl_intact": False,
            "bone_marrow_edema": False,
            "joint_effusion": False,
            "raw_findings": "",
            "raw_impression": ""
        }

        # Check for ACL tear
        acl_keywords = ["anterior cruciate ligament", "acl", "acl tear", "acl rupture"]
        tear_keywords = ["tear", "rupture", "disruption", "discontinuity", "torn"]
        for kw in acl_keywords:
            if kw in text:
                for tk in tear_keywords:
                    if tk in text:
                        findings["acl_tear"] = True
                        break

        # Check for meniscus tear
        if "meniscus" in text or "meniscal" in text:
            for tk in tear_keywords:
                if tk in text:
                    findings["meniscus_tear"] = True
                    if "medial" in text:
                        findings["meniscus_type"] = "medial"
                    elif "lateral" in text:
                        findings["meniscus_type"] = "lateral"
                    break

        # Check PCL
        if "posterior cruciate" in text and "intact" in text:
            findings["pcl_intact"] = True

        # Bone marrow edema
        if "bone marrow edema" in text or "bone marrow contusion" in text:
            findings["bone_marrow_edema"] = True

        # Joint effusion
        if "effusion" in text:
            findings["joint_effusion"] = True

        # Extract FINDINGS section
        raw = pdf_result.raw_text
        if "FINDINGS" in raw:
            start = raw.index("FINDINGS")
            end = raw.index("IMPRESSION") if "IMPRESSION" in raw else len(raw)
            findings["raw_findings"] = raw[start:end].strip()

        if "IMPRESSION" in raw:
            start = raw.index("IMPRESSION")
            findings["raw_impression"] = raw[start:].strip()

        return findings
