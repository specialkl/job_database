import streamlit as st
import google.generativeai as genai
import requests
import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials # <--- NEW LIBRARY
from prompts import JOB_EXTRACTION_PROMPT
import traceback

# --- CONFIGURATION ---
st.set_page_config(page_title="Job Extractor AI", layout="wide")

# --- AUTHENTICATION SETUP ---
# We use st.secrets for Cloud deployment
# If running locally, you must have a .streamlit/secrets.toml file
try:
    gemini_key = st.secrets["GEMINI_API_KEY"]
    # We expect the entire JSON content from Google Cloud to be in secrets
    google_sheets_creds = st.secrets["gcp_service_account"]
except FileNotFoundError:
    st.error("Secrets not found. If running locally, check .streamlit/secrets.toml")
    st.stop()

# --- GOOGLE SHEETS FUNCTION
def save_to_google_sheets(data_dict):
    try:
        # 1. Use gspread's internal helper to handle the secrets dict directly
        # This automatically handles scopes and tokens for you.
        client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        
        # 2. Open the sheet
        sheet_name = "2026 Job Search" 
        sheet = client.open(sheet_name).sheet1
        
        # 3. Prepare row
        row = [str(data_dict.get(k, "")) for k in data_dict.keys()]
        
        # 4. Append
        sheet.append_row(row)
        return True

    except Exception as e:
        st.error("❌ Google Sheets Error")
        # This will print the FULL error trace so we can see exactly what's wrong
        st.code(traceback.format_exc()) 
        return False

# --- MAIN APP ---
st.title("🤖 Job Extractor")

target_url = st.text_input("Paste Job URL:")

if st.button("Extract & Save", type="primary"):
    if not target_url:
        st.warning("Please paste a URL.")
    else:
        status = st.empty()
        status.info("Parsing Job...")
        
        try:
            # 1. Jina Reader
            jina_url = f"https://r.jina.ai/{target_url}"
            resp = requests.get(jina_url)
            job_text = resp.text

            # 2. Gemini
            status.info("Asking Gemini...")
            genai.configure(api_key=gemini_key)

            model = genai.GenerativeModel(
                            'gemini-2.5-flash',
                            system_instruction=JOB_EXTRACTION_PROMPT
                        )

            response = model.generate_content(
                            contents=f"URL: {target_url}\nCONTENT:\n{job_text}",
                            generation_config={"response_mime_type": "application/json"}
                        )
            
            data = json.loads(response.text)
            
            # 3. Save to Sheets
            status.info("Saving to Google Sheets...")
            if save_to_google_sheets(data):
                status.success("✅ Success! Data saved to Google Sheets.")
                st.json(data)
            
        except Exception as e:
            st.error(f"Error: {e}")