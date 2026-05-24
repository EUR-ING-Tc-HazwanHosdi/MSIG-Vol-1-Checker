import streamlit as st
import pandas as pd
import openai
import pdfplumber

# Set page layout
st.set_page_config(page_title="MSIG Volume Guider", layout="wide", page_icon="📄")

# App Header
st.title("📄 MSIG Volume Guider AI")
st.markdown("Upload MSIG PDF reports to analyze volume, premiums, and performance.")

# 1. Sidebar - Setup & Security
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Enter OpenAI API Key", type="password", help="Get your key from platform.openai.com")
    if api_key:
        openai.api_key = api_key
    
    st.divider()
    st.info("This AI processes your PDF text and tables to guide you through MSIG volume reports.")

# 2. File Uploader
uploaded_file = st.file_uploader("Upload MSIG PDF Report", type=['pdf'])

if uploaded_file:
    with st.spinner("Extracting data from MSIG PDF..."):
        all_text = ""
        table_summary = ""
        
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                # Loop through pages (limit to first 15 pages for speed/token limits)
                for i, page in enumerate(pdf.pages[:15]):
                    # Extract Text
                    page_text = page.extract_text()
                    if page_text:
                        all_text += f"\n--- Page {i+1} ---\n" + page_text
                    
                    # Extract Tables
                    tables = page.extract_tables()
                    for table in tables:
                        # Convert list-table to a simple string format for AI
                        table_summary += f"\n[Table on Page {i+1}]\n"
                        for row in table:
                            # Filter out None values and join
                            table_summary += " | ".join([str(item) for item in row if item is not None]) + "\n"

            st.success(f"Successfully processed {len(pdf.pages)} pages!")
            
        except Exception as e:
            st.error(f"Error reading PDF: {e}")

    # 3. User Interaction
    st.divider()
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Data Preview")
        with st.expander("Show extracted text and tables"):
            st.text(all_text[:2000] + "...") # Preview first 2000 chars

    with col2:
        st.subheader("Ask the Guider")
        query = st.text_area("What would you like to know about this MSIG volume?", 
                             placeholder="e.g., What is the total GWP for the Motor department?")

        if st.button("Analyze Now"):
            if not api_key:
                st.warning("Please enter an OpenAI API Key in the sidebar.")
            elif not query:
                st.warning("Please enter a question.")
            else:
                with st.spinner("AI is analyzing your report..."):
                    # Combine text and table data for the AI context
                    full_context = f"TEXT CONTENT:\n{all_text[:4000]}\n\nTABLE CONTENT:\n{table_summary[:3000]}"
                    
                    try:
                        response = openai.ChatCompletion.create(
                            model="gpt-4-turbo-preview",
                            messages=[
                                {"role": "system", "content": "You are a specialized MSIG Volume Analyst. You interpret insurance data, premiums, and volumes from PDF reports. Be precise and point out specific numbers."},
                                {"role": "user", "content": f"Based on this report:\n{full_context}\n\nQuestion: {query}"}
                            ],
                            temperature=0
                        )
                        st.markdown("### 🤖 Guider Analysis:")
                        st.info(response.choices[0].message.content)
                    except Exception as e:
                        st.error(f"AI Error: {e}")
