import streamlit as st
import fitz
import re

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="MSIG Checker Lite", layout="wide")

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
# LOGIC
# =========================
def get_class(pe):
    for c, mn, mx in STP_CLASSES:
        if mn <= pe <= mx:
            return c
    return "Unknown"


def land_check(pe, land, stp_class):
    if stp_class != 1:
        return None, "Manual check required"

    ref_pe = min(CLASS_1_LAND.keys(), key=lambda x: abs(x - pe))
    req = CLASS_1_LAND[ref_pe]

    if land >= req:
        return True, req
    return False, req


# =========================
# UI
# =========================
st.title("🛡️ MSIG Volume 1 Checker (Lite)")

# 🔴 ONLY ONE UPLOADER (IMPORTANT FIX)
file = st.file_uploader(
    "Upload Consultant Proposal (PDF)",
    type="pdf",
    key="single_upload"
)

# =========================
# MAIN
# =========================
if file:

    pe, land, text = extract_pdf(file)

    if pe is None:
        pe = 150
    if land is None:
        land = 0.0

    col1, col2 = st.columns(2)

    # =====================
    # INPUT / OUTPUT LEFT
    # =====================
    with col1:
        st.subheader("📋 Extracted Data")

        pe = st.number_input("PE", value=pe)
        land = st.number_input("Land Area (m²)", value=land)

        flow = (pe * SEWAGE_RATE) / 1000
        st.metric("Flow (m³/d)", f"{flow:.2f}")

    # =====================
    # COMPLIANCE RIGHT
    # =====================
    with col2:
        st.subheader("✅ Compliance")

        stp_class = get_class(pe)
        st.write("Class:", stp_class)

        status, req = land_check(pe, land, stp_class)

        if status is True:
            st.success(f"Land OK (Min {req} m²)")
        elif status is False:
            st.error(f"Land FAIL (Min {req} m²)")
        else:
            st.info(req)

    with st.expander("Raw Text"):
        st.text(text)
