import streamlit as st
import re

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="MSIG Compliance Engine",
    page_icon="🛡️",
    layout="wide"
)

# =========================
# HEADER
# =========================
st.title("🛡️ MSIG Compliance Engine (Auto Detection v6)")
st.caption("Planning • Sewer • Pump Station • STP Compliance Checker")

# =========================
# FILE UPLOAD
# =========================
uploaded_file = st.file_uploader("Upload Consultant PDF", type=["pdf"])

# =========================
# MOCK PDF TEXT EXTRACTION
# (Replace with PyMuPDF / pdfminer in production)
# =========================
def fake_pdf_extract(file):
    return """
    SEWERAGE RETICULATION CALCULATION
    Population Equivalent PE 1228
    Flow 257.88 m3/day
    Pipe Diameter 150 mm
    Slope 0.02
    STP Capacity 0
    Land Area 0 m2
    """

# =========================
# AUTO DETECT SUBMISSION TYPE
# =========================
def detect_submission(text):
    text_lower = text.lower()

    score = {
        "vol1": 0,
        "vol3": 0,
        "vol4": 0
    }

    # Vol 1 Planning signals
    if "layout" in text_lower or "planning" in text_lower:
        score["vol1"] += 2
    if "population equivalent" in text_lower:
        score["vol1"] += 1

    # Vol 3 Sewer & Pump signals
    if "pipe" in text_lower or "slope" in text_lower or "sewer" in text_lower:
        score["vol3"] += 2
    if "pump" in text_lower or "manhole" in text_lower:
        score["vol3"] += 2

    # Vol 4 STP signals
    if "stp" in text_lower or "treatment" in text_lower:
        score["vol4"] += 3
    if "capacity" in text_lower:
        score["vol4"] += 1

    best = max(score, key=score.get)

    mapping = {
        "vol1": "📘 Vol 1 - Planning Submission",
        "vol3": "📗 Vol 3 - Sewer & Pump Submission",
        "vol4": "📕 Vol 4 - STP Submission"
    }

    confidence = round(score[best] / 5, 2)

    if confidence < 0.3:
        return "Unknown", 0.0

    return mapping[best], confidence

# =========================
# PARAMETER EXTRACTION (simple regex engine)
# =========================
def extract_parameters(text):
    def find(pattern):
        match = re.search(pattern, text)
        return float(match.group(1)) if match else 0

    return {
        "PE": find(r"PE\s*[:=]?\s*(\d+)"),
        "Flow": find(r"Flow\s*[:=]?\s*([\d.]+)"),
        "Pipe": find(r"Pipe Diameter\s*[:=]?\s*(\d+)"),
        "Slope": find(r"Slope\s*[:=]?\s*([\d.]+)"),
        "STP": find(r"STP Capacity\s*[:=]?\s*(\d+)"),
        "Land": find(r"Land Area\s*[:=]?\s*([\d.]+)")
    }

# =========================
# ENGINE LOGIC
# =========================
def compliance_engine(params, submission_type):

    issues = []
    warnings = []
    score = 100

    # VOL 1 CHECKS
    if "Vol 1" in submission_type:
        if params["PE"] > 500:
            warnings.append("⚠️ High development density")
            score -= 10
        if params["Land"] < 100:
            warnings.append("⚠️ Small land area may affect planning")
            score -= 15

    # VOL 3 CHECKS
    if "Vol 3" in submission_type:
        if params["Pipe"] < 150:
            issues.append("❌ Pipe diameter too small")
            score -= 25
        if params["Slope"] < 0.01:
            warnings.append("⚠️ Low slope may affect flow")
            score -= 10

    # VOL 4 CHECKS
    if "Vol 4" in submission_type:
        if params["STP"] < params["PE"]:
            issues.append("❌ STP undersized for PE")
            score -= 30

    # fallback safety
    if submission_type == "Unknown":
        issues.append("❌ Cannot reliably detect submission type")
        score = 0

    # risk level
    if score >= 80:
        risk = "Low"
    elif score >= 50:
        risk = "Medium"
    else:
        risk = "Critical"

    return risk, score, issues, warnings

# =========================
# MAIN APP
# =========================
if uploaded_file:

    raw_text = fake_pdf_extract(uploaded_file)

    submission_type, confidence = detect_submission(raw_text)
    params = extract_parameters(raw_text)

    risk, score, issues, warnings = compliance_engine(params, submission_type)

    st.success(f"Detected: {submission_type} | Confidence: {confidence}")

    # =========================
    # TABS SYSTEM (CORE FEATURE)
    # =========================
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview",
        "📘 Vol 1 Planning",
        "📗 Vol 3 Sewer & Pump",
        "📕 Vol 4 STP"
    ])

    with tab1:
        st.subheader("📊 Compliance Summary")
        st.metric("Risk Level", risk)
        st.metric("Score", f"{score}/100")

        st.json(params)

        if issues:
            st.error("Issues Found")
            for i in issues:
                st.write(i)

        if warnings:
            st.warning("Warnings")
            for w in warnings:
                st.write(w)

    with tab2:
        st.subheader("📘 Planning Review")
        st.write("Population, Land Use, Density Analysis")

        if "Vol 1" in submission_type:
            st.success("This submission includes Planning Scope")
        else:
            st.info("Not detected as Planning submission")

    with tab3:
        st.subheader("📗 Sewer & Pump Review")

        if "Vol 3" in submission_type:
            st.success("Sewerage Reticulation detected")

        st.write("Pipe sizing, slope, hydraulic flow checks")

    with tab4:
        st.subheader("📕 STP Review")

        if "Vol 4" in submission_type:
            st.success("STP Submission detected")

        st.write("Treatment capacity vs PE comparison")

else:
    st.info("Upload a consultant PDF to start compliance checking")