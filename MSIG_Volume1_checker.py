import streamlit as st
import pandas as pd
import openai
import pdfplumber

st.set_page_config(page_title="MSIG PDF Volume Guider", layout="wide")
st.title("📄 MSIG PDF Volume Guider")

# Sidebar for API Key
with st.sidebar:
    api_key = st.text_input("Enter OpenAI API Key", type="password")
    if api_key:
        openai.api_key = api_key

uploaded_file = st.file_uploader("Upload MSIG PDF Report", type=['pdf'])

if uploaded_file:
    with st.spinner("Extracting data from PDF..."):
        all_text = ""
        tables_data = []
        
        # Open the PDF using pdfplumber
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                # Extract text
                all_text += page.extract_text() + "\n"
                # Extract tables (if any)
                table = page.extract_table()
                if table:
                    tables_data.append(pd.DataFrame(table))

        st.success("PDF Processed!")

    # Layout: Show extracted text summary
    with st.expander("View Extracted Text Summary"):
        st.write(all_text[:1000] + "...") # Show first 1000 characters

    # AI Chat Interface
    user_question = st.text_input("Ask the Guider about this PDF volume:")

    if user_question:
        if not api_key:
            st.error("Please enter your API Key in the sidebar.")
        else:
            with st.spinner("The AI is reading the report..."):
                # We feed the extracted text to the AI
                # Note: For very long PDFs, we usually send the most relevant chunks
                prompt = f"""
                You are an MSIG Volume Guider. Below is the content of an MSIG PDF report.
                Please answer the question based strictly on this data.

                REPORT CONTENT:
                {all_text[:3000]} 

                USER QUESTION: 
                {user_question}
                """

                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-4-turbo-preview",
                        messages=[{"role": "system", "content": "You are a professional insurance analyst."},
                                  {"role": "user", "content": prompt}]
                    )
                    st.markdown("### Guider Analysis:")
                    st.write(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"AI Error: {e}")
