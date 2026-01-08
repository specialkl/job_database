import streamlit as st
import google.generativeai as genai
import json
import gspread
import traceback
from prompts import JOB_EXTRACTION_PROMPT

# --- CONFIGURATION ---
st.set_page_config(page_title="Job Extractor (Direct URL)", layout="wide")

# --- AUTHENTICATION ---
try:
    gemini_key = st.secrets["GEMINI_API_KEY"]
    google_sheets_creds = st.secrets["gcp_service_account"]
except FileNotFoundError:
    st.error("Secrets not found.")
    st.stop()
except KeyError as e:
    st.error(f"Missing secret: {e}")
    st.stop()

# --- GOOGLE SHEETS FUNCTION ---
def save_to_google_sheets(data_dict):
    try:
        client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        sheet_name = "2026 Job Search" 
        sheet = client.open(sheet_name).sheet1
        row = [str(data_dict.get(k, "")) for k in data_dict.keys()]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error("❌ Google Sheets Error")
        st.write(f"Error: {e}")
        return False

# --- MAIN APP UI ---
st.title("🤖 Job Extractor (Direct URL Mode)")
st.warning("⚠️ Note: The Gemini API cannot 'browse' the web. It will only infer details from the words inside the URL string itself.")

target_url = st.text_input("Paste Job URL:", placeholder="https://www.linkedin.com/jobs/view/...")

if st.button("Extract & Save", type="primary"):
    if not target_url:
        st.warning("Please paste a URL.")
    else:
        status = st.empty()
        try:
            status.info("🧠 Asking Gemini to analyze the URL string...")
            
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(
                'gemini-2.5-flash', # Or 'gemini-1.5-flash'
                system_instruction=JOB_EXTRACTION_PROMPT
            )
            
            # We strictly pass the URL string, no page content
            prompt_content = f"Here is the job link:\n{target_url}"
            
            response = model.generate_content(
                contents=prompt_content,
                generation_config={"response_mime_type": "application/json"}
            )
            
            data = json.loads(response.text)
            
            # Show the result
            st.subheader("Extraction Result")
            st.json(data)
            
            # Save
            status.info("💾 Saving...")
            if save_to_google_sheets(data):
                status.success("✅ Saved to Sheets")
                
        except Exception as e:
            st.error(f"Error: {e}")
            st.write(traceback.format_exc())