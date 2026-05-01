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
# PDF EXTRACTOR
# =========================
def extract_pdf(file):
    text = ""
    file.seek(0)
    doc = fitz.open(stream=file.read(), filetype="pdf")

    for page in doc:
        t = page.get_text()
        if t:
            text += t + "\n"

    pe = re.search(r"(PE|Population Equivalent)[^\d]*(\d{2,6})", text, re.I)
    land = re.search(r"(Land Area|Site Area)[^\d]*(\d+\.?\d*)", text, re.I)

    pe_val = int(pe.group(2)) if pe else None
    land_val = float(land.group(2)) if land else None

    return pe_val, land_val, text


# =========================
# LOGIC ENGINE (VOL 1)
# =========================
def get_class(pe):
    for c, mn, mx in STP_CLASSES:
        if mn <= pe <= mx:
            return c
    return "Unknown"


def check_compliance(pe, land, flow):
    issues = []
    recommendations = []
    observations = []

    stp_class = get_class(pe)

    # Rules
    if pe < 150:
        issues.append("PE below minimum requirement (150)")
        recommendations.append("Increase PE to at least 150")

    if stp_class == 1:
        ref_pe = min(CLASS_1_LAND.keys(), key=lambda x: abs(x - pe))
        required_land = CLASS_1_LAND[ref_pe]

        if land < required_land:
            issues.append(f"Land area insufficient (Required: {required_land} m²)")
            recommendations.append("Increase land area to meet requirement")
    else:
        issues.append("Land check requires manual review for Class >1")

    # Observations
    observations.append(f"System classified as Class {stp_class}")
    observations.append(f"Detected PE: {pe}")
    observations.append(f"Estimated Flow: {flow:.2f} m³/day")

    if len(issues) == 0:
        observations.append("No major non-compliance detected based on available data")

    # Assumptions
    assumptions = [
        "Flow calculated using 210 L/person/day",
        "Land requirement based on nearest MSIG reference",
        "Limited to extracted data from PDF"
    ]

    # Limitations
    limitations = [
        "Automatic extraction may miss tabulated/drawing data",
        "Manual verification required for full compliance",
        "Class >1 requires detailed engineering review"
    ]

    # Risk
    risk_score = min(len(issues) * 30, 100)
    if len(issues) == 0:
        risk_score = 10

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
        "risk": risk_score,
        "confidence": confidence
    }


# =========================
# REPORT GENERATOR
# =========================
def generate_report(result, pe, land, flow):
    file_name = "MSIG_Compliance_Report.pdf"
    doc = SimpleDocTemplate(file_name)
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

    content.append(Paragraph("Compliance Summary", styles["Heading3"]))
    content.append(Paragraph(f"Status: {result['status']}", styles["Normal"]))
    content.append(Paragraph(f"Class: {result['class']}", styles["Normal"]))
    content.append(Paragraph(f"Risk Score: {result['risk']}%", styles["Normal"]))
    content.append(Paragraph(f"Confidence: {result['confidence']}", styles["Normal"]))
    content.append(Spacer(1, 10))

    sections = ["observations", "issues", "recommendations", "assumptions", "limitations"]

    for sec in sections:
        content.append(Paragraph(sec.capitalize(), styles["Heading3"]))
        items = result.get(sec, [])
        if items:
            for i in items:
                content.append(Paragraph(f"- {i}", styles["Normal"]))
        else:
            content.append(Paragraph("None", styles["Normal"]))

    doc.build(content)
    return file_name


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
# TAB 1 (STP)
# =========================
with tab1:
    file = st.file_uploader("Upload Consultant Proposal (PDF)", type="pdf", key="upload")

    if file:
        pe, land, text = extract_pdf(file)

        pe = pe or 150
        land = land or 0.0

        flow = (pe * SEWAGE_RATE) / 1000

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Extracted Data")
            pe = st.number_input("PE", value=pe, key="pe_input")
            land = st.number_input("Land Area", value=land, key="land_input")
            st.metric("Flow (m³/d)", f"{flow:.2f}")

        with col2:
            if st.button("Run Compliance Check"):
                result = check_compliance(pe, land, flow)

                st.subheader("Result")
                st.write(result["status"])
                st