import streamlit as st
import fitz
import re

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="MSIG Compliance Engine", layout="wide")

SEWAGE_RATE = 210


# =========================
# PDF EXTRACTION
# =========================
def extract_pdf(file):
    text = ""
    file_bytes = file.read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    for page in doc:
        page_text = page.get_text()
        if page_text:
            text += page_text + "\n"

    return text


# =========================
# ENGINEERING VALUE EXTRACTION (FIXED)
# =========================
def extract_values(text):

    def safe_int(pattern):
        m = re.search(pattern, text, re.I)
        try:
            return int(m.group(1))
        except:
            return None

    def safe_float(pattern):
        m = re.search(pattern, text, re.I)
        try:
            return float(m.group(1))
        except:
            return None

    pe = safe_int(r"population\s*equivalent[^\d]*(\d{2,7})")
    if not pe:
        pe = safe_int(r"\bPE\b[^\d]*(\d{2,7})")

    land = safe_float(r"land\s*area[^\d]*(\d+\.?\d*)")

    pipe = safe_int(r"pipe\s*diameter[^\d]*(\d{2,4})")

    slope = safe_float(r"slope[^\d]*(\d+\.?\d*)")

    stp = safe_int(r"(stp|treatment\s*plant)[^\d]*(\d{2,7})")

    return {
        "pe": pe,
        "land": land,
        "pipe": pipe,
        "slope": slope,
        "stp": stp,
    }


# =========================
# AUTO DETECTION ENGINE
# =========================
def detect_submission(text):
    t = text.lower()

    vol1 = sum([
        "population equivalent" in t,
        "land area" in t,
        "planning" in t
    ])

    vol3 = sum([
        "pipe" in t,
        "manning" in t,
        "gradient" in t,
        "manhole" in t
    ])

    vol4 = sum([
        "treatment plant" in t,
        "stp" in t,
        "aeration" in t,
        "effluent" in t
    ])

    scores = {
        "Vol 1 - Planning": vol1,
        "Vol 3 - Sewer & Pump": vol3,
        "Vol 4 - STP": vol4
    }

    best = max(scores, key=scores.get)
    confidence = scores[best] / 4

    if scores[best] == 0:
        return "Unknown", 0.0

    return best, round(confidence, 2)


# =========================
# VALIDATION LAYER
# =========================
def validate_inputs(v):
    errors = []

    if not v["pe"] or v["pe"] < 10:
        errors.append("Invalid or missing PE")

    if v["land"] is None:
        errors.append("Missing land area")

    if v["pipe"] and (v["pipe"] < 100 or v["pipe"] > 2000):
        errors.append("Pipe diameter unrealistic")

    if v["slope"] and v["slope"] > 5:
        errors.append("Slope unrealistic")

    return errors


# =========================
# RISK ENGINE
# =========================
def risk_engine(values, submission_type):

    errors = validate_inputs(values)

    if errors:
        return "Critical", 0, errors, ["Fix PDF extraction / improve document clarity"], ["Re-upload cleaner PDF"]

    pe = values["pe"] or 0
    land = values["land"] or 0
    pipe = values["pipe"] or 0
    slope = values["slope"] or 0
    stp = values["stp"] or 0

    risk = 0
    issues = []
    warnings = []
    rec = []

    # ================= VOL 1 =================
    if "Vol 1" in submission_type:
        if land < pe * 0.8:
            risk += 50
            issues.append("Insufficient land area for PE")

    # ================= VOL 3 =================
    if "Vol 3" in submission_type:
        if pipe < 150:
            risk += 40
            issues.append("Pipe undersized")

        if slope < 0.01:
            risk += 20
            warnings.append("Low hydraulic slope")

    # ================= VOL 4 =================
    if "Vol 4" in submission_type:
        if stp < pe:
            risk += 60
            issues.append("STP undersized")

    score = max(0, 100 - risk)

    if score >= 80:
        level = "Low"
    elif score >= 50:
        level = "Medium"
    else:
        level = "High"

    if not issues:
        issues.append("No critical issues detected")

    rec.append("Verify MSIG Volume compliance before submission")

    return level, score, issues, warnings, rec


# =========================
# UI
# =========================
st.title("🛡️ MSIG Compliance Engine (Auto Detection v5 - Pro)")

file = st.file_uploader("Upload Consultant PDF", type="pdf")

if file:

    text = extract_pdf(file)
    values = extract_values(text)

    submission_type, confidence = detect_submission(text)

    st.success(f"Detected: {submission_type} | Confidence: {confidence}")

    pe = values["pe"] or 0
    land = values["land"] or 0
    pipe = values["pipe"] or 0
    slope = values["slope"] or 0
    stp = values["stp"] or 0

    flow = (pe * SEWAGE_RATE) / 1000 if pe else 0

    level, score, issues, warnings, rec = risk_engine(values, submission_type)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview",
        "📘 Vol 1 Planning",
        "📗 Vol 3 Sewer & Pump",
        "📕 Vol 4 STP"
    ])

    # ================= OVERVIEW =================
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

        st.subheader("Compliance Result")
        st.write(f"Risk Level: **{level}**")
        st.write(f"Score: **{score}/100**")

        st.progress(score)

        st.write("Issues:", issues)
        st.write("Warnings:", warnings)
        st.write("Recommendations:", rec)

    # ================= VOL 1 =================
    with tab2:
        st.subheader("Planning Submission (Vol 1)")

        if "Vol 1" in submission_type:
            st.success("Detected as Planning Submission")
        else:
            st.warning("Not primary module")

        st.write("Land Area:", land)
        st.write("PE:", pe)

    # ================= VOL 3 =================
    with tab3:
        st.subheader("Sewer & Pump (Vol 3)")

        if "Vol 3" in submission_type:
            st.success("Detected Sewer/Pump Submission")

        st.write("Pipe Diameter:", pipe)
        st.write("Slope:", slope)

        if pipe and pipe < 150:
            st.error("Pipe undersized")

    # ================= VOL 4 =================
    with tab4:
        st.subheader("STP Submission (Vol 4)")

        if "Vol 4" in submission_type:
            st.success("Detected STP Submission")

        st.write("STP Capacity:", stp)
        st.write("Required PE:", pe)

        if stp and pe and stp < pe:
            st.error("STP Undersized")

    # ================= RAW =================
    with st.expander("Raw Extracted Text"):
        st.text(text)