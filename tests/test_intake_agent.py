"""Tests for the Intake Agent and parsers."""
import pytest
from parsers.medical_code_mapper import MedicalCodeMapper, VALID_CPT_CODES, VALID_ICD10_CODES
from parsers.text_parser import TextParser


class TestMedicalCodeMapper:
    """Tests for medical code mapping from clinical descriptions."""

    def setup_method(self):
        self.mapper = MedicalCodeMapper()

    def test_map_pt_evaluation_to_cpt(self):
        """Physical Therapy Evaluation should map to CPT 97161."""
        codes = self.mapper.map_description_to_cpt(
            "Physical Therapy Evaluation - Initial Assessment"
        )
        code_ids = [c.code for c in codes]
        assert "97161" in code_ids

    def test_map_therapeutic_exercise_to_cpt(self):
        """Therapeutic Exercise should map to CPT 97110."""
        codes = self.mapper.map_description_to_cpt(
            "Therapeutic Exercise sessions for strength and flexibility"
        )
        code_ids = [c.code for c in codes]
        assert "97110" in code_ids

    def test_map_acl_reconstruction_to_cpt(self):
        """ACL Reconstruction should map to CPT 29888."""
        codes = self.mapper.map_description_to_cpt(
            "Arthroscopically Aided ACL Reconstruction"
        )
        code_ids = [c.code for c in codes]
        assert "29888" in code_ids

    def test_map_meniscectomy_to_cpt(self):
        """Meniscectomy should map to CPT 29881."""
        codes = self.mapper.map_description_to_cpt(
            "Arthroscopy knee surgical with meniscectomy"
        )
        code_ids = [c.code for c in codes]
        assert "29881" in code_ids

    def test_map_acl_tear_to_icd10(self):
        """ACL tear findings should map to ICD-10 S83.511A."""
        codes = self.mapper.map_findings_to_icd10(
            "Complete tear of the anterior cruciate ligament"
        )
        code_ids = [c.code for c in codes]
        assert "S83.511A" in code_ids

    def test_map_meniscus_tear_to_icd10(self):
        """Medial meniscus tear should map to ICD-10 S83.211A."""
        codes = self.mapper.map_findings_to_icd10(
            "Complex medial meniscus tear involving the posterior horn"
        )
        code_ids = [c.code for c in codes]
        assert "S83.211A" in code_ids

    def test_map_back_pain_to_icd10(self):
        """Chronic back pain should map to ICD-10 M54.50 (not deprecated M54.5)."""
        codes = self.mapper.map_findings_to_icd10(
            "Chronic lower back pain - ongoing treatment"
        )
        code_ids = [c.code for c in codes]
        assert "M54.50" in code_ids
        assert "M54.5" not in code_ids  # Ensure deprecated code is NOT used

    def test_extract_cpt_from_text(self):
        """Should extract CPT codes directly mentioned in text."""
        codes = self.mapper.extract_cpt_from_text(
            "CPT 29888 - ACL Reconstruction ₹3,50,000\n"
            "CPT 29881 - Meniscectomy ₹1,00,000"
        )
        code_ids = [c.code for c in codes]
        assert "29888" in code_ids
        assert "29881" in code_ids

    def test_validate_known_code(self):
        assert self.mapper.validate_code("29888") is True
        assert self.mapper.validate_code("S83.511A") is True

    def test_validate_unknown_code(self):
        assert self.mapper.validate_code("99999") is False


class TestTextParser:
    """Tests for user query intent extraction."""

    def setup_method(self):
        self.parser = TextParser()
        self.sample_query = (
            "Hi DuCO-Agent, I need to get my knee operated on soon, "
            "and Priya has some physical therapy bills lying around. "
            "We have Insurer1 (Plan A) and Insurer2 (Plan B). "
            "Can you help us figure out which plan pays first for my surgery and her bills? "
            "How much will we actually have to pay out of our own pocket? "
            "Also, we need the pre-auth letters generated for both insurers "
            "so we don't end up with a claim rejection. Please help!"
        )

    def test_extracts_patients(self):
        result = self.parser.parse_query(self.sample_query)
        assert "Priya Sen" in result.patients_mentioned

    def test_extracts_plans(self):
        result = self.parser.parse_query(self.sample_query)
        assert len(result.plans_mentioned) >= 2

    def test_extracts_claims(self):
        result = self.parser.parse_query(self.sample_query)
        claims = result.claims_identified
        assert any("Surgery" in c for c in claims)
        assert any("Therapy" in c or "PT" in c for c in claims)

    def test_extracts_actions(self):
        result = self.parser.parse_query(self.sample_query)
        actions = result.actions_requested
        assert "determine_primary_secondary" in actions
        assert "calculate_oop" in actions
        assert "generate_preauth" in actions
