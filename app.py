import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import os

# Set page config
st.set_page_config(page_title="BOM Extractor", layout="wide")

st.title("BOM Extractor MVP")
st.markdown("Upload a product diagram to extract a Bill of Materials.")

# Initialize session state for API key
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# Get API key from sidebar with save functionality
with st.sidebar:
    st.subheader("🔑 API Key Setup")
    
    # Show current status
    if st.session_state.api_key:
        st.success("✅ API Key saved!")
        if st.button("Clear API Key"):
            st.session_state.api_key = ""
            st.rerun()
    else:
        key_input = st.text_input(
            "Enter Google API Key", 
            type="password",
            placeholder="Paste your key here..."
        )
        
        if st.button("💾 Save Key", type="primary"):
            if key_input:
                st.session_state.api_key = key_input
                st.rerun()
            else:
                st.error("Please enter a key first.")
        
        st.markdown("[Get your API key here](https://aistudio.google.com/app/apikey)")

# Use the saved key
api_key = st.session_state.api_key

# File Uploader
uploaded_file = st.file_uploader("Upload an image (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_container_width=True)

    if st.button("Generate BOM"):
        if not api_key:
            st.error("Please enter and save your API Key in the sidebar first.")
        else:
            try:
                # Configure Gemini
                genai.configure(api_key=api_key)
                # User requested specific model
                model = genai.GenerativeModel('models/gemini-2.5-flash')

                # Prepare the prompt
                prompt = """
                Analyze the provided product diagram/image. 
                Identify all parts, callout numbers, and quantities visible or implied.
                Return ONLY a raw JSON array of objects. 
                Each object must have the following fields:
                - "id": The callout number or identifier from the diagram (string).
                - "part_name": The name of the part (string).
                - "quantity": The count of this part (integer).
                - "description": A brief description of the part or its function if evident (string).

                Do not include any markdown formatting (like ```json ... ```). Just the raw JSON array.
                If no parts are found, return an empty array [].
                """

                with st.spinner("Analyzing image..."):
                    response = model.generate_content([prompt, image])
                    response_text = response.text.strip()
                    
                    # Clean up response if it contains markdown code blocks
                    if response_text.startswith("```json"):
                        response_text = response_text[7:]
                    if response_text.startswith("```"):
                        response_text = response_text[3:]
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]
                    
                    response_text = response_text.strip()

                    try:
                        data = json.loads(response_text)
                        
                        if isinstance(data, list):
                            df = pd.DataFrame(data)
                            
                            if not df.empty:
                                st.success("BOM Generated Successfully!")
                                st.dataframe(df, use_container_width=True)

                                # Download Buttons
                                csv = df.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    label="Download CSV",
                                    data=csv,
                                    file_name="bom.csv",
                                    mime="text/csv",
                                )

                                json_str = df.to_json(orient="records", indent=2)
                                st.download_button(
                                    label="Download JSON",
                                    data=json_str,
                                    file_name="bom.json",
                                    mime="application/json",
                                )
                            else:
                                st.warning("No data found in the response.")
                        else:
                            st.error("Model returned invalid JSON format (not a list).")
                            st.text_area("Raw Response", response_text)

                    except json.JSONDecodeError:
                        st.error("Failed to parse JSON response.")
                        st.text_area("Raw Response", response_text)

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
