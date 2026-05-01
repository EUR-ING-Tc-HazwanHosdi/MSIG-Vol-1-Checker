import streamlit as st
import fitz
import re

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="MSIG Compliance Engine", layout="wide")

SEWAGE_RATE = 210

# =========================
# PDF EXTRACTION ENGINE
# =========================
def extract_pdf(file):
    text = ""
    file_bytes = file.read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    for page in doc:
        t = page.get_text()
        if t:
            text += t + "\n"

    return text


def extract_values(text):
    pe = re.search(r"(PE|Population Equivalent)[^\d]*(\d{1,7})", text, re.I)
    land = re.search(r"(Land Area|Site Area)[^\d]*(\d+\.?\d*)", text, re.I)
    pipe = re.search(r"(Pipe Diameter)[^\d]*(\d+)", text, re.I)
    slope = re.search(r"(Slope)[^\d]*(\d+\.?\d*)", text, re.I)
    stp = re.search(r"(STP|Treatment Plant Capacity)[^\d]*(\d+)", text, re.I)

    return {
        "pe": int(pe.group(2)) if pe else None,
        "land": float(land.group(2)) if land else None,
        "pipe": int(pipe.group(2)) if pipe else None,
        "slope": float(slope.group(2)) if slope else None,
        "stp": float(stp.group(2)) if stp else None,
    }


# =========================
# AUTO DETECTION ENGINE
# =========================
def detect_submission(text):
    t = text.lower()

    score_vol1 = 0
    score_vol3 = 0
    score_vol4 = 0

    # Vol 1 Planning signals
    if "population equivalent" in t or "pe" in t:
        score_vol1 += 2
    if "land area" in t:
        score_vol1 += 2
    if "planning" in t or "development" in t:
        score_vol1 += 1

    # Vol 3 Sewer signals
    if "pipe" in t or "manning" in t:
        score_vol3 += 2
    if "gradient" in t or "slope" in t:
        score_vol3 += 2
    if "manhole" in t or "sewer" in t:
        score_vol3 += 2

    # Vol 4 STP signals
    if "treatment plant" in t or "stp" in t:
        score_vol4 += 3
    if "aeration" in t or "sbr" in t:
        score_vol4 += 2
    if "effluent" in t:
        score_vol4 += 2

    scores = {
        "Vol 1 - Planning": score_vol1,
        "Vol 3 - Sewer & Pump": score_vol3,
        "Vol 4 - STP": score_vol4
    }

    best = max(scores, key=scores.get)
    confidence = scores[best] / 7  # normalize

    if scores[best] == 0:
        return "Unknown", 0.0

    return best, round(confidence, 2)


# =========================
# RISK ENGINE
# =========================
def risk_engine(values, submission_type):
    risk = 0
    issues = []
    warnings = []
    recommendations = []

    pe = values["pe"] or 0
    land = values["land"] or 0
    pipe = values["pipe"] or 0
    slope = values["slope"] or 0
    stp = values["stp"] or 0

    # Vol 1 logic
    if "Vol 1" in submission_type:
        if land < pe * 0.8:
            risk += 40
            issues.append("Insufficient land area for PE")
        if pe > 500:
            warnings.append("High development density")

    # Vol 3 logic
    if "Vol 3" in submission_type:
        if pipe < 150:
            risk += 30
            issues.append("Pipe diameter too small")
        if slope < 0.01:
            warnings.append("Low hydraulic gradient")

    # Vol 4 logic
    if "Vol 4" in submission_type:
        if stp < pe:
            risk += 50
            issues.append("STP capacity undersized")
        if stp > pe * 10:
            warnings.append("Possible overdesign STP capacity")

    # Clamp
    risk = min(risk, 100)

    if risk < 30:
        level = "Low"
    elif risk < 70:
        level = "Medium"
    else:
        level = "High"

    if not issues:
        issues.append("None detected")

    if not recommendations:
        recommendations.append("Verify compliance with MSIG guideline volumes")

    return level, risk, issues, warnings, recommendations


# =========================
# UI
# =========================
st.title("🛡️ MSIG Compliance Engine (Auto Detection v5)")

file = st.file_uploader("Upload Consultant PDF", type="pdf")

if file:

    text = extract_pdf(file)
    values = extract_values(text)

    submission_type, confidence = detect_submission(text)

    st.success(f"Detected Submission: {submission_type}  | Confidence: {confidence}")

    pe = values["pe"] or 150
    land = values["land"] or 0
    pipe = values["pipe"] or 150
    slope = values["slope"] or 0.02
    stp = values["stp"] or 0

    flow = (pe * SEWAGE_RATE) / 1000

    level, risk, issues, warnings, rec = risk_engine(values, submission_type)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Overview",
        "Vol 1 Planning",
        "Vol 3 Sewer & Pump",
        "Vol 4 STP"
    ])

    # =========================
    # OVERVIEW TAB
    # =========================
    with tab1:
        st.subheader("Extracted Parameters")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("PE", pe)
            st.metric("Land Area (m²)", land)
            st.metric("Flow (m³/day)", round(flow, 2))

        with col2:
            st.metric("Pipe Diameter", pipe)
            st.metric("Slope", slope)
            st.metric("STP Capacity", stp)

        st.subheader("Result")
        st.write(f"Risk Level: **{level}**")
        st.write(f"Score: **{100 - risk}**")

        st.progress(int(100 - risk))

    # =========================
    # VOL 1
    # =========================
    with tab2:
        st.subheader("Planning Compliance")

        if "Vol 1" in submission_type:
            st.success("Relevant Submission Type")
        else:
            st.warning("Not primary module")

        st.write("Issues:", issues)
        st.write("Warnings:", warnings)
        st.write("Recommendations:", rec)

    # =========================
    # VOL 3
    # =========================
    with tab3:
        st.subheader("Sewer & Pump Compliance")

        if "Vol 3" in submission_type:
            st.success("Relevant Submission Type")

        st.write("Pipe Diameter:", pipe)
        st.write("Slope:", slope)

        if pipe < 150:
            st.error("Pipe too small")
        else:
            st.success("Pipe OK")

    # =========================
    # VOL 4
    # =========================
    with tab4:
        st.subheader("STP Compliance")

        if "Vol 4" in submission_type:
            st.success("Relevant Submission Type")

        st.write("STP Capacity:", stp)
        st.write("Required PE:", pe)

        if stp < pe:
            st.error("STP Undersized")
        else:
            st.success("STP OK")

    # =========================
    # RAW TEXT
    # =========================
    with st.expander("Raw Extracted Text"):
        st.text(text)