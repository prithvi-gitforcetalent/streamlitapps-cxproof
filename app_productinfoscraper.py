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
import cloudscraper
from bs4 import BeautifulSoup
import logging




SCREENSHOTONE_ACCESS_KEY = st.secrets["SCREENSHOTONE_ACCESS_KEY"]
SCREENSHOTONE_SECRET_KEY = st.secrets["SCREENSHOTONE_SECRET_KEY"]
AWS_ACCESS_KEY = st.secrets["AWS_ACCESS_KEY"]
AWS_SECRET_KEY = st.secrets["AWS_SECRET_KEY"]
AWS_BUCKET_NAME = st.secrets["AWS_BUCKET_NAME"]
AWS_REGION = st.secrets["AWS_REGION"]
S3_BASE_URL = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/"
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]



def get_page_metadata(url):
    """Extract title and metadata from a webpage with multiple request strategies"""
    logging.info(f"Starting metadata extraction for: {url}")

    # Strategy 1: Standard cloudscraper approach
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

        response = scraper.get(url, timeout=15, allow_redirects=True)
        logging.info(f"Strategy 1 status code: {response.status_code}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string.strip() if soup.title else ""

            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                description = meta_desc.get("content").strip()

            if not description:
                og_desc = soup.find("meta", attrs={"property": "og:description"})
                if og_desc and og_desc.get("content"):
                    description = og_desc.get("content").strip()

            if title or description:
                return {"title": title, "description": description}
    except Exception as e:
        logging.error(f"Strategy 1 failed: {str(e)}")

    # Strategy 2: Try with standard requests library and different user agent
    if "strategy_1_failed" or response.status_code != 200:
        try:
            import requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/'  # Sometimes helps bypass restrictions
            }

            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            logging.info(f"Strategy 2 status code: {response.status_code}")

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                title = soup.title.string.strip() if soup.title else ""

                description = ""
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    description = meta_desc.get("content").strip()

                if not description:
                    og_desc = soup.find("meta", attrs={"property": "og:description"})
                    if og_desc and og_desc.get("content"):
                        description = og_desc.get("content").strip()

                if title or description:
                    return {"title": title, "description": description}
        except Exception as e:
            logging.error(f"Strategy 2 failed: {str(e)}")

    # Strategy 3: Try mobile user agent
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9'
        }

        import requests
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        logging.info(f"Strategy 3 status code: {response.status_code}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string.strip() if soup.title else ""

            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                description = meta_desc.get("content").strip()

            if not description:
                og_desc = soup.find("meta", attrs={"property": "og:description"})
                if og_desc and og_desc.get("content"):
                    description = og_desc.get("content").strip()

            if title or description:
                return {"title": title, "description": description}
    except Exception as e:
        logging.error(f"Strategy 3 failed: {str(e)}")

    # If all strategies fail, return error
    return {
        "title": "Unable to access page content",
        "description": "This page appears to be blocking automated access",
        "error": "All access strategies failed"
    }


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

        metadata = get_page_metadata(url)

        # Store metadata in the result
        result = {
            "image_urls": s3_urls,
            "metadata": metadata
        }

        return result if s3_urls else None


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
def process_multiple_images_with_ai(image_urls, page_metadata, prompt, model="gpt-4o"):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])  # Initialize the client

    all_results = []
    combined_text = ""

    total_images = len(image_urls)

    # Determine how many images to process based on the new logic
    if total_images >= 9:
        # If 9+ images, process half
        images_to_process = total_images // 2
    elif total_images >= 6:
        # If 6-8 images, process exactly 6
        images_to_process = 6
    else:
        # If 5 or fewer, process all of them
        images_to_process = total_images

    # Use only the determined number of images for processing
    images_to_process_list = image_urls[:images_to_process]

    # Add metadata to the start of each prompt
    metadata_text = f"Page Title: {page_metadata['title']}\nPage Description: {page_metadata['description']}\n\n"

    for i, img_url in enumerate(images_to_process_list):
        try:
            # Create a modified prompt to indicate which section it is
            section_prompt = f"{metadata_text}{prompt}\n\n(This is section {i + 1} of {images_to_process} from the webpage screenshot.)"


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


st.set_page_config(
    page_title="Product Info Scraper"
)


st.title("Website Screenshot + AI Analysis 🚀")
logging.basicConfig(level=logging.INFO)
logging.info("App loading...")


# Layout: Screenshot on Left | AI Output on Right
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Website Screenshot 📸")

    # User Input for URL
    url = st.text_input("Enter website URL:", "https://getbild.com/")

    # Capture Screenshot Button
    if st.button("Capture Screenshot"):
        with st.spinner("Taking screenshot and splitting into multiple images..."):
            try:
                result = take_screenshot(url)
                if result and result["image_urls"]:
                    image_urls = result["image_urls"]
                    metadata = result["metadata"]

                    logging.info(f"Metadata returned is: {metadata}")
                    st.success(f"Screenshot captured and split into {len(image_urls)} images!")
                    # Display page metadata
                    st.subheader("Page Information")
                    # st.write(f"**Title:** {metadata['title']}")
                    # st.write(f"**Description:** {metadata['description']}")

                    st.write(f"**Title:** {metadata.get('title', 'Not available')}")
                    st.write(f"**Description:** {metadata.get('description', 'Not available')}")


                    # Display all images in a scrollable container
                    with st.container():
                        for i, img_url in enumerate(image_urls):
                            st.image(img_url, caption=f"Section {i + 1}", use_container_width=True)
                            st.markdown("---")  # Add a separator between images
                    # Store in session state
                    st.session_state["image_urls"] = image_urls
                    st.session_state["page_metadata"] = metadata
                else:
                    # Check if there's an error message in the result
                    error_msg = result.get("error", "Unknown error") if result else "Unknown error"
                    st.error(f"Failed to capture screenshot: {error_msg}")
            except Exception as e:
                st.error(f"Failed to capture screenshot: {str(e)}")

with col2:
    st.subheader("AI Analysis 🧠")

    # User Input for prompt
    prompt = st.text_area("Enter your prompt:", """Objective: You are a highly specialized text parser. You receive a screenshot text capture of a product webpage. Your task is to extract key sentences / phrases relevant to the product such as product descriptions, features, and value propositions—while excluding navigation items, testimonials, pricing, or other irrelevant data.

Return Format:
{
  "product_raw_text": "<filtered sentences goes here in the original order>"
}""", height=200)

    st.info(
        "Note: For efficiency, pages with 9+ sections will only process the first half. Pages with 6-8 sections will process up to 6 sections. Pages with 5 or fewer sections will process all sections.")

    if st.button("Process with AI"):
        if "image_urls" in st.session_state and st.session_state["image_urls"]:
            # Get the total number of images
            total_images = len(st.session_state["image_urls"])
            page_metadata = st.session_state.get("page_metadata", {"title": "", "description": ""})

            # Determine how many images to process based on the same logic
            if total_images >= 9:
                # If 9+ images, process half
                images_to_process = total_images // 2
            elif total_images >= 6:
                # If 6-8 images, process exactly 6
                images_to_process = 6
            else:
                # If 5 or fewer, process all of them
                images_to_process = total_images

            with st.spinner(f"Processing {images_to_process} of {total_images} images with AI..."):
                results = process_multiple_images_with_ai(st.session_state["image_urls"], page_metadata, prompt,
                                                          "gpt-4o")
                st.session_state["ai_results"] = results

                st.success(f"✅ AI Processing Complete! (Analyzed {images_to_process} sections)")



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
