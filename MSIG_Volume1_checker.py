import streamlit as st
import fitz
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="MSIG Compliance Checker", layout="wide")

SEWAGE_RATE = 210

STP_CLASSES = [
    (1, 150, 1000),
    (2, 1001, 5000),
    (3, 5001, 20000),
    (4, 20001, 10**9)
]

CLASS_1_LAND = {
    150: 283,
    200: 360,
    500: 664,
    1000: 1016
}

# =========================
# SAFE PDF EXTRACTOR
# =========================
def extract_pdf(file):
    text = ""

    try:
        file_bytes = file.getvalue()
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page in doc:
            t = page.get_text()
            if t:
                text += t + "\n"

        # safer regex
        pe_match = re.search(r"PE\s*[:\-]?\s*(\d{2,6})", text, re.I)
        land_match = re.search(r"(Land Area|Site Area)[^\d]*(\d+\.?\d*)", text, re.I)

        pe_val = int(pe_match.group(1)) if pe_match else None
        land_val = float(land_match.group(2)) if land_match else None

        return pe_val, land_val, text

    except Exception:
        return None, None, ""


# =========================
# CLASS ENGINE
# =========================
def get_class(pe):
    for c, mn, mx in STP_CLASSES:
        if mn <= pe <= mx:
            return c
    return "Unknown"


# =========================
# COMPLIANCE ENGINE (VOL 1)
# =========================
def check_compliance(pe, land, flow):
    issues = []
    recommendations = []
    observations = []

    stp_class = get_class(pe)

    # RULES
    if pe < 150:
        issues.append("PE below minimum requirement (150)")
        recommendations.append("Increase design PE to minimum 150")

    if stp_class == 1:
        ref_pe = min(CLASS_1_LAND.keys(), key=lambda x: abs(x - pe))
        required_land = CLASS_1_LAND[ref_pe]

        if land < required_land:
            issues.append(f"Insufficient land area (Min: {required_land} m²)")
            recommendations.append("Increase site area or revise layout")
    else:
        issues.append("Class >1 requires manual engineering verification")

    # OBSERVATIONS
    observations.append(f"Detected Class: {stp_class}")
    observations.append(f"Population Equivalent: {pe}")
    observations.append(f"Estimated Flow: {flow:.2f} m³/day")

    if len(issues) == 0:
        observations.append("No critical non-compliance detected")

    # ASSUMPTIONS
    assumptions = [
        "Flow based on 210 L/person/day",
        "Land check based on nearest Class 1 reference",
        "Extraction limited to PDF text only"
    ]

    # LIMITATIONS
    limitations = [
        "Cannot fully read drawings/tables in PDF",
        "Requires manual engineering verification",
        "Only supports simplified MSIG logic"
    ]

    # RISK
    risk = min(len(issues) * 30, 100)
    if len(issues) == 0:
        risk = 10

    confidence = "High" if pe and land else "Medium"

    status = "Compliant" if len(issues) == 0 else "Non-Compliant"

    return {
        "status": status,
        "class": stp_class,
        "issues": issues,
        "recommendations": recommendations,
        "observations": observations,
        "assumptions": assumptions,
        "limitations": limitations,
        "risk": risk,
        "confidence": confidence
    }


# =========================
# PDF REPORT GENERATOR
# =========================
def generate_report(result, pe, land, flow):
    filename = "MSIG_Compliance_Report.pdf"
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("MSIG COMPLIANCE CHECKER", styles["Title"]))
    content.append(Paragraph("Engineering Compliance Report", styles["Heading2"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Project Data", styles["Heading3"]))
    content.append(Paragraph(f"PE: {pe}", styles["Normal"]))
    content.append(Paragraph(f"Land Area: {land} m²", styles["Normal"]))
    content.append(Paragraph(f"Flow: {flow:.2f} m³/day", styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Summary", styles["Heading3"]))
    content.append(Paragraph(f"Status: {result['status']}", styles["Normal"]))
    content.append(Paragraph(f"Class: {result['class']}", styles["Normal"]))
    content.append(Paragraph(f"Risk Score: {result['risk']}%", styles["Normal"]))
    content.append(Paragraph(f"Confidence: {result['confidence']}", styles["Normal"]))
    content.append(Spacer(1, 10))

    def add_section(title, items):
        content.append(Paragraph(title, styles["Heading3"]))
        for i in items:
            content.append(Paragraph(f"- {i}", styles["Normal"]))

    add_section("Observations", result["observations"])
    add_section("Issues", result["issues"] or ["None"])
    add_section("Recommendations", result["recommendations"])
    add_section("Assumptions", result["assumptions"])
    add_section("Limitations", result["limitations"])

    doc.build(content)
    return filename


# =========================
# UI
# =========================
st.title("🛡️ MSIG Compliance Checker")

tab1, tab2, tab3 = st.tabs([
    "Vol 1: STP",
    "Vol 3: Sewer Line",
    "Vol 4: Pump Station"
])

# =========================
# TAB 1
# =========================
with tab1:
    file = st.file_uploader("Upload Consultant Proposal (PDF)", type="pdf")

    if file:
        pe, land, text = extract_pdf(file)

        pe = pe or 150
        land = land or 0.0

        flow = (pe * SEWAGE_RATE) / 1000

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Extracted Data")
            pe = st.number_input("PE", value=pe)
            land = st.number_input("Land Area (m²)", value=land)
            st.metric("Flow (m³/day)", f"{flow:.2f}")

        with col2:
            if st.button("Run Compliance Check"):
                result = check_compliance(pe, land, flow)

                st.subheader("Result")
                st.write(f"Status: {result['status']}")
                st.metric("Risk Score", f"{result['risk']}%")
                st.write(f"Confidence: {result['confidence']}")

                st.subheader("Observations")
                for i in result["observations"]:
                    st.write(f"- {i}")

                st.subheader("Issues")
                for i in result["issues"]:
                    st.write(f"- {i}")

                st.subheader("Recommendations")
                for i in result["recommendations"]:
                    st.write(f"- {i}")

                pdf = generate_report(result, pe, land, flow)

                with open(pdf, "rb") as f:
                    st.download_button("Download Report", f, file_name="MSIG_Report.pdf")

        with st.expander("Raw Extracted Text"):
            st.text(text)


# =========================
# TAB 2 (SEWER LINE)
# =========================
with tab2:
    st.subheader("Sewer Line Check (Vol 3)")

    pipe = st.number_input("Pipe Diameter (mm)", value=150)
    slope = st.number_input("Slope", value=0.01)

    issues = []

    if pipe < 150:
        issues.append("Pipe diameter below minimum requirement (150mm)")
    if slope < 0.005:
        issues.append("Slope too low (risk of blockage)")

    if issues:
        st.error("Issues Found")
        for i in issues:
            st.write(f"- {i}")
    else:
        st.success("Basic sewer line compliance OK")


# =========================
# TAB 3 (PUMP STATION)
# =========================
with tab3:
    st.subheader("Pump Station Check (Vol 4)")

    redundancy = st.selectbox("Pump Redundancy", ["Yes", "No"])

    if redundancy == "No":
        st.error("Non-compliant: No standby pump provided")
    else:
        st.success("Pump redundancy OK")