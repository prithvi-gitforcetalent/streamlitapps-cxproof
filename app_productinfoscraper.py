import uuid
import streamlit as st
import shutil
import boto3
from screenshotone import Client, TakeOptions
from io import BytesIO
from openai import OpenAI
import base64
from PIL import Image
import os
import json

# Replace hardcoded keys with st.secrets
SCREENSHOTONE_ACCESS_KEY = st.secrets["SCREENSHOTONE_ACCESS_KEY"]
SCREENSHOTONE_SECRET_KEY = st.secrets["SCREENSHOTONE_SECRET_KEY"]
AWS_ACCESS_KEY = st.secrets["AWS_ACCESS_KEY"]
AWS_SECRET_KEY = st.secrets["AWS_SECRET_KEY"]
AWS_BUCKET_NAME = st.secrets["AWS_BUCKET_NAME"]
AWS_REGION = st.secrets["AWS_REGION"]
S3_BASE_URL = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/"
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Function to split long screenshot into multiple images
def split_long_screenshot(input_image):
    page_height = 1080  # Height of each page in pixels
    unique_id = str(uuid.uuid4())
    image_files = []

    # Open the image
    img = Image.open(input_image)
    print(f"Processing image: {img.width}x{img.height} pixels")

    # Calculate number of pages
    total_height = img.height
    num_pages = (total_height + page_height - 1) // page_height
    print(f"Splitting into {num_pages} pages...")

    # Split into pages
    for i in range(num_pages):
        # Calculate the crop box for this page
        top = i * page_height
        bottom = min((i + 1) * page_height, total_height)

        # Crop the image
        page = img.crop((0, top, img.width, bottom))

        # Convert to RGB mode if necessary
        if page.mode != 'RGB':
            page = page.convert('RGB')

        # Save each page as a separate image with a unique filename
        page_filename = f"screenshot_part_{unique_id}_{i + 1}.png"
        page.save(page_filename)
        image_files.append(page_filename)
        print(f"Created image: {page_filename}")

    # Clean up the original screenshot
    os.remove(input_image)

    return image_files


# Function to take screenshot
def take_screenshot(url):
    client = Client(SCREENSHOTONE_ACCESS_KEY, SCREENSHOTONE_SECRET_KEY)

    options = (
        TakeOptions.url(url)
        .format("png")
        .full_page(True)
        .block_cookie_banners(True)
        .block_chats(True)
        .timeout(30)
    )

    try:
        image = client.take(options)
        screenshot_bytes = BytesIO()
        shutil.copyfileobj(image, screenshot_bytes)
        screenshot_bytes.seek(0)

        # Generate a temporary filename for the screenshot
        temp_screenshot = f"temp_screenshot_{str(uuid.uuid4())}.png"

        with open(temp_screenshot, 'wb') as f:
            f.write(screenshot_bytes.read())

        # Call the split_long_screenshot function to create multiple images
        image_files = split_long_screenshot(temp_screenshot)

        # Upload all images to S3
        s3_urls = []
        for img_file in image_files:
            s3_url = upload_to_s3(img_file)
            if s3_url:
                s3_urls.append(s3_url)

        return s3_urls if s3_urls else None

    except Exception as e:
        print(f"❌ Screenshot capture failed: {e}")
        return None


# Function to upload file to AWS S3
def upload_to_s3(file_name):
    s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY,
                             region_name=AWS_REGION)

    try:
        s3_client.upload_file(file_name, AWS_BUCKET_NAME, file_name)
        s3_url = f"{S3_BASE_URL}{file_name}"
        os.remove(file_name)  # Clean up the file after upload
        return s3_url
    except Exception as e:
        print(f"❌ S3 upload failed: {e}")
        return None


# Function to process multiple images with AI
def process_multiple_images_with_ai(image_urls, prompt, model="gpt-4o"):
    client = OpenAI(api_key=OPENAI_API_KEY)  # Initialize the client

    all_results = []
    combined_text = ""

    # Calculate the midpoint - only process first half of images
    midpoint = len(image_urls) // 2
    # Ensure at least one image is processed
    if midpoint == 0 and len(image_urls) > 0:
        midpoint = 1

    # Use only the first half of images for processing
    images_to_process = image_urls[:midpoint]

    for i, img_url in enumerate(images_to_process):
        try:
            # Create a modified prompt to indicate which section it is
            section_prompt = f"{prompt}\n\n(This is section {i + 1} of {midpoint} from the first half of the webpage screenshot.)"

            # Make API call for this image
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": section_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": img_url}
                            }
                        ]
                    }
                ],
                max_tokens=1500
            )

            result_text = response.choices[0].message.content.strip()

            # Try to parse as JSON if the prompt expects JSON output
            try:
                if "{" in result_text and "}" in result_text:
                    result_json = json.loads(result_text)
                    if "product_raw_text" in result_json:
                        section_text = result_json["product_raw_text"]
                        if combined_text:
                            combined_text += "\n\n" + section_text
                        else:
                            combined_text = section_text
                else:
                    if combined_text:
                        combined_text += "\n\n" + result_text
                    else:
                        combined_text = result_text
            except:
                # If not valid JSON, just append the text
                if combined_text:
                    combined_text += "\n\n" + result_text
                else:
                    combined_text = result_text

            all_results.append({
                "section": i + 1,
                "image_url": img_url,
                "result": result_text
            })

        except Exception as e:
            all_results.append({
                "section": i + 1,
                "image_url": img_url,
                "error": str(e)
            })

    return {
        "combined_result": combined_text,
        "section_results": all_results
    }


# Streamlit App UI
st.title("Website Screenshot + AI Analysis 🚀")

# Layout: Screenshot on Left | AI Output on Right
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Website Screenshot 📸")

    # User Input for URL
    url = st.text_input("Enter website URL:", "https://getbild.com/")

    # Capture Screenshot Button
    if st.button("Capture Screenshot"):
        with st.spinner("Taking screenshot and splitting into multiple images..."):
            image_urls = take_screenshot(url)
            if image_urls:
                st.success(f"Screenshot captured and split into {len(image_urls)} images!")

                # Display all images in a scrollable container
                with st.container():
                    for i, img_url in enumerate(image_urls):
                        st.image(img_url, caption=f"Section {i + 1}", use_container_width=True)
                        st.markdown("---")  # Add a separator between images

                st.session_state["image_urls"] = image_urls
            else:
                st.error("Failed to capture screenshot")

with col2:
    st.subheader("AI Analysis 🧠")

    # User Input for prompt
    prompt = st.text_area("Enter your prompt:", """Objective: You are a highly specialized text parser. You receive a screenshot text capture of a product webpage. Your task is to extract key sentences / phrases relevant to the product such as product descriptions, features, and value propositions—while excluding navigation items, testimonials, pricing, or other irrelevant data.

Return Format:
{
  "product_raw_text": "<filtered sentences goes here in the original order>"
}""", height=200)

    st.info("Note: For efficiency, only the first half of the page sections will be processed with the AI.")

    if st.button("Process with AI"):
        if "image_urls" in st.session_state and st.session_state["image_urls"]:
            # Calculate how many images we'll process
            total_images = len(st.session_state["image_urls"])
            images_to_process = total_images // 2
            if images_to_process == 0 and total_images > 0:
                images_to_process = 1

            with st.spinner(f"Processing the first {images_to_process} of {total_images} images with AI..."):
                results = process_multiple_images_with_ai(st.session_state["image_urls"], prompt, "gpt-4o")
                st.session_state["ai_results"] = results

                st.success(f"✅ AI Processing Complete! (Analyzed first {images_to_process} sections)")



                # Display combined results
                st.subheader("Combined Results")
                st.text_area("Output:", results["combined_result"], height=300)

                # Add download button for results
                st.download_button(
                    "Download Results (JSON)",
                    data=json.dumps(results, indent=2),
                    file_name="analysis_results.json",
                    mime="application/json"
                )

                # Option to show individual section results
                with st.expander("Show Individual Section Results"):
                    for section in results["section_results"]:
                        st.subheader(f"Section {section['section']}")
                        if "error" in section:
                            st.error(f"Error: {section['error']}")
                        else:
                            st.text_area(f"Section {section['section']} Result:", section["result"], height=150)
        else:
            st.error("❌ Please capture a screenshot first.")
