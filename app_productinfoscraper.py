import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import re

def fetch_html(url):
    """Fetch HTML content from a URL using Cloudscraper."""
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return None



def extract_product_info(html_content):
    """Extracts title, meta description, and text from <p>, <h1>, <h2>, <h3>, and <div> tags while removing duplicates."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract Page Title
    title = soup.title.string.strip() if soup.title else "N/A"

    # Extract Meta Description (fixing potential NoneType issue)
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc_tag.get("content", "N/A").strip() if meta_desc_tag else "N/A"

    extracted_content = []
    seen_texts = set()  # Track unique texts to avoid duplicates

    # Extract text from <h1>, <h2>, <h3>, <p>, and <div> tags
    for tag in soup.find_all(["h1", "h2", "h3", "p", "div"]):
        text = tag.get_text(" ", strip=True)  # Ensure text within the same tag stays on one line
        if text and text not in seen_texts:  # Ensure uniqueness
            seen_texts.add(text)
            extracted_content.append(text)

    # Limit extracted content to the first 2000 characters
    extracted_text = "\n".join(extracted_content)[:20000]

    return {
        "title": title if title else "N/A",
        "meta_desc": meta_desc if meta_desc else "N/A",
        "extracted_content": extracted_text if extracted_text else "No content extracted"
    }



st.set_page_config(page_title="Product Page Scraper", layout="wide")

st.title("🕵️‍♂️ Product Page Scraper")
st.write("Enter a product URL and name to extract useful information.")

# User Inputs
product_url = st.text_input("🔗 Enter the product page URL:")
product_name = st.text_input("📌 Enter the product/module name:")

if st.button("Scrape Product Info"):
    if product_url:
        st.info(f"Fetching product details for: **{product_name}**")

        # Fetch and process HTML
        html_content = fetch_html(product_url)
        if html_content:
            product_info = extract_product_info(html_content)

            # Display results
            st.subheader("📖 Page Title")
            st.write(product_info["title"])  # Use correct key

            st.subheader("📝 Page Meta Data")
            st.write(product_info["meta_desc"])  # Use correct key

            st.subheader("📜 Page Content")
            st.text_area("Extracted Content", product_info["extracted_content"], height=300)  # Use correct key




        else:
            st.error("Failed to fetch the page. Please check the URL and try again.")
    else:
        st.warning("Please enter a valid URL.")

