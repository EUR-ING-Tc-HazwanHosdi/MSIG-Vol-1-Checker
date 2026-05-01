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
# PDF EXTRACTOR (SAFE)
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
# AUTO DETECT SUBMISSION TYPE
# =========================
def detect_submission_type(text):
    text = text.lower()

    vol1 = ["population equivalent", "site area", "land area", "planning", "development"]
    vol3 = ["sewer", "pipe", "manhole", "invert", "pump", "hydraulic", "gradient", "flow"]
    vol4 = ["stp", "treatment", "aeration", "effluent", "bod", "sludge", "wwtp"]

    score1 = sum(2 for k in vol1 if k in text)
    score3 = sum(2 for k in vol3 if k in text)
    score4 = sum(2 for k in vol4 if k in text)

    scores = {
        "Vol 1 - Planning Submission": score1,
        "Vol 3 - Sewer & Pump Submission": score3,
        "Vol 4 - STP Submission": score4
    }

    best = max(scores, key=scores.get)

    if scores[best] == 0:
        return "Unknown"

    return best


# =========================
# ENGINE CORE
# =========================
class Engine:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.recommendations = []
        self.score = 100

    def issue(self, msg):
        self.issues.append(msg)
        self.score -= 25

    def warn(self, msg):
        self.warnings.append(msg)
        self.score -= 10

    def recommend(self, msg):
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
# VOL 1 ENGINE
# =========================
def run_vol1(engine, pe, land):
    density = pe / land if land > 0 else 0

    if pe < 150:
        engine.issue("PE below MSIG minimum (150)")

    if density > 1:
        engine.warn("High development density")

    if land < 300:
        engine.warn("Small land area for planning")

    engine.recommend("Check zoning & authority requirements")

    return engine


# =========================
# VOL 3 ENGINE
# =========================
def run_vol3(engine, pipe, slope, flow):

    if pipe < 150:
        engine.issue("Pipe diameter below standard (150mm)")

    if slope < 0.005:
        engine.issue("Slope too low → blockage risk")

    if slope > 0.05:
        engine.issue("Slope unrealistic (>5%)")

    if flow <= 0:
        engine.issue("Invalid flow input")

    engine.recommend("Check hydraulic gradient & pump sizing")

    return engine


# =========================
# VOL 4 ENGINE
# =========================
def run_vol4(engine, pe, capacity):

    if capacity <= 0:
        engine.issue("STP capacity not defined")

    if capacity < pe:
        engine.issue("STP undersized for PE")

    if capacity > pe * 2:
        engine.warn("Possible overdesign (cost inefficiency)")

    engine.recommend("Verify treatment process selection")

    return engine


# =========================
# RUN ENGINE
# =========================
def run_engine(data, module):
    engine = Engine()

    if module == "Vol 1 - Planning Submission":
        engine = run_vol1(engine, data["pe"], data["land"])

    elif module == "Vol 3 - Sewer & Pump Submission":
        engine = run_vol3(engine, data["pipe"], data["slope"], data["flow"])

    elif module == "Vol 4 - STP Submission":
        engine = run_vol4(engine, data["pe"], data["capacity"])

    return engine.finalize()


# =========================
# PDF REPORT
# =========================
def generate_report(result, data, module):
    file = "MSIG_Report.pdf"
    doc = SimpleDocTemplate(file)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("MSIG COMPLIANCE ENGINE REPORT", styles["Title"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Submission Type: {module}", styles["Heading3"]))
    content.append(Spacer(1, 10))

    for k, v in data.items():
        content.append(Paragraph(f"{k}: {v}", styles["Normal"]))

    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Risk: {result['risk']}", styles["Heading3"]))
    content.append(Paragraph(f"Score: {result['score']}", styles["Normal"]))

    def section(title, items):
        content.append(Spacer(1, 10))
        content.append(Paragraph(title, styles["Heading3"]))
        for i in items:
            content.append(Paragraph(f"- {i}", styles["Normal"]))

    section("Issues", result["issues"] or ["None"])
    section("Warnings", result["warnings"] or ["None"])
    section("Recommendations", result["recommendations"] or ["None"])

    doc.build(content)
    return file


# =========================
# UI
# =========================
st.title("🛡️ MSIG Compliance Engine (Auto Detect)")

file = st.file_uploader("Upload Consultant PDF", type="pdf")

if file:

    pe, land, text = extract_pdf(file)
    module = detect_submission_type(text)

    st.info(f"Detected Submission Type: {module}")

    flow = (pe * 210) / 1000

    # INPUTS
    pe = st.number_input("PE", value=pe)
    land = st.number_input("Land Area", value=land)

    pipe = st.number_input("Pipe Diameter", value=150)
    slope = st.number_input("Slope", value=0.01)
    capacity = st.number_input("STP Capacity", value=200)

    data = {
        "pe": pe,
        "land": land,
        "flow": flow,
        "pipe": pipe,
        "slope": slope,
        "capacity": capacity
    }

    if st.button("Run MSIG Engine"):

        result = run_engine(data, module)

        st.subheader("RESULT")
        st.write("Risk:", result["risk"])
        st.write("Score:", result["score"])

        st.subheader("Issues")
        for i in result["issues"]:
            st.write("❌", i)

        st.subheader("Warnings")
        for i in result["warnings"]:
            st.write("⚠️", i)

        st.subheader("Recommendations")
        for i in result["recommendations"]:
            st.write("✅", i)

        pdf = generate_report(result, data, module)

        with open(pdf, "rb") as f:
            st.download_button("Download Report", f, file_name="MSIG_Report.pdf")

        with st.expander("Raw Extracted Text"):
            st.text(text)