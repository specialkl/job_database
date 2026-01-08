import streamlit as st
import google.generativeai as genai
import requests
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from prompts import JOB_EXTRACTION_PROMPT

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

# --- GOOGLE SHEETS SETUP ---
def save_to_google_sheets(data_dict):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Authenticate using the dictionary from secrets, not a file path
    creds = ServiceAccountCredentials.from_json_keyfile_dict(google_sheets_creds, scope)
    client = gspread.authorize(creds)
    
    # Open the sheet - MAKE SURE THIS NAME MATCHES EXACTLY
    sheet_name = "Job Hunt Database" 
    try:
        sheet = client.open(sheet_name).sheet1
        # Convert values to string to avoid JSON errors in Sheets
        row = [str(data_dict.get(k, "")) for k in data_dict.keys()]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Google Sheets Error: {e}")
        return False

# --- MAIN APP ---
st.title("🤖 Job Extractor (Connected to Sheets)")

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
                            'gemini-1.5-flash-latest',
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