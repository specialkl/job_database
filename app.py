import streamlit as st
import google.generativeai as genai
import requests
import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials # <--- NEW LIBRARY
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

# --- GOOGLE SHEETS FUNCTION ---
def save_to_google_sheets(data_dict):
    # The modern scopes (Google Auth uses slightly different URLs sometimes, but these are standard)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # Convert Streamlit secrets to a standard Python dictionary
        credentials_dict = dict(st.secrets["gcp_service_account"])
        
        # Create credentials object
        creds = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scopes
        )
        
        # Authorize gspread
        client = gspread.authorize(creds)
        
        # Open the sheet
        sheet_name = "Job Hunt Database"  # Make sure this matches exactly!
        sheet = client.open(sheet_name).sheet1
        
        # Prepare row data
        row = [str(data_dict.get(k, "")) for k in data_dict.keys()]
        
        # Append
        sheet.append_row(row)
        return True
        
    except Exception as e:
        # Detailed error logging
        st.error(f"Google Sheets Error: {e}")
        # If it's a specific API error, try to print the response body
        if hasattr(e, 'response'):
             st.write(getattr(e, 'response', 'No response text'))
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