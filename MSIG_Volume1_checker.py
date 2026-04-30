import streamlit as st
import fitz
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="STP Smart Assist Pro", layout="wide")

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
    file_bytes = file.read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")

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
# LOGIC ENGINE
# =========================
def get_class(pe):
    for c, mn, mx in STP_CLASSES:
        if mn <= pe <= mx:
            return c
    return "Unknown"


def check_compliance(pe, land):
    issues = []
    recommendations = []

    stp_class = get_class(pe)

    # Rule 1: Minimum PE
    if pe < 150:
        issues.append("PE below minimum requirement (150)")
        recommendations.append("Increase PE to at least 150")

    # Rule 2: Land check (Class 1 only)
    if stp_class == 1:
        ref_pe = min(CLASS_1_LAND.keys(), key=lambda x: abs(x - pe))
        required_land = CLASS_1_LAND[ref_pe]

        if land < required_land:
            issues.append(f"Land area insufficient (Required: {required_land} m²)")
            recommendations.append("Increase land area to meet requirement")
    else:
        issues.append("Land check requires manual review for Class >1")

    # Risk Score
    risk_score = min(len(issues) * 30, 100)

    status = "Compliant" if len(issues) == 0 else "Non-Compliant"

    return {
        "status": status,
        "class": stp_class,
        "issues": issues,
        "recommendations": recommendations,
        "risk": risk_score
    }


# =========================
# REPORT GENERATOR
# =========================
def generate_report(result):
    file_name = "stp_report.pdf"
    doc = SimpleDocTemplate(file_name)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph(f"Status: {result['status']}", styles["Title"]))
    content.append(Paragraph(f"Class: {result['class']}", styles["Normal"]))
    content.append(Paragraph(f"Risk Score: {result['risk']}%", styles["Normal"]))

    content.append(Paragraph("Issues:", styles["Heading2"]))
    for i in result["issues"]:
        content.append(Paragraph(f"- {i}", styles["Normal"]))

    content.append(Paragraph("Recommendations:", styles["Heading2"]))
    for r in result["recommendations"]:
        content.append(Paragraph(f"- {r}", styles["Normal"]))

    doc.build(content)
    return file_name


# =========================
# UI
# =========================
st.title("🛡️ STP Smart Assist Pro")

file = st.file_uploader("Upload Consultant Proposal (PDF)", type="pdf", key="upload")

if file:
    pe, land, text = extract_pdf(file)

    pe = pe or 150
    land = land or 0.0

    col1, col2 = st.columns(2)

    # LEFT SIDE
    with col1:
        st.subheader("📋 Extracted Data")

        pe = st.number_input("Population Equivalent (PE)", value=pe, key="pe_input")
        land = st.number_input("Land Area (m²)", value=land, key="land_input")

        flow = (pe * SEWAGE_RATE) / 1000
        st.metric("Flow (m³/d)", f"{flow:.2f}")

    # RIGHT SIDE
    with col2:
        st.subheader("✅ Compliance Result")

        if st.button("Run Compliance Check"):
            result = check_compliance(pe, land)

            st.write(f"**Status:** {result['status']}")
            st.write(f"**Class:** {result['class']}")
            st.metric("Risk Score", f"{result['risk']}%")

            st.subheader("Issues")
            for i in result["issues"]:
                st.write(f"- {i}")

            st.subheader("Recommendations")
            for r in result["recommendations"]:
                st.write(f"- {r}")

            report_file = generate_report(result)

            with open(report_file, "rb") as f:
                st.download_button(
                    "📥 Download Compliance Report",
                    f,
                    file_name="STP_Compliance_Report.pdf"
                )

    with st.expander("Raw Extracted Text"):
        st.text(text)