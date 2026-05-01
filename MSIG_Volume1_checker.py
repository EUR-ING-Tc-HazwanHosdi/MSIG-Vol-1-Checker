import streamlit as st
import fitz
import re

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="MSIG Compliance Engine", layout="wide")

SEWAGE_RATE = 210


# =========================
# PDF TEXT EXTRACTION
# =========================
def extract_pdf(file):
    text = ""

    try:
        doc = fitz.open(stream=file.getvalue(), filetype="pdf")
        for page in doc:
            text += page.get_text() + "\n"
    except:
        return 150, 0.0, ""

    pe = re.search(r"(PE|Population Equivalent)[^\d]*(\d{2,6})", text, re.I)
    land = re.search(r"(Land Area|Site Area)[^\d]*(\d+\.?\d*)", text, re.I)

    pe_val = int(pe.group(2)) if pe else 150
    land_val = float(land.group(2)) if land else 300

    return pe_val, land_val, text


# =========================
# STRONG SUBMISSION DETECTOR
# =========================
def detect_submission_type(text):
    text = text.lower()

    def score(keywords):
        return sum(text.count(k) for k in keywords)

    vol1 = [
        "population equivalent", "pe", "site area",
        "land area", "development", "planning", "proposal"
    ]

    vol3 = [
        "sewer", "pipe", "manhole", "invert level",
        "hydraulic", "gradient", "pump", "flow velocity"
    ]

    vol4 = [
        "stp", "treatment", "aeration",
        "effluent", "bod", "sludge", "wwtp"
    ]

    scores = {
        "Vol 1 - Planning Submission": score(vol1),
        "Vol 3 - Sewer & Pump Submission": score(vol3),
        "Vol 4 - STP Submission": score(vol4)
    }

    best = max(scores, key=scores.get)
    best_score = scores[best]

    # confidence system (IMPORTANT FIX)
    total_hits = sum(scores.values())

    if total_hits == 0:
        return "Unknown", 0

    confidence = best_score / total_hits

    # stricter decision logic
    if best_score >= 2 and confidence >= 0.5:
        return best, confidence

    return "Unknown", confidence


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

    def finalize(self, confidence=1.0):

        # 🔥 confidence penalty (IMPORTANT FIX)
        if confidence < 0.6:
            self.score -= 20
            self.warnings.append("Low detection confidence - review required")

        # safety cap (prevents fake 100 scores)
        self.score = min(self.score, 95)
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
def run_vol1(e, pe, land):
    density = pe / land if land > 0 else 0

    if pe < 150:
        e.issue("PE below MSIG minimum (150)")

    if land < 250:
        e.warn("Small land area for development")

    if density > 1:
        e.warn("High development density")

    e.recommend("Verify planning compliance with authority zoning")

    return e


# =========================
# VOL 3 ENGINE
# =========================
def run_vol3(e, pipe, slope, flow):

    if pipe < 150:
        e.issue("Pipe diameter below standard (150mm)")

    if slope < 0.005:
        e.issue("Slope too low (blockage risk)")

    if slope > 0.05:
        e.issue("Slope too steep (design unrealistic)")

    if flow <= 0:
        e.issue("Invalid flow input")

    e.recommend("Check hydraulic gradient and manhole spacing")

    return e


# =========================
# VOL 4 ENGINE
# =========================
def run_vol4(e, pe, capacity):

    if capacity <= 0:
        e.issue("STP capacity not defined")

    if capacity < pe:
        e.issue("STP undersized for PE")

    if capacity > pe * 2:
        e.warn("Possible overdesign")

    e.recommend("Confirm treatment process (SBR / EA / etc)")

    return e


# =========================
# RUN ENGINE SELECTOR
# =========================
def run_engine(module, data, confidence):
    e = Engine()

    if module == "Vol 1 - Planning Submission":
        e = run_vol1(e, data["pe"], data["land"])

    elif module == "Vol 3 - Sewer & Pump Submission":
        e = run_vol3(e, data["pipe"], data["slope"], data["flow"])

    elif module == "Vol 4 - STP Submission":
        e = run_vol4(e, data["pe"], data["capacity"])

    return e.finalize(confidence)


# =========================
# UI
# =========================
st.title("🛡️ MSIG Compliance Engine (Auto Detection v4)")

file = st.file_uploader("Upload Consultant PDF", type="pdf")

if file:

    pe, land, text = extract_pdf(file)

    module, confidence = detect_submission_type(text)

    st.info(f"Detected: {module}")
    st.caption(f"Detection confidence: {confidence:.2f}")

    # ❗ if unknown → still allow but warn strongly
    if module == "Unknown":
        st.warning("Low detection confidence — manual verification recommended")

    # inputs
    pe = st.number_input("PE", value=pe)
    land = st.number_input("Land Area (m²)", value=land)

    pipe = st.number_input("Pipe Diameter", value=150)
    slope = st.number_input("Slope", value=0.01)
    capacity = st.number_input("STP Capacity", value=200)

    data = {
        "pe": pe,
        "land": land,
        "flow": (pe * SEWAGE_RATE) / 1000,
        "pipe": pipe,
        "slope": slope,
        "capacity": capacity
    }

    if st.button("Run Compliance Engine"):

        result = run_engine(module, data, confidence)

        st.subheader("RESULT")

        st.write("Risk:", result["risk"])
        st.write("Score:", result["score"])

        st.subheader("Issues")
        for i in result["issues"]:
            st.write("❌", i)

        st.subheader("Warnings")
        for w in result["warnings"]:
            st.write("⚠️", w)

        st.subheader("Recommendations")
        for r in result["recommendations"]:
            st.write("✅", r)

        with st.expander("Raw Extracted Text"):
            st.text(text)