import streamlit as st
import fitz  # PyMuPDF
import re

# --- MSIG DATA & LOGIC ---
STP_CLASSES = [
    {"Class": 1, "Min PE": 150, "Max PE": 1000},
    {"Class": 2, "Min PE": 1001, "Max PE": 5000},
    {"Class": 3, "Min PE": 5001, "Max PE": 20000},
    {"Class": 4, "Min PE": 20001, "Max PE": float('inf')}
]

# [span_1](start_span)Table 5-1: Land Requirements for Class 1 (m2)[span_1](end_span)
CLASS_1_LAND = {150: 283, 200: 360, 500: 664, 1000: 1016}

def extract_data_from_pdf(file):
    """Simple extraction logic to find key terms in the consultant's PDF."""
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    
    # Simple RegEx to find numbers near keywords (e.g., "PE: 500")
    pe_match = re.search(r"(?:PE|Population Equivalent)[:\s]*(\d+,?\d*)", text, re.I)
    land_match = re.search(r"(?:Land Area|Site Area)[:\s]*(\d+,?\d*)", text, re.I)
    
    extracted_pe = int(pe_match.group(1).replace(',', '')) if pe_match else None
    extracted_land = float(land_match.group(1).replace(',', '')) if land_match else None
    
    return extracted_pe, extracted_land, text

# --- STREAMLIT UI ---
st.title("Consultant Proposal PDF Checker")
st.markdown("Automated validation against **MSIG Vol 1 (2025)** standards.")

uploaded_file = st.file_uploader("Upload Consultant Proposal (PDF)", type="pdf")

if uploaded_file:
    with st.spinner("Analyzing PDF..."):
        pe, land, full_text = extract_data_from_pdf(uploaded_file)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Extracted Parameters")
        final_pe = st.number_input("Confirmed PE", value=pe if pe else 150)
        final_land = st.number_input("Confirmed Land Area (m²)", value=land if land else 0.0)
        
        # [span_2](start_span)[span_3](start_span)Mandatory MSIG Sewage Generation Rate[span_2](end_span)[span_3](end_span)
        gen_rate = 210 
        avg_flow = (final_pe * gen_rate) / 1000
        st.info(f"Calculated Flow: **{avg_flow:.2f} m³/day** (based on 210L/p/d)")

    with col2:
        st.subheader("MSIG Compliance Results")
        
        # 1. [span_4](start_span)Classification Check[span_4](end_span)
        stp_class = next((c["Class"] for c in STP_CLASSES if c["Min PE"] <= final_pe <= c["Max PE"]), None)
        st.write(f"**STP Classification:** Class {stp_class}")
        
        # 2. [span_5](start_span)Land Area Check (Table 5-1 Example)[span_5](end_span)
        if stp_class == 1:
            # Find closest PE in our reference table
            req_land = min(CLASS_1_LAND.values(), key=lambda x: abs(x - final_pe)) 
            if final_land >= req_land:
                st.success(f"✅ Land Area Compliant (Required: {req_land}m²)")
            else:
                st.error(f"❌ Land Area Insufficient (Required: {req_land}m²)")
        
        # 3. Mandatory Document Search
        st.write("**Mandatory Component Search:**")
        docs = {
            "Whole Life Cycle Cost (WLCC)": ["WLCC", "Life Cycle Cost", "CBA"],
            "GHG/Carbon Calculation": ["GHG", "Carbon Footprint", "CO2"],
            "Multi-Criteria Analysis (MCA)": ["MCA", "Multi Criteria"]
        }
        
        for doc_name, keywords in docs.items():
            found = any(key.lower() in full_text.lower() for key in keywords)
            if found:
                st.write(f"✅ {doc_name}: Found in PDF")
            else:
                st.warning(f"⚠️ {doc_name}: Not detected")

    with st.expander("View Extracted Text"):
        st.write(full_text)
)