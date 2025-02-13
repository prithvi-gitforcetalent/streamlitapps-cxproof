

import streamlit as st
from openai import OpenAI
# Ensure API key is securely stored in Streamlit secrets
api_key = "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"


# Set the title of the app
st.title("AI 1")


if not api_key:
    st.error("API key not found. Please add your OpenAI API key in Streamlit secrets.")
else:
    # Initialize the OpenAI client
    client = OpenAI(api_key=api_key)

    # Input: Dropdown with OpenAI GPT models
    models = [
        "gpt-3.5-turbo",
        # "gpt-4",
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
