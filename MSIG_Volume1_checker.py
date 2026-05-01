import streamlit as st
import fitz
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="MSIG Compliance Engine", layout="wide")


# =========================
# ENGINE CORE
# =========================
class ComplianceEngine:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.recommendations = []
        self.score = 100

    def add_issue(self, msg):
        self.issues.append(msg)
        self.score -= 25

    def add_warning(self, msg):
        self.warnings.append(msg)
        self.score -= 10

    def add_recommendation(self, msg):
        self.recommendations.append(msg)

    def finalize(self):
        self.score = max(0, self.score)

        if self.score >= 80:
            risk = "Low"
        elif self.score >= 50:
            risk = "Medium"
        else:
            risk = "High"

        return {
            "score": self.score,
            "risk": risk,
            "issues": self.issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations
        }


# =========================
# PDF PARSER (SAFE)
# =========================
def extract_pdf(file):
    try:
        text = ""
        file_bytes = file.getvalue()
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page in doc:
            text += page.get_text()

        pe = re.search(r"PE\s*[:\-]?\s*(\d{2,6})", text)
        land = re.search(r"(Land Area|Site Area)[^\d]*(\d+\.?\d*)", text)

        return (
            int(pe.group(1)) if pe else 150,
            float(land.group(2)) if land else 0.0,
            text
        )

    except Exception:
        return 150, 0.0, ""


# =========================
# VOL 1 ENGINE (PLANNING)
# =========================
def run_vol1(engine, pe, land):
    density = pe / land if land > 0 else 0

    if pe < 150:
        engine.add_issue("PE below MSIG minimum (150)")

    if density > 1:
        engine.add_warning("High site density detected")

    if land < 300:
        engine.add_warning("Small land area may affect layout planning")

    engine.add_recommendation("Verify local authority zoning compliance")

    return engine


# =========================
# VOL 3 ENGINE (SEWER + PUMP)
# =========================
def run_vol3(engine, pipe, slope, flow):

    if pipe < 150:
        engine.add_issue("Pipe diameter below 150mm standard")

    if slope < 0.005:
        engine.add_issue("Slope too low → risk of sedimentation")

    if flow > 100:
        engine.add_warning("High flow → check pump capacity")

    engine.add_recommendation("Verify hydraulic gradient and manhole spacing")

    return engine


# =========================
# VOL 4 ENGINE (STP)
# =========================
def run_vol4(engine, pe, capacity):

    if capacity < pe:
        engine.add_issue("STP undersized for design PE")

    if capacity > pe * 1.5:
        engine.add_warning("Possible overdesign (cost inefficiency)")

    engine.add_recommendation("Confirm treatment process selection (SBR / Extended Aeration)")

    return engine


# =========================
# RUN ENGINE
# =========================
def run_engine(data):
    engine = ComplianceEngine()

    engine = run_vol1(engine, data["pe"], data["land"])
    engine = run_vol3(engine, data["pipe"], data["slope"], data["flow"])
    engine = run_vol4(engine, data["pe"], data["capacity"])

    return engine.finalize()


# =========================
# PDF REPORT GENERATOR
# =========================
def generate_report(result, data):
    filename = "MSIG_Report.pdf"
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("MSIG COMPLIANCE ENGINE REPORT", styles["Title"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("PROJECT DATA", styles["Heading3"]))
    content.append(Paragraph(f"PE: {data['pe']}", styles["Normal"]))
    content.append(Paragraph(f"Land Area: {data['land']} m²", styles["Normal"]))
    content.append(Paragraph(f"Flow: {data['flow']:.2f} m³/day", styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("RESULT", styles["Heading3"]))
    content.append(Paragraph(f"Risk Level: {result['risk']}", styles["Normal"]))
    content.append(Paragraph(f"Score: {result['score']}", styles["Normal"]))
    content.append(Spacer(1, 10))

    def section(title, items):
        content.append(Paragraph(title, styles["Heading3"]))
        for i in items:
            content.append(Paragraph(f"- {i}", styles["Normal"]))

    section("Issues", result["issues"] or ["None"])
    section("Warnings", result["warnings"] or ["None"])
    section("Recommendations", result["recommendations"] or ["None"])

    doc.build(content)
    return filename


# =========================
# UI
# =========================
st.title("🛡️ MSIG Compliance Engine (Professional)")

tab1, tab2, tab3 = st.tabs([
    "Vol 1: Planning",
    "Vol 3: Sewer & Pump",
    "Vol 4: STP"
])

# =========================
# TAB 1
# =========================
with tab1:
    file = st.file_uploader("Upload Consultant PDF", type="pdf")

    if file:
        pe, land, text = extract_pdf(file)
        flow = (pe * 210) / 1000

        col1, col2 = st.columns(2)

        with col1:
            pe = st.number_input("PE", value=pe)
            land = st.number_input("Land Area (m²)", value=land)
            st.metric("Flow", f"{flow:.2f} m³/day")

        with col2:
            pipe = st.number_input("Pipe Diameter (mm)", value=150)
            slope = st.number_input("Slope", value=0.01)
            capacity = st.number_input("STP Capacity (PE)", value=200)

            if st.button("Run MSIG Engine"):

                data = {
                    "pe": pe,
                    "land": land,
                    "flow": flow,
                    "pipe": pipe,
                    "slope": slope,
                    "capacity": capacity
                }

                result = run_engine(data)

                st.subheader("RESULT")
                st.write("Risk:", result["risk"])
                st.write("Score:", result["score"])

                st.subheader("Issues")
                for i in result["issues"]:
                    st.write("-", i)

                st.subheader("Warnings")
                for i in result["warnings"]:
                    st.write("-", i)

                st.subheader("Recommendations")
                for i in result["recommendations"]:
                    st.write("-", i)

                pdf = generate_report(result, data)

                with open(pdf, "rb") as f:
                    st.download_button("Download Report", f, file_name="MSIG_Report.pdf")

        with st.expander("Raw Extracted Text"):
            st.text(text)


# =========================
# TAB 2 (VIEW ONLY)
# =========================
with tab2:
    st.subheader("Sewer & Pump Overview")
    st.info("This module is integrated into the engine. Use Vol 1 tab to run full checks.")


# =========================
# TAB 3 (VIEW ONLY)
# =========================
with tab3:
    st.subheader("STP Overview")
    st.info("STP logic is integrated into engine scoring system.")