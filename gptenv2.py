

import streamlit as st
from openai import OpenAI


# Set the title of the app
st.title("AI 2")

# Get API key from Streamlit secrets
api_key = st.secrets["openai"]["api_key2"] if "openai" in st.secrets else None


if not api_key:
    st.error("API key not found. Please add your OpenAI API key in Streamlit secrets.")
else:
    # Initialize the OpenAI client
    client = OpenAI(api_key=api_key)

    # Input: Dropdown with OpenAI GPT models
       models = [
        "gpt-3.5-turbo",
        "gpt-4o-mini",
        "gpt-4o",
        # "gpt-4",st
        # "gpt-4-turbo",
        # "gpt-4-32k",
        # "gpt-4-1106-preview"
    ]
    selected_model = st.selectbox("Choose a model", models)

    # Input: Big text box for the prompt
    prompt = st.text_area("Enter your prompt here", height=150)

    # Placeholder for the response
    response_placeholder = st.empty()

    # Button to generate the response
    if st.button("Generate Response"):
        if prompt.strip() == "":
            st.warning("Please enter a prompt.")
        else:
            try:
                # Call OpenAI API with only the user's prompt
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=[{"role": "user", "content": prompt}]  # No system message
                )

                # Extract the response content
                response_text = response.choices[0].message.content

                # Display the response in the text area
                response_placeholder.text_area("Response", value=response_text, height=150)

            except Exception as e:
                st.error(f"An error occurred: {e}")
