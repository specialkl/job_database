import streamlit as st
import google.generativeai as genai
import requests
import json
import pandas as pd
import os
from dotenv import load_dotenv

# Import your prompt
from prompts import JOB_EXTRACTION_PROMPT

# --- CONFIGURATION ---
st.set_page_config(page_title="Job Extractor AI", layout="wide")

# 1. Load Environment Variables (Securely)
load_dotenv() # This loads the .env file

# 2. Try to get the key from the environment
env_api_key = os.getenv("GEMINI_API_KEY")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Logic: If key is in .env, use it. Otherwise, ask for it.
    if env_api_key:
        st.success("✅ API Key loaded from .env")
        api_key = env_api_key
    else:
        api_key = st.text_input("Gemini API Key", type="password")
        st.caption("Tip: Add GEMINI_API_KEY to a .env file to skip this step.")
        
    st.markdown("[Get Key](https://aistudio.google.com/app/apikey)")
    st.divider()
    st.caption("Powered by Gemini 1.5 & Jina Reader")

# --- MAIN APP ---
st.title("🤖 URL-to-JSON Job Extractor")
st.markdown("Paste a job link (LinkedIn, Greenhouse, Lever, etc.) to extract structured data.")

target_url = st.text_input("Paste Job URL:", placeholder="https://www.linkedin.com/jobs/view/...")

if st.button("Extract Data", type="primary"):
    if not api_key:
        st.error("⚠️ Missing API Key. Please add it to .env or the sidebar.")
    elif not target_url:
        st.warning("⚠️ Please paste a URL first.")
    else:
        status_text = st.empty()
        
        try:
            # STEP 1: Scrape via Jina Reader
            status_text.info("🕷️ Fetching and parsing page content...")
            jina_url = f"https://r.jina.ai/{target_url}"
            scrape_response = requests.get(jina_url)
            
            if scrape_response.status_code != 200:
                st.error(f"Failed to fetch URL. Status: {scrape_response.status_code}")
                st.stop()
                
            job_text_content = scrape_response.text
            
            if "Sign In" in job_text_content[:500] and "LinkedIn" in job_text_content[:500]:
                st.warning("⚠️ LinkedIn might be blocking this request. Try a public/guest link if possible.")

            # STEP 2: Send to Gemini
            status_text.info("🧠 Analyzing with Gemini...")
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            user_message = f"""
            URL: {target_url}
            CONTENT:
            {job_text_content}
            """
            
            response = model.generate_content(
                contents=user_message,
                system_instruction=JOB_EXTRACTION_PROMPT,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # STEP 3: Display Results
            status_text.success("✅ Extraction Complete!")
            data = json.loads(response.text)
            
            tab1, tab2 = st.tabs(["📊 Table View", "📝 Raw JSON"])
            
            with tab1:
                df = pd.DataFrame([data])
                if 'raw_posting_text_verbatim_plain' in df.columns:
                    display_df = df.drop(columns=['raw_posting_text_verbatim_plain'])
                else:
                    display_df = df
                st.dataframe(display_df.T, use_container_width=True, height=600)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "job_data.csv", "text/csv")
                
            with tab2:
                st.json(data)

        except Exception as e:
            st.error(f"An error occurred: {e}")