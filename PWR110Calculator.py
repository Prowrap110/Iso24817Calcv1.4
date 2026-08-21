import streamlit as st
import pandas as pd
from fpdf import FPDF

from app_identity import APP_NAME, APP_VERSION
from corrosion_defects import (
    ACTUAL_DEFECT_LENGTH,
    DEFECT_LENGTH_BASES,
    ENTER_MANUALLY,
    INDEPENDENT_DEFECTS,
)
from prowrap_calculations import (
    apply_type_a_class3_result_to_repair,
    calculate_repair,
    calculate_type_a_class3_prowrap_check,
    substrate_credit_bar_for_iso_check,
)
from prowrap_materials import PROWRAP
from prowrap_mechanisms import MECHANISM_CHOICES
from strain_limits import LCL_STRAIN_LIMIT, STRAIN_LIMIT_CHOICES
from calculator_form import (
    NEUTRAL_CHOICE,
    calculation_corrosion_rate,
    initialise_inputs,
    manual_defects_from_state,
    missing_required_fields,
    new_calculation,
)

MANUAL_DEFECT_COLUMNS = (
    "Defect ID",
    "Individual longitudinal length [mm]",
    "Remaining wall [mm]",
    "Separation exceeds 3t",
)

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🔧",
    layout="wide"
)

def safe_text(text):
    """Safely replaces Turkish/Special characters to prevent PDF encoding crashes."""
    if not isinstance(text, str):
        return str(text)
    replacements = {
        'ı': 'i', 'İ': 'I', 'ş': 's', 'Ş': 'S', 
        'ğ': 'g', 'Ğ': 'G', 'ü': 'u', 'Ü': 'U', 
        'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
    }
    for tr, eng in replacements.items():
        text = text.replace(tr, eng)
    return text

def create_pdf(report_data):
    """Generates a PDF report and returns it as bytes."""
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(
        0, 10, txt=f"PROWRAP COMPOSITE REPAIR REPORT - v{APP_VERSION}",
        ln=True, align='C',
    )
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 8, txt="Preliminary basis: selected ISO 24817 / ASME PCC-2 concepts", ln=True, align='C')
    pdf.ln(5)

    def add_section(title, data_dict):
        ensure_page_space(8 + len(data_dict) * 6 + 5)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 8, txt=title, ln=True, fill=True)
        pdf.set_font("Arial", '', 11)
        for key, val in data_dict.items():
            pdf.cell(90, 6, txt=safe_text(f"{key}:"), border=0)
            pdf.cell(0, 6, txt=safe_text(str(val)), ln=True, border=0)
        pdf.ln(5)

    def ensure_page_space(required_height):
        if pdf.get_y() + required_height > pdf.h - pdf.b_margin:
            pdf.add_page()

    def add_manual_b31g_table(candidate_assessments, governing_id):
        columns = (
            ("Defect ID", 38, "L"),
            ("Length [mm]", 25, "R"),
            ("Wall [mm]", 24, "R"),
            ("Method", 24, "C"),
            ("Applicable", 24, "C"),
            ("Credit [MPa]", 28, "R"),
            ("Governing", 25, "C"),
        )
        row_height = 5.5
        title_height = 6

        def fit_cell_text(value, width):
            text = safe_text(str(value))
            if pdf.get_string_width(text) <= width - 2:
                return text
            suffix = "..."
            while text and pdf.get_string_width(text + suffix) > width - 2:
                text = text[:-1]
            return text + suffix

        def draw_title(continued=False):
            pdf.set_font("Arial", 'B', 10)
            suffix = " (continued)" if continued else ""
            pdf.cell(
                0,
                title_height,
                txt=f"Individual B31G candidate assessments{suffix}",
                ln=True,
            )

        def draw_header():
            pdf.set_font("Arial", 'B', 7)
            pdf.set_fill_color(225, 235, 248)
            for heading, width, alignment in columns:
                pdf.cell(
                    width,
                    row_height,
                    txt=heading,
                    border=1,
                    align=alignment,
                    fill=True,
                )
            pdf.ln(row_height)

        ensure_page_space(title_height + 2 * row_height + 2)
        draw_title()
        draw_header()
        for item in candidate_assessments:
            if pdf.get_y() + row_height > pdf.h - pdf.b_margin:
                pdf.add_page()
                draw_title(continued=True)
                draw_header()
            assessment = item["assessment"]
            values = (
                item["defect_id"],
                f"{item['length_mm']:.1f}",
                f"{item['remaining_wall_mm']:.3f}",
                assessment["method"].title(),
                "Yes" if assessment["applicable"] else "No",
                f"{item['credited_pressure_mpa']:.2f}",
                "Yes" if item["defect_id"] == governing_id else "No",
            )
            pdf.set_font("Arial", '', 7)
            for value, (_heading, width, alignment) in zip(values, columns):
                pdf.cell(
                    width,
                    row_height,
                    txt=fit_cell_text(value, width),
                    border=1,
                    align=alignment,
                )
            pdf.ln(row_height)
        pdf.ln(3)

    add_section("1. Project & Pipeline Data", {
        "Customer": report_data['customer'],
        "Location": report_data['location'],
        "Report No": report_data['report_no'],
        "Pipe Outer Diameter": f"{report_data['od']} mm",
        "Nominal Wall Thickness": f"{report_data['wall']} mm",
        "Pipe Yield Strength": f"{report_data['yield_str']} MPa",
        "Design Pressure": f"{report_data['pressure']} bar",
        "Operating Temperature": f"{report_data['temp']} C"
    })

    defect_assessment = {
        "Defect Mechanism": report_data['defect_type'],
        "Defect Location": report_data['defect_loc'],
        "Remaining Wall": f"{report_data['rem_wall']} mm",
        "Remaining Wall @ End of Life": f"{report_data['rem_wall_eol']:.2f} mm"
        + (f" (internal corrosion {report_data['internal_corrosion_rate']:.2f} mm/yr)"
           if report_data['internal_corrosion_rate'] > 0 else ""),
        "Axial Length": f"{report_data['length']} mm",
        "Wall Loss": f"{report_data['wall_loss_ratio']*100:.1f} %",
        "Repair Logic": report_data['calc_method_thick'],
        "Calculation Basis": report_data['calculation_basis'],
    }
    allowable_pipe_stress = report_data.get("allowable_pipe_stress_mpa")
    if allowable_pipe_stress is not None:
        defect_assessment["Allowable Pipe Stress S_allow"] = (
            f"{allowable_pipe_stress:.2f} MPa"
        )
    substrate_pressure = report_data["p_steel_capacity"]
    defect_assessment["Substrate Allowable Pressure p_s"] = (
        f"{substrate_pressure:.2f} MPa ({substrate_pressure * 10.0:.2f} bar)"
    )
    defect_assessment["Composite Pressure Deficit"] = (
        f"{report_data['p_composite_design']:.2f} MPa"
    )
    is_external_corrosion = (
        report_data["defect_type"] == "Corrosion"
        and report_data["defect_loc"] == "External"
    )
    if is_external_corrosion:
        defect_assessment.update({
            "Defect Length Basis": report_data["defect_length_basis"],
            "Overall Repair-Zone Span": (
                f"{report_data['repair_zone_length_mm']:.1f} mm"
            ),
            "3t Interaction Threshold": (
                f"{report_data['interaction_distance_mm']:.1f} mm"
            ),
            "B31G Candidates Assessed": str(
                len(report_data["b31g_assessments"])
            ),
            "Governing Defect": report_data["governing_defect_id"],
            "B31G Assessment Length": (
                f"{report_data['governing_b31g_length_mm']:.1f} mm"
            ),
            "B31G Assessment Remaining Wall": (
                f"{report_data['governing_b31g_remaining_wall_mm']:.3f} mm"
            ),
            "Governing Credited Pressure": (
                f"{report_data['p_steel_capacity']:.2f} MPa"
            ),
        })
    add_section("2. Defect Assessment", defect_assessment)

    if is_external_corrosion:
        assumptions = report_data["defect_basis_assumptions"]
        candidate_assessments = report_data["b31g_assessments"]
        ensure_page_space(8 + len(assumptions) * 5 + 5)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, txt="Defect-basis assumptions", ln=True)
        pdf.set_font("Arial", '', 9)
        for assumption in assumptions:
            pdf.multi_cell(0, 5, txt=safe_text(f"- {assumption}"))
        if report_data["defect_length_basis"] == ENTER_MANUALLY:
            add_manual_b31g_table(
                candidate_assessments,
                report_data["governing_defect_id"],
            )
        else:
            pdf.ln(3)

    add_section("3. Optimized Repair Design", {
        "Required Plies": f"{report_data['num_plies']} Layers",
        "Repair Thickness": f"{report_data['final_thickness']:.2f} mm",
        "Continuous Repair Length (ISO)": (
            f"{report_data['iso_length']:.0f} mm"
        ),
        "500 mm Bands": str(report_data['num_bands_500']),
        "300 mm Bands": str(report_data['num_bands_300']),
        "Total Axial Bands": str(report_data['num_bands']),
        "Effective Covered Length": f"{report_data['covered_length_mm']:g} mm",
        "Procurement Axial Length": f"{report_data['proc_length']:g} mm",
        "Design Factor": f"{report_data['design_factor']}",
        "Strain Limit Basis": report_data["strain_limit_basis"],
        "Base Strain (epsilon_c0)": (
            f"{report_data['strain_limit_base'] * 100:.3f}%"
        ),
        "Final Design Strain (epsilon_c)": (
            f"{report_data['design_strain'] * 100:.3f}%"
        ),
        "Circumferential Strain Route": (
            report_data["circumferential_strain_route"]
        ),
    })
    
    # Add the basis note to the PDF directly under the design section.
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(100, 100, 100) # Dark grey for note
    if report_data["strain_limit_basis"] == LCL_STRAIN_LIMIT:
        standards_note = (
            "* Thickness per ISO 24817 Formula 11 performance route "
            f"(base epsilon_c0 = 0.55%, Class 3, {report_data['design_life']} "
            "yr design life); axial extent per Formulae 18/20/21; minimum "
            "thickness per 7.5.14. "
        )
    else:
        standards_note = (
            "* Thickness per ISO 24817 Formula 10 standard route "
            "(base epsilon_c0 = 0.25%); axial extent per Formulae 18/20/21; "
            "minimum thickness per 7.5.14. "
        )
    if report_data.get("b31g_details"):
        b31g = report_data["b31g_details"]
        method_label = b31g["method"].title()
        applicability_note = (
            " at current remaining wall. "
            if b31g["applicable"]
            else "; the governing assessment is outside applicability and "
            "no substrate pressure credit is taken. "
        )
        standards_note += (
            "Substrate MAWP (p_s) per ASME B31G-2023 Level 1 "
            f"({method_label}){applicability_note}"
        )
    elif allowable_pipe_stress is not None:
        standards_note += (
            "Dent substrate pressure uses the component-pipe allowable "
            "stress basis; the laminate carries the pressure deficit. "
        )
    else:
        standards_note += (
            "No substrate pressure credit is taken; the full design pressure "
            "is assigned to the laminate. "
        )
    standards_note += "Verify against licensed copies of applicable standards before use."
    pdf.multi_cell(0, 5, txt=safe_text(standards_note))
    pdf.set_text_color(0, 0, 0) # Reset to black
    pdf.ln(2)
    for warning_text in report_data.get("compliance_warnings", []):
        pdf.set_font("Arial", 'B', 9)
        pdf.set_text_color(200, 0, 0)
        pdf.multi_cell(0, 5, txt=safe_text(f"WARNING: {warning_text}"))
        pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    add_section("4. Material Procurement", {
        "Fabric Needed": f"{report_data['optimized_sqm']:.2f} sqm",
        "Epoxy Required": f"{report_data['epoxy_kg']:.1f} kg"
    })

    steps = [
        "1. Surface Prep: Grit blast to SA 2.5; Profile >60 microns.",
        "2. Primer/Filler: Apply Prowrap Filler to defect area to restore OD.",
        f"3. Lamination: Saturate Carbon Cloth. Apply {report_data['num_plies']} layers per band.",
        "4. Wrapping: Install "
        f"{report_data['num_bands_500']} x 500 mm and "
        f"{report_data['num_bands_300']} x 300 mm axial band(s), "
        f"{report_data['num_bands']} total. Maintain the fixed 50 mm "
        "inter-band stitch overlap.",
        f"5. Quality Control: Minimum average Shore D hardness of {PROWRAP['shore_d_min']} required."
    ]

    # --- METHOD STATEMENT SECTION IN PDF ---
    checklist_height = 8 + len(steps) * 6 + (8 if report_data['num_plies'] == 2 else 0)
    if pdf.get_y() + checklist_height > pdf.h - pdf.b_margin:
        pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(0, 8, txt="5. Installation Checklist (Method Statement)", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    
    for step in steps:
        pdf.multi_cell(0, 6, txt=safe_text(step))
        
    if report_data['num_plies'] == 2:
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(200, 0, 0)
        pdf.multi_cell(0, 6, txt="NOTE: Protap recommends min. 3 layer repair if the repair is subject to harsh and corrosive environment in line with ISO 24817.")
        pdf.set_text_color(0, 0, 0)

    # Safe PDF output across different fpdf versions
    output = pdf.output(dest='S')
    if isinstance(output, str):
        return output.encode('latin-1', 'replace')
    return bytes(output)

def run_calculation(
    customer,
    location,
    report_no,
    od,
    wall,
    pressure,
    temp,
    defect_type,
    defect_loc,
    length,
    rem_wall,
    yield_strength,
    design_factor,
    design_life,
    show_typea_class3_check=False,
    installation_temp=20.0,
    component_type="Straight",
    cyclic_derating_factor=1.0,
    internal_corrosion_rate=0.0,
    axial_load_case=0,
    cloth_width_1_mm=300,
    cloth_width_2_mm=300,
    defect_length_basis=ACTUAL_DEFECT_LENGTH,
    individual_defects=(),
    strain_limit_basis=NEUTRAL_CHOICE,
):
    try:
        cloth_widths_mm = (cloth_width_1_mm, cloth_width_2_mm)
        report_data = calculate_repair(
            customer,
            location,
            report_no,
            od,
            wall,
            pressure,
            temp,
            defect_type,
            defect_loc,
            length,
            rem_wall,
            yield_strength,
            design_factor,
            design_life,
            force_3_layers=st.session_state.force_3_layers,
            internal_corrosion_rate=internal_corrosion_rate,
            installation_temp=installation_temp,
            component_type=component_type,
            cyclic_derating_factor=cyclic_derating_factor,
            axial_load_case=axial_load_case,
            cloth_widths_mm=cloth_widths_mm,
            defect_length_basis=defect_length_basis,
            individual_defects=individual_defects,
            strain_limit_basis=strain_limit_basis,
        )
    except ValueError as exc:
        st.session_state.calc_active = False
        for err in str(exc).splitlines():
            st.error(f"❌ **INPUT ERROR:** {err}")
        return

    defect_type = report_data["defect_type"]
    calculation_basis = report_data["calculation_basis"]

    wall_loss_ratio = report_data["wall_loss_ratio"]
    num_plies = report_data["num_plies"]
    final_thickness = report_data["final_thickness"]
    total_repair_length_calc = report_data["iso_length"]
    effective_covered_length = report_data["covered_length_mm"]
    procurement_axial_length = report_data["proc_length"]
    optimized_sqm = report_data["optimized_sqm"]
    epoxy_kg = report_data["epoxy_kg"]
    is_upgraded = report_data["is_upgraded"]
    p_steel_capacity = report_data["p_steel_capacity"]
    p_composite_design = report_data["p_composite_design"]
    design_strain = report_data["design_strain"]
    num_bands = report_data["num_bands"]
    substrate_allowable_pressure = substrate_credit_bar_for_iso_check(report_data)
    typea_class3_result = None
    typea_class3_note = None

    if show_typea_class3_check:
        if defect_type not in ["Crack", "Leak"] and "Type A" in report_data["calc_method_thick"]:
            try:
                typea_class3_result = calculate_type_a_class3_prowrap_check(
                    od=od,
                    pressure_bar=pressure,
                    temp=temp,
                    rem_wall=report_data["rem_wall_eol"],
                    design_life=design_life,
                    nominal_wall_mm=wall,
                    substrate_allowable_pressure_bar=substrate_allowable_pressure,
                    installation_temp=installation_temp,
                    component_type=component_type,
                    cyclic_derating_factor=cyclic_derating_factor,
                    axial_load_case=axial_load_case,
                    strain_limit_basis=strain_limit_basis,
                )
            except ValueError as exc:
                typea_class3_note = str(exc)
        else:
            typea_class3_note = (
                "Type A / Class 3 check requires a Type A (non-crack/non-leak, "
                "not through-wall within design life) defect."
            )

    if typea_class3_result:
        report_data = apply_type_a_class3_result_to_repair(
            report_data,
            typea_class3_result,
            cloth_widths_mm=cloth_widths_mm,
        )
        num_plies = report_data["num_plies"]
        final_thickness = report_data["final_thickness"]
        total_repair_length_calc = report_data["iso_length"]
        effective_covered_length = report_data["covered_length_mm"]
        procurement_axial_length = report_data["proc_length"]
        optimized_sqm = report_data["optimized_sqm"]
        epoxy_kg = report_data["epoxy_kg"]
        is_upgraded = report_data["is_upgraded"]
    num_bands_500 = report_data["num_bands_500"]
    num_bands_300 = report_data["num_bands_300"]
    num_bands = report_data["num_bands"]

    st.success(f"✅ Calculation Complete")

    for warning_text in report_data.get("compliance_warnings", []):
        st.error(f"⚠️ **ISO 24817 COMPLIANCE:** {warning_text}")

    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    m1.metric("Required Plies", f"{num_plies}", f"{final_thickness:.2f} mm")
    m2.metric("Req. Repair Length", f"{total_repair_length_calc:.0f} mm")
    m3.metric("Effective Covered Length", f"{effective_covered_length:g} mm")
    m4.metric("Procurement Axial Length", f"{procurement_axial_length:g} mm")
    m5.metric(
        "Band Plan",
        f"500: {num_bands_500} | 300: {num_bands_300}",
        f"{num_bands} total bands",
    )
    m6.metric("Optimized Fabric", f"{optimized_sqm:.2f} m²")
    m7.metric("Epoxy Needed", f"{epoxy_kg:.1f} kg")

    st.markdown("---")
    if num_plies == 2 and not is_upgraded:
        col_warn, col_btn = st.columns([3, 1])
        with col_warn:
            st.warning("⚠️ **PROTAP Recommendation:** Protap recommends min. 3 layer repair if the repair is subject to harsh and corrosive environment in line with ISO 24817.")
        with col_btn:
            if st.button("⬆️ Do you want 3 layers?", use_container_width=True):
                st.session_state.force_3_layers = True
                st.rerun() 
    elif is_upgraded:
        st.info("ℹ️ **Design Upgraded:** Minimum 3 layers applied based on PROTAP recommendation for harsh environments.")
    st.markdown("---")

    tab1, tab2 = st.tabs(["📊 Engineering Analysis", "📄 Method Statement"])
    
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Defect Analysis")
            st.write(f"**Mechanism:** {defect_type}")
            st.write(f"**Calculation Basis:** {calculation_basis}")
            st.write(f"**Wall Loss:** {wall_loss_ratio*100:.1f}%")
            if defect_type == "Corrosion" and defect_loc == "External":
                st.write(
                    "**Defect Length Basis:** "
                    f"{report_data['defect_length_basis']}"
                )
                st.write(
                    "**B31G Candidates Assessed:** "
                    f"{len(report_data['b31g_assessments'])}"
                )
                st.write(
                    "**Overall Repair-Zone Span:** "
                    f"{report_data['repair_zone_length_mm']:.1f} mm"
                )
                st.write(
                    "**3t Interaction Threshold:** "
                    f"{report_data['interaction_distance_mm']:.1f} mm"
                )
                st.write(
                    "**Governing Defect ID:** "
                    f"{report_data['governing_defect_id']}"
                )
                st.write(
                    "**B31G Assessment Length:** "
                    f"{report_data['governing_b31g_length_mm']:.1f} mm"
                )
                st.write(
                    "**B31G Assessment Remaining Wall:** "
                    f"{report_data['governing_b31g_remaining_wall_mm']:.3f} mm"
                )
                for assumption in report_data["defect_basis_assumptions"]:
                    st.info(assumption)
                if report_data["defect_length_basis"] == ENTER_MANUALLY:
                    assessment_rows = [
                        {
                            "Defect ID": item["defect_id"],
                            "B31G length [mm]": item["length_mm"],
                            "Remaining wall [mm]": item["remaining_wall_mm"],
                            "Credited pressure [MPa]": item[
                                "credited_pressure_mpa"
                            ],
                            "Governing": (
                                item["defect_id"]
                                == report_data["governing_defect_id"]
                            ),
                        }
                        for item in report_data["b31g_assessments"]
                    ]
                    st.dataframe(
                        assessment_rows,
                        hide_index=True,
                        width="stretch",
                    )
            b31g = report_data.get("b31g_details")
            if b31g:
                st.write(f"**Substrate MAWP p_s (ASME B31G {b31g['method'].title()}, SF={b31g['safety_factor']:.2f}):** {p_steel_capacity:.2f} MPa")
                st.write(f"**B31G:** d/t={b31g['d_over_t']:.3f}, z={b31g['z']:.2f}, M={b31g['folias_m']:.3f}, S_F={b31g['s_f_mpa']:.0f} MPa, P_F={b31g['p_f_mpa']:.2f} MPa")
                st.write(f"**B31G Acceptance (pipe alone):** {'ACCEPTABLE' if b31g.get('acceptable') else 'NOT ACCEPTABLE'} at design pressure")
            else:
                allowable_pipe_stress = report_data.get("allowable_pipe_stress_mpa")
                if allowable_pipe_stress is not None:
                    st.write(
                        "**Allowable Pipe Stress S_allow:** "
                        f"{allowable_pipe_stress:.2f} MPa"
                    )
                st.write(
                    "**Substrate Allowable Pressure p_s:** "
                    f"{p_steel_capacity:.2f} MPa "
                    f"({p_steel_capacity * 10.0:.2f} bar)"
                )
                if p_steel_capacity == 0:
                    st.write(
                        "**Load Assignment:** Full design pressure is assigned "
                        "to the laminate."
                    )
            st.write(
                f"**Composite Pressure Deficit:** {p_composite_design:.2f} MPa"
            )
        with c2:
            st.markdown("### Structural Design")
            st.write(f"**Composite Design Pressure:** {p_composite_design:.2f} MPa")
            st.write(
                "**Continuous Repair Length:** "
                f"{total_repair_length_calc:.1f} mm"
            )
            st.write(
                "**Strain Limit Basis:** "
                f"{report_data['strain_limit_basis']}"
            )
            st.write(
                "**Base Strain (epsilon_c0):** "
                f"{report_data['strain_limit_base'] * 100:.3f}%"
            )
            st.write(
                "**Final Design Strain (epsilon_c):** "
                f"{design_strain * 100:.3f}%"
            )
            st.write(
                "**Circumferential Strain Route:** "
                f"{report_data['circumferential_strain_route']}"
            )
            type_b_details = report_data.get("type_b_details")
            if type_b_details:
                st.markdown("### Type B Check (ISO Formula 12)")
                st.write(f"**Type B Service Life:** {type_b_details['design_life_years']:.0f} years (capped; revalidate thereafter)")
                st.write(f"**Type B Temp Limit:** {type_b_details['service_temp_limit_c']:.1f} °C")
                st.write(f"**gamma_LCL:** {type_b_details['gamma_lcl_j_m2']:.0f} J/m²")
                st.write(f"**Defect Size (end of life):** {type_b_details['defect_size_used_mm']:.0f} mm")
                st.write(f"**f_leak (Formula 16):** {type_b_details['fleak']:.3f}")
                st.write(f"**Max Achievable Pressure (asymptote):** {type_b_details['p_max_asymptote_mpa']:.2f} MPa")
                if type_b_details.get("repairable_formula12", True):
                    st.write(f"**Formula 12 Thickness:** {type_b_details['t_formula12_mm']:.2f} mm")
                else:
                    st.write("**Formula 12 Thickness:** NO SOLUTION - defect not repairable at this pressure")
                st.write(f"**Type A Thickness (7.5.7 max rule):** {type_b_details['t_typea_mm']:.2f} mm")
                st.write(f"**Validity d <= 6*sqrt(D*t):** {'OK' if type_b_details['d_within_validity'] else 'EXCEEDED'}")
            st.write(f"**Design Factor (f):** {design_factor}")

        if show_typea_class3_check:
            st.markdown("### ISO Type A / Class 3 Check")
            if typea_class3_result:
                if axial_load_case == 1:
                    st.write(
                        "**Axial Loads:** included per ISO 24817 Formula 4 "
                        f"(end-thrust F_eq = {typea_class3_result['feq_n']/1000:.0f} kN; "
                        "severed-pipe / above-ground case)"
                    )
                if typea_class3_result["strain_limit_basis"] == LCL_STRAIN_LIMIT:
                    st.write(
                        "**Basis:** PRW110 performance data "
                        "(ISO 24817 Formula 11, eps_lt = "
                        f"{PROWRAP['long_term_strain_lcl']*100:.2f}%)."
                    )
                else:
                    st.write(
                        "**Basis:** Standard Formula 10 route "
                        "(epsilon_c0 = 0.25%)."
                    )
                st.write(
                    f"**Substrate Credit:** {substrate_allowable_pressure:.1f} bar "
                    f"({substrate_allowable_pressure * 0.1:.2f} MPa effective pipe capacity)"
                )
                if not report_data.get("iso_typea_class3_controls", True):
                    st.write(
                        "**Structural Control:** Not controlling; effective pipe capacity "
                        "covers design pressure."
                    )
                    st.write(
                        f"**Non-controlling ISO Thickness:** "
                        f"{typea_class3_result['tdesign_final_mm']:.2f} mm"
                    )
                    st.write(
                        f"**Non-controlling ISO Layer Count:** "
                        f"{typea_class3_result['layer_count']}"
                    )
                else:
                    st.write("**Structural Control:** ISO Type A / Class 3 controls displayed plies.")
                    st.write(f"**Final Thickness:** {typea_class3_result['tdesign_final_mm']:.2f} mm")
                    st.write(f"**Layer Count:** {typea_class3_result['layer_count']}")
                st.write(f"**Required Overlap:** {typea_class3_result['lover_required_mm']:.1f} mm")
                st.write(f"**Component Factor:** {typea_class3_result['fth_stress']:.2f}")
                st.write(
                    f"**Thickness Check:** {'OK' if typea_class3_result['thickness_check_ok'] else 'NOT OK'}"
                )
            elif typea_class3_note:
                st.warning(typea_class3_note)

    with tab2:
        st.markdown("## 🛠️ Prowrap Repair Method Statement")
        st.markdown("---")
        
        c_pipe, c_defect, c_repair = st.columns(3)
        with c_pipe:
            st.info("**1. Pipeline Parameters**")
            st.markdown(f"""
            - **Diameter:** {od} mm
            - **Nominal Wall:** {wall} mm
            - **Grade:** {yield_strength} MPa
            - **Design Pressure:** {pressure} bar
            - **Op. Temp:** {temp} °C
            """)
        with c_defect:
            st.warning("**2. Defect Description**")
            if defect_type == "Corrosion" and defect_loc == "External":
                st.markdown(f"""
                - **Mechanism:** {defect_type} ({defect_loc})
                - **Minimum Remaining Wall:** {report_data['rem_wall']} mm
                - **Overall Repair-Zone Span:** {report_data['repair_zone_length_mm']} mm
                - **Governing Defect ID:** {report_data['governing_defect_id']}
                - **Wall Loss:** {wall_loss_ratio*100:.1f}%
                """)
            else:
                st.markdown(f"""
                - **Mechanism:** {defect_type} ({defect_loc})
                - **Remaining Wall:** {rem_wall} mm
                - **Axial Length:** {length} mm
                - **Wall Loss:** {wall_loss_ratio*100:.1f}%
                """)
        with c_repair:
            st.success("**3. Optimized Repair Design**")
            st.markdown(f"""
            - **Total Plies:** {num_plies} Layers
            - **Req. Length (ISO):** {total_repair_length_calc:.0f} mm
            - **500 mm Bands:** {num_bands_500}
            - **300 mm Bands:** {num_bands_300}
            - **Total Axial Bands:** {num_bands}
            - **Effective Covered Length:** {effective_covered_length:g} mm
            - **Procurement Axial Length:** {procurement_axial_length:g} mm
            - **Fabric Needed:** {optimized_sqm:.2f} m²
            - **Epoxy Total:** {epoxy_kg:.1f} kg
            """)
            # Add the calculation-basis note to the UI dynamically.
            st.caption(f"*Preliminary estimate based on selected ISO 24817 / ASME PCC-2 concepts for a specified design life of {design_life} years. Full ISO traceability requires route-specific verification and approved long-term design data.*")

        st.markdown("---")
        st.markdown("### 📋 Installation Checklist")
        st.markdown(f"""
        1. **Surface Prep:** Grit blast to **SA 2.5**; Profile **>60µm**.
        2. **Primer/Filler:** Apply Prowrap Filler to defect area to restore OD.
        3. **Lamination:** Saturate Carbon Cloth. Apply **{num_plies} layers** per band.
        4. **Wrapping:** Install **{num_bands_500} x 500 mm** and **{num_bands_300} x 300 mm** axial band(s), **{num_bands} total**. Maintain the fixed 50 mm inter-band stitch overlap.
        5. **Quality Control:** Minimum average Shore D hardness of **{PROWRAP['shore_d_min']}** required.
        """)

    # --- J. PDF DOWNLOAD GENERATOR WITH ERROR CATCHING ---
    st.divider()
    try:
        pdf_bytes = create_pdf(report_data)
        st.download_button(
            label="📄 Download Report as PDF",
            data=pdf_bytes,
            file_name=f"Prowrap_Repair_{safe_text(report_no)}.pdf",
            mime="application/pdf",
            type="primary"
        )
    except Exception as pdf_error:
        st.error(f"⚠️ Could not generate PDF. Error details: {pdf_error}")

# A helper function to reset calculation state when a user types a new input
def reset_calc():
    st.session_state.calc_active = False
    st.session_state.force_3_layers = False

def main():
    if 'calc_active' not in st.session_state:
        st.session_state.calc_active = False
    if 'force_3_layers' not in st.session_state:
        st.session_state.force_3_layers = False
    initialise_inputs(st.session_state)

    try:
        st.title(f"🔧 {APP_NAME}")
        st.markdown(f"**Basis:** Preliminary ISO 24817 / ASME PCC-2 screening estimate | **T-Limit:** {PROWRAP['max_temp']}°C")
        
        st.sidebar.header("1. Project Info")
        if st.sidebar.button("New / Clear Calculation", on_click=lambda: new_calculation(st.session_state), use_container_width=True):
            st.rerun()
        customer = st.sidebar.text_input("Customer", key="customer", on_change=reset_calc)
        location = st.sidebar.text_input("Location", key="location", on_change=reset_calc)
        report_no = st.sidebar.text_input("Report No", key="report_no", on_change=reset_calc)
        
        st.sidebar.header("2. Pipeline Data")
        od = st.sidebar.number_input("Pipe OD [mm]", key="od", on_change=reset_calc)
        wall = st.sidebar.number_input("Nominal Wall [mm]", key="wall", on_change=reset_calc)
        yield_str = st.sidebar.number_input("Pipe Yield [MPa]", key="yield_str", on_change=reset_calc)
        
        st.sidebar.header("3. Service Conditions")
        pres = st.sidebar.number_input("Design Pressure [bar]", key="pres", on_change=reset_calc)
        temp = st.sidebar.number_input("Op. Temperature [°C]", key="temp", on_change=reset_calc)
        
        st.sidebar.header("4. Defect Data")
        type_ = st.sidebar.selectbox(
            "Mechanism",
            [NEUTRAL_CHOICE, *MECHANISM_CHOICES],
            key="type_",
            on_change=reset_calc,
        )
        loc_ = st.sidebar.selectbox("Location", [NEUTRAL_CHOICE, "External", "Internal"], key="loc_", on_change=reset_calc)
        len_ = st.sidebar.number_input("Defect Length [mm]", key="len_", on_change=reset_calc)
        is_external_corrosion = type_ == "Corrosion" and loc_ == "External"
        defect_length_basis = ACTUAL_DEFECT_LENGTH
        individual_defects = ()
        if is_external_corrosion:
            defect_length_basis = st.sidebar.selectbox(
                "Defect Length Basis",
                [NEUTRAL_CHOICE, *DEFECT_LENGTH_BASES],
                key="defect_length_basis",
                on_change=reset_calc,
            )
            if defect_length_basis == ACTUAL_DEFECT_LENGTH:
                st.sidebar.caption(
                    "Defect Length is the longitudinal length of the "
                    "continuous or combined interacting flaw."
                )
            elif defect_length_basis in {
                INDEPENDENT_DEFECTS,
                ENTER_MANUALLY,
            }:
                st.sidebar.caption(
                    "Defect Length is the complete outer-to-outer "
                    "repair-zone span for the overall continuous repair."
                )
        manual_input_error = None
        if defect_length_basis == ENTER_MANUALLY:
            if wall is None:
                st.sidebar.caption(
                    "3t Interaction Threshold: enter the nominal wall first."
                )
            else:
                st.sidebar.caption(
                    f"3t Interaction Threshold: {3.0 * wall:.1f} mm"
                )
            edited_manual_defects = st.sidebar.data_editor(
                pd.DataFrame(
                    st.session_state.manual_defect_rows,
                    columns=MANUAL_DEFECT_COLUMNS,
                ),
                key="manual_defects_editor",
                num_rows="dynamic",
                hide_index=True,
                column_order=MANUAL_DEFECT_COLUMNS,
                column_config={
                    "Defect ID": st.column_config.TextColumn(required=True),
                    "Individual longitudinal length [mm]":
                        st.column_config.NumberColumn(
                            min_value=0.01, required=True,
                        ),
                    "Remaining wall [mm]": st.column_config.NumberColumn(
                        min_value=0.0, required=True,
                    ),
                    "Separation exceeds 3t":
                        st.column_config.CheckboxColumn(required=True),
                },
                on_change=reset_calc,
            )
            st.session_state.manual_defect_rows = (
                edited_manual_defects.to_dict("records")
            )
            try:
                individual_defects = manual_defects_from_state(
                    st.session_state
                )
            except ValueError as exc:
                manual_input_error = str(exc)
                individual_defects = ()
            rem_ = min(
                (defect.remaining_wall_mm for defect in individual_defects),
                default=None,
            )
        else:
            rem_ = st.sidebar.number_input(
                "Remaining Wall [mm]", key="rem_", on_change=reset_calc
            )
        if defect_length_basis == INDEPENDENT_DEFECTS:
            interaction_distance = 3.0 * wall if wall is not None else None
            st.sidebar.info(
                "Each corrosion defect is 10 mm longitudinal by 10 mm "
                "circumferential."
            )
            if interaction_distance is None:
                st.sidebar.info(
                    "Enter the nominal wall to calculate the 3t interaction "
                    "threshold."
                )
            else:
                st.sidebar.info(
                    "Each corrosion defect is separated from every other "
                    "defect by more than "
                    f"{interaction_distance:g} mm (3t)."
                )
            st.sidebar.info(
                "Each corrosion defect uses the entered remaining wall."
            )
            st.sidebar.info(
                "The entered defect length is the overall repair-zone span."
            )
        corr_rate = calculation_corrosion_rate(st.session_state)
        if loc_ == "Internal" and type_ == "Corrosion":
            corr_rate = st.sidebar.number_input(
                "Internal Corrosion Rate [mm/yr]", min_value=0.0, key="corr_rate",
                step=0.05, on_change=reset_calc,
                help="Post-repair growth of internal corrosion; used to project the remaining wall to end of design life. External defects are sealed by the repair (rate 0).")
        
        st.sidebar.header("5. Safety & Design Settings")
        design_life = st.sidebar.number_input("Design Life [years]", min_value=1, key="design_life", on_change=reset_calc)
        df = st.sidebar.number_input("Design Factor (f)", min_value=0.1, max_value=1.0, key="df", on_change=reset_calc)
        strain_limit_basis = st.sidebar.selectbox(
            "Strain Limit",
            [NEUTRAL_CHOICE, *STRAIN_LIMIT_CHOICES],
            key="strain_limit_basis",
            on_change=reset_calc,
        )

        st.sidebar.header("6. Installation & Load Conditions")
        st.sidebar.caption("These inputs feed the baseline design (thermal mismatch, component factor f_th, cyclic derating, Formula 4 axial loads) and the ISO Type A / Class 3 check.")
        show_typea_class3_check = st.sidebar.checkbox("Show Type A / Class 3 check", key="show_typea_class3_check", on_change=reset_calc)
        st.sidebar.caption(
            "Substrate credit is route-specific; the applicable calculation "
            "basis is shown in the result."
        )
        installation_temp = st.sidebar.number_input("Installation temperature [°C]", key="installation_temp", on_change=reset_calc)
        component_type = st.sidebar.selectbox("Component type", [NEUTRAL_CHOICE, "Straight", "Bend", "Tee", "Flange", "Reducer"], key="component_type", on_change=reset_calc)
        cyclic_derating_factor = st.sidebar.number_input("Cyclic derating factor", min_value=0.01, max_value=1.0, key="cyclic_derating_factor", on_change=reset_calc)
        axial_load_case = st.sidebar.selectbox(
            "Axial load case", [NEUTRAL_CHOICE, 0, 1], key="axial_load_case", on_change=reset_calc,
            help="1 = severed-pipe/guillotine load credible, or above-ground pipeline near bends/closures: axial loads calculated per ISO Formula 4. 0 = buried restrained pipeline: axial loads not taken into account.")
        
        cloth_width_1_mm = st.sidebar.selectbox(
            "Prowrap CF Cloth Width 1 [mm]",
            [NEUTRAL_CHOICE, 300, 500],
            key="cloth_width_1_mm",
            on_change=reset_calc,
            help="Select the first available approved axial cloth width.",
        )
        cloth_width_2_mm = st.sidebar.selectbox(
            "Prowrap CF Cloth Width 2 [mm]",
            [NEUTRAL_CHOICE, 300, 500],
            key="cloth_width_2_mm",
            on_change=reset_calc,
            help="Select the second available approved axial cloth width. Select the same value twice when only one width is available.",
        )
        missing_fields = missing_required_fields(st.session_state)
        form_ready = not missing_fields
        st.sidebar.caption(
            "After entering the last value, press Enter or Tab to apply it before calculating."
        )
        if st.sidebar.button(
            "Calculate & Optimize",
            type="primary" if form_ready else "secondary",
        ):
            if manual_input_error:
                st.session_state.calc_active = False
                st.sidebar.error(
                    f"❌ **INPUT ERROR:** {manual_input_error}"
                )
            elif missing_fields:
                st.session_state.calc_active = False
                st.sidebar.error(
                    f"Missing required fields: {', '.join(missing_fields)}."
                )
            else:
                st.session_state.calc_active = True
                st.session_state.force_3_layers = False
            
        if st.session_state.calc_active:
            run_calculation(
                customer,
                location,
                report_no,
                od,
                wall,
                pres,
                temp,
                type_,
                loc_,
                len_,
                rem_,
                yield_str,
                df,
                design_life,
                show_typea_class3_check,
                installation_temp,
                component_type,
                cyclic_derating_factor,
                corr_rate,
                axial_load_case,
                cloth_width_1_mm,
                cloth_width_2_mm,
                defect_length_basis=defect_length_basis,
                individual_defects=individual_defects,
                strain_limit_basis=strain_limit_basis,
            )
            
    except Exception as e:
        st.error(f"⚠️ Application Error: {e}")

if __name__ == "__main__":
    main()
