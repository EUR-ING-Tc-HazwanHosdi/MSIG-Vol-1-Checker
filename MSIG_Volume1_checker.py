import streamlit as st
import fitz  # PyMuPDF
import re

# --- CONFIGURATION & MSIG DATA ---
st.set_page_config(page_title="MSIG Vol 1 Checker", layout="wide")

STP_CLASSES = [
    {"Class": 1, "Min": 150, "Max": 1000},
    {"Class": 2, "Min": 1001, "Max": 5000},
    {"Class": 3, "Min": 5001, "Max": 20000},
    {"Class": 4, "Min": 20001, "Max": float('inf')}
]

# Land Requirements Table 5-1 (Simplified for Class 1)
CLASS_1_LAND = {150: 283, 200: 360, 500: 664, 1000: 1016}

def extract_data(file):
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    
    # Regex to find PE and Land Area
    pe_pattern = re.search(r"(?:PE|Population Equivalent)[:\s]*(\d+,?\d*)", text, re.I)
    land_pattern = re.search(r"(?:Land Area|Site Area)[:\s]*(\d+,?\d*)", text, re.I)
    
    extracted_pe = int(pe_pattern.group(1).replace(',', '')) if pe_pattern else None
    extracted_land = float(land_pattern.group(1).replace(',', '')) if land_pattern else None
    
    return extracted_pe, extracted_land, text

# --- UI INTERFACE ---
st.title("🛡️ MSIG Vol 1 Proposal Validator")
st.markdown("Automated compliance check for **Sewerage Planning (PDC 1)** submissions.")

uploaded_file = st.file_uploader("Upload Consultant Proposal (PDF)", type="pdf")

if uploaded_file:
    pe_val, land_val, full_text = extract_data(uploaded_file)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Extracted Data")
        # Ensure values are not None for the number_input
        pe = st.number_input("Population Equivalent (PE)", value=pe_val if pe_val else 150)
        land = st.number_input("Proposed Land Area (m²)", value=land_val if land_val else 0.0)
        
        # Calculation based on MSIG 210L/p/d standard
        avg_flow = (pe * 210) / 1000
        st.metric("Design Average Flow", f"{avg_flow:.2f} m³/d")

    with col2:
        st.subheader("✅ Compliance Audit")
        
        # 1. Class Check
        stp_class = next((c["Class"] for c in STP_CLASSES if c["Min"] <= pe <= c["Max"]), "N/A")
        st.write(f"**STP Classification:** Class {stp_class}")
        
        # 2. Land Check
        if stp_class == 1:
            # Find closest reference land area
            req_land = min(CLASS_1_LAND.values(), key=lambda x: abs(x - pe)) 
            if land >= req_land:
                st.success(f"Land Area: PASS (Min: {req_land}m²)")
            else:
                st.error(f"Land Area: FAIL (Min: {req_land}m²)")
        else:
            st.info("Manual check required for Class 2-4 Land Requirements.")

        # 3. Mandatory Document Keywords Search
        st.write("**Required Document Check:**")
        checklist = {
            "Whole Life Cycle Cost (WLCC)": ["WLCC", "Life Cycle", "CBA"],
            "GHG/Carbon Calculation": ["GHG", "Carbon", "CO2"],
            "Multi-Criteria Analysis": ["MCA", "Multi Criteria"]
        }
        
        for item, keys in checklist.items():
            if any(k.lower() in full_text.lower() for k in keys):
                st.write(f"✔️ {item}: Detected")
            else:
                st.write(f"❌ {item}: **Missing**")

    with st.expander("Show Raw Extracted Text"):
        st.text(full_text)

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
