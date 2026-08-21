from io import BytesIO
import unittest

from pypdf import PdfReader

from PWR110Calculator import create_pdf
from corrosion_defects import (
    ACTUAL_DEFECT_LENGTH,
    ENTER_MANUALLY,
    INDEPENDENT_DEFECTS,
    IndividualCorrosionDefect,
)
from prowrap_calculations import (
    apply_type_a_class3_result_to_repair,
    calculate_repair,
    calculate_type_a_class3_prowrap_check,
    substrate_credit_bar_for_iso_check,
)
from strain_limits import LCL_STRAIN_LIMIT, STANDARD_STRAIN_LIMIT
from test_current_calculation_baseline import default_inputs


class ReportWordingTest(unittest.TestCase):
    @staticmethod
    def _pdf_text(pdf_bytes):
        return "\n".join(
            page.extract_text() or ""
            for page in PdfReader(BytesIO(pdf_bytes)).pages
        )

    @staticmethod
    def _dent_report_pages(mechanism):
        report_data = calculate_repair(**default_inputs(
            defect_type=mechanism,
            rem_wall=9.53,
        ))

        pdf_bytes = create_pdf(report_data)

        assert pdf_bytes.startswith(b"%PDF")
        reader = PdfReader(BytesIO(pdf_bytes))
        return [page.extract_text() or "" for page in reader.pages]

    @classmethod
    def _dent_report_text(cls, mechanism):
        return "\n".join(cls._dent_report_pages(mechanism))

    def test_dent_pdf_keeps_installation_checklist_together(self):
        for mechanism in ("Dent w/crack", "Dent no-crack"):
            with self.subTest(mechanism=mechanism):
                pages = self._dent_report_pages(mechanism)
                self.assertTrue(any(
                    "5. Installation Checklist (Method Statement)" in page
                    and "5. Quality Control:" in page
                    for page in pages
                ))

    def test_standard_pdf_traces_the_standard_route_without_lcl_claims(self):
        report = calculate_repair(
            **default_inputs(strain_limit_basis=STANDARD_STRAIN_LIMIT),
        )

        text = self._pdf_text(create_pdf(report))

        for expected in (
            "Strain Limit Basis: Standard (0.0025)",
            "Base Strain (epsilon_c0): 0.250%",
            "Final Design Strain (epsilon_c):",
            "Circumferential Strain Route: standard_formula_10",
            "Formula 10 standard route",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)
        self.assertNotIn("Formula 11 performance route", text)
        self.assertNotIn("0.55%", text)

    def test_lcl_pdf_identifies_formula_11_and_the_selected_base_strain(self):
        report = calculate_repair(
            **default_inputs(strain_limit_basis=LCL_STRAIN_LIMIT),
        )

        text = self._pdf_text(create_pdf(report))

        for expected in (
            "Strain Limit Basis: LCL (0.0055)",
            "Base Strain (epsilon_c0): 0.550%",
            "Final Design Strain (epsilon_c):",
            "Circumferential Strain Route: lcl_formula_11_performance",
            "Formula 11 performance route",
            "0.55%",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)

    def test_pdf_reports_each_band_width_without_a_singular_installation_claim(self):
        report = calculate_repair(
            **default_inputs(length=348.246, cloth_widths_mm=(500, 300)),
        )

        text = self._pdf_text(create_pdf(report))

        self.assertIn("Continuous Repair Length (ISO): 637 mm", text)
        self.assertIn("500 mm Bands: 1", text)
        self.assertIn("300 mm Bands: 1", text)
        self.assertIn("Total Axial Bands: 2", text)
        self.assertIn("Effective Covered Length: 750 mm", text)
        self.assertIn("Procurement Axial Length: 800 mm", text)
        self.assertIn("Fabric Needed: 3.45 sqm", text)
        self.assertIn("Epoxy Required: 4.1 kg", text)
        self.assertIn(
            "4. Wrapping: Install 1 x 500 mm and 1 x 300 mm axial "
            "band(s), 2 total. Maintain the fixed 50 mm inter-band stitch "
            "overlap.",
            " ".join(text.split()),
        )
        self.assertNotIn("band(s) of", text)

    def test_pdf_reports_effective_coverage_for_each_available_width_plan(self):
        cases = (
            ((500, 300), 1, 1, 750, 800),
            ((300, 300), 0, 3, 800, 900),
            ((500, 500), 2, 0, 950, 1000),
        )

        for widths, count_500, count_300, covered, procurement in cases:
            with self.subTest(widths=widths):
                report = calculate_repair(
                    **default_inputs(length=348.246, cloth_widths_mm=widths),
                )
                text = self._pdf_text(create_pdf(report))

                self.assertIn(f"500 mm Bands: {count_500}", text)
                self.assertIn(f"300 mm Bands: {count_300}", text)
                self.assertIn(f"Effective Covered Length: {covered} mm", text)
                self.assertIn(f"Procurement Axial Length: {procurement} mm", text)

    def test_pdf_reports_effective_coverage_when_typea_class3_controls(self):
        repair = calculate_repair(
            **default_inputs(
                defect_type="Dent w/crack",
                length=140.0,
                rem_wall=9.53,
                cloth_widths_mm=(500.0, 300.0),
            ),
        )
        class3 = calculate_type_a_class3_prowrap_check(
            od=repair["od"],
            pressure_bar=repair["pressure"],
            temp=repair["temp"],
            rem_wall=repair["rem_wall_eol"],
            design_life=repair["design_life"],
            substrate_allowable_pressure_bar=substrate_credit_bar_for_iso_check(repair),
            nominal_wall_mm=repair["wall"],
        )
        report = apply_type_a_class3_result_to_repair(
            repair, class3, cloth_widths_mm=(500.0, 300.0),
        )

        self.assertTrue(report["iso_typea_class3_controls"])
        text = self._pdf_text(create_pdf(report))

        self.assertIn("Effective Covered Length: 750 mm", text)
        self.assertIn("Procurement Axial Length: 800 mm", text)

    def test_dent_with_crack_pdf_reports_full_pressure_laminate_basis(self):
        text = self._dent_report_text("Dent w/crack")

        self.assertIn("Dent w/crack - full-pressure laminate", text)
        self.assertIn("Substrate Allowable Pressure p_s: 0.00 MPa (0.00 bar)", text)
        self.assertIn("Composite Pressure Deficit: 5.00 MPa", text)
        self.assertNotIn("B31G", text)
        self.assertIn(
            "Preliminary basis: selected ISO 24817 / ASME PCC-2 concepts",
            text,
        )

    def test_dent_no_crack_pdf_reports_substrate_load_sharing_basis(self):
        text = self._dent_report_text("Dent no-crack")

        self.assertIn("Dent no-crack - substrate load sharing", text)
        self.assertIn("Allowable Pipe Stress S_allow: 258.48 MPa", text)
        self.assertIn("Substrate Allowable Pressure p_s: 10.78 MPa (107.76 bar)", text)
        self.assertIn("Composite Pressure Deficit: 0.00 MPa", text)
        self.assertNotIn("B31G", text)
        self.assertIn(
            "Preliminary basis: selected ISO 24817 / ASME PCC-2 concepts",
            text,
        )

    def test_internal_dent_no_crack_pdf_reports_type_b_basis(self):
        report_data = calculate_repair(**default_inputs(
            defect_type="Dent no-crack",
            defect_loc="Internal",
            rem_wall=9.53,
        ))

        pdf_bytes = create_pdf(report_data)

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        text = "\n".join(
            page.extract_text() or ""
            for page in PdfReader(BytesIO(pdf_bytes)).pages
        )
        self.assertIn("Repair Logic: Type B (Total Replacement)", text)
        self.assertIn("Calculation Basis: Type B full replacement", text)
        self.assertNotIn("substrate load sharing", text)

    def test_independent_pdf_records_assumptions_and_two_lengths(self):
        report = calculate_repair(
            **default_inputs(length=1000.0, rem_wall=9.0),
            defect_length_basis=INDEPENDENT_DEFECTS,
        )

        text = self._pdf_text(create_pdf(report))

        self.assertIn("PROWRAP COMPOSITE REPAIR REPORT - v1.4", text)
        self.assertIn("Defect Length Basis: Independent defects", text)
        self.assertIn("Overall Repair-Zone Span: 1000.0 mm", text)
        self.assertIn("B31G Assessment Length: 10.0 mm", text)
        self.assertIn("10 mm longitudinal by 10 mm circumferential", text)
        self.assertIn(
            "Calculation Basis: ASME B31G-2023 Level 1 (Modified)", text,
        )
        self.assertIn(
            "Substrate MAWP (p_s) per ASME B31G-2023 Level 1 (Modified)",
            text,
        )

    def test_high_smys_pdf_reports_original_method_and_fallback_warning(self):
        report = calculate_repair(
            **default_inputs(yield_strength=555.0),
            defect_length_basis=ACTUAL_DEFECT_LENGTH,
        )

        text = self._pdf_text(create_pdf(report))

        self.assertIn(
            "Calculation Basis: ASME B31G-2023 Level 1 (Original)", text,
        )
        self.assertIn(
            "Substrate MAWP (p_s) per ASME B31G-2023 Level 1 (Original)",
            text,
        )
        self.assertIn(
            "falling back to Original B31G",
            " ".join(text.split()),
        )

    def test_manual_pdf_lists_candidates_and_governing_defect(self):
        report = calculate_repair(
            **default_inputs(length=500.0, rem_wall=6.0, wall=12.0),
            defect_length_basis=ENTER_MANUALLY,
            individual_defects=(
                IndividualCorrosionDefect("D-01", 80.0, 10.5, True),
                IndividualCorrosionDefect("D-02", 12.0, 6.0, True),
            ),
        )

        text = self._pdf_text(create_pdf(report))

        self.assertIn("Defect Length Basis: Enter manually", text)
        self.assertIn(f"Governing Defect: {report['governing_defect_id']}", text)
        table = text.split("Individual B31G candidate assessments", 1)[1]
        table = table.split("3. Optimized Repair Design", 1)[0]
        for heading in (
            "Defect ID",
            "Length [mm]",
            "Wall [mm]",
            "Method",
            "Applicable",
            "Credit [MPa]",
            "Governing",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, table)
        for value in (
            "D-01",
            "80.0",
            "10.500",
            "D-02",
            "12.0",
            "6.000",
            "Modified",
        ):
            with self.subTest(value=value):
                self.assertIn(value, table)

    def test_manual_pdf_table_repeats_headers_and_preserves_following_section(self):
        defects = tuple(
            IndividualCorrosionDefect(
                f"D-{index:02d}",
                10.0 + index,
                6.0 + (index % 5) * 0.5,
                True,
            )
            for index in range(1, 29)
        )
        report = calculate_repair(
            **default_inputs(length=500.0, rem_wall=6.0, wall=12.0),
            defect_length_basis=ENTER_MANUALLY,
            individual_defects=defects,
        )

        reader = PdfReader(BytesIO(create_pdf(report)))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages)

        for index in range(1, 29):
            self.assertIn(f"D-{index:02d}", text)
        table_header_pages = [
            page for page in pages
            if "Applicable" in page and "Credit [MPa]" in page
        ]
        self.assertGreaterEqual(len(table_header_pages), 2)
        self.assertTrue(any(
            "5. Installation Checklist (Method Statement)" in page
            and "5. Quality Control:" in page
            for page in pages
        ))

    def test_all_external_corrosion_pdf_routes_include_traceability_fields(self):
        base = default_inputs(
            od=1016.0,
            wall=12.0,
            pressure=104.9,
            length=1000.0,
            rem_wall=9.652,
            yield_strength=450.0,
            cloth_width_mm=500.0,
        )
        routes = {
            "actual": (ACTUAL_DEFECT_LENGTH, ()),
            "independent": (INDEPENDENT_DEFECTS, ()),
            "manual": (
                ENTER_MANUALLY,
                (
                    IndividualCorrosionDefect("D-01", 10.0, 9.652, True),
                    IndividualCorrosionDefect("D-02", 35.0, 10.0, True),
                ),
            ),
        }
        common = (
            "PROWRAP COMPOSITE REPAIR REPORT - v1.4",
            "Overall Repair-Zone Span: 1000.0 mm",
            "3t Interaction Threshold: 36.0 mm",
            "B31G Candidates Assessed:",
            "Governing Defect:",
            "B31G Assessment Length:",
            "B31G Assessment Remaining Wall:",
            "Governing Credited Pressure:",
            "Continuous Repair Length (ISO):",
            "Required Plies:",
            "Calculation Basis: ASME B31G-2023 Level 1 (Modified)",
        )
        route_fields = {
            "actual": (
                "Defect Length Basis: Actual defect length",
                "B31G Candidates Assessed: 1",
                "Governing Defect: Actual/combined defect",
                "B31G Assessment Length: 1000.0 mm",
                "B31G Assessment Remaining Wall: 9.652 mm",
                "continuous or interacting corrosion feature",
            ),
            "independent": (
                "Defect Length Basis: Independent defects",
                "B31G Candidates Assessed: 1",
                "Governing Defect: Independent 10x10 mm defects",
                "B31G Assessment Length: 10.0 mm",
                "10 mm longitudinal by 10 mm circumferential",
                "more than 36 mm (3t)",
                "uses the entered remaining wall",
            ),
            "manual": (
                "Defect Length Basis: Enter manually",
                "B31G Candidates Assessed: 2",
                "Governing Defect: D-02",
                "B31G Assessment Length: 35.0 mm",
                "B31G Assessment Remaining Wall: 10.000 mm",
                "more than 36 mm (3t)",
                "Individual B31G candidate assessments",
                "D-01",
                "D-02",
            ),
        }

        for route, (basis, defects) in routes.items():
            with self.subTest(route=route):
                report = calculate_repair(
                    **base,
                    defect_length_basis=basis,
                    individual_defects=defects,
                )
                reader = PdfReader(BytesIO(create_pdf(report)))
                text = "\n".join(
                    page.extract_text() or "" for page in reader.pages
                )
                self.assertEqual(len(reader.pages), 2)
                for field in (*common, *route_fields[route]):
                    self.assertIn(field, text)


if __name__ == "__main__":
    unittest.main()
