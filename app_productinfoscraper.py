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
    """Extract relevant product information including title, metadata, and cleaned page content."""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract Page Title
    title = soup.title.string.strip() if soup.title else None

    # Extract Meta Description
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc_tag["content"].strip() if meta_desc_tag else None

    # Make a copy of the soup for content extraction
    content_soup = BeautifulSoup(str(soup), 'html.parser')

    # Remove unwanted sections - more comprehensive list
    for tag in ["footer", "nav", "aside", "script", "style", "header", "noscript", "iframe"]:
        for element in content_soup.find_all(tag):
            element.decompose()

    # Remove common UI elements by class/id
    for selector in [
        ".footer", "#footer", ".header", "#header", ".navbar", "#navbar",
        ".menu", "#menu", ".sidebar", "#sidebar", ".ad", ".advertisement",
        ".cookie", ".banner", ".social", ".share", ".comments", ".related",
        ".copyright", ".rights", ".legal", ".terms", ".privacy"
    ]:
        for element in content_soup.select(selector):
            element.decompose()

    # Try to extract the main content area
    main_element = None
    main_selectors = [
        "main", "#main", "article", ".content", "#content",
        ".main-content", ".product-content", ".product-description"
    ]

    for selector in main_selectors:
        elements = content_soup.select(selector)
        if elements:
            main_element = max(elements, key=lambda x: len(x.get_text()))
            break

    # If we found a main content element, use that; otherwise use the whole page
    if main_element:
        # Extract structured content
        return extract_structured_content(main_element, title, meta_desc)
    else:
        # Extract structured content from the whole page
        return extract_structured_content(content_soup, title, meta_desc)


def extract_structured_content(content_element, title, meta_desc):
    """Extract structured content with headings and paragraphs."""
    # Find main heading (typically h1)
    main_heading = content_element.find('h1')
    if not main_heading:
        main_heading = content_element.find('h2')

    main_heading_text = main_heading.get_text().strip() if main_heading else None

    # Find product description (after main heading)
    description = ""
    if main_heading:
        # Look for paragraphs after the main heading
        element = main_heading.next_sibling
        while element and (not hasattr(element, 'name') or element.name not in ['h1', 'h2', 'h3']):
            if hasattr(element, 'name') and element.name == 'p':
                description += element.get_text().strip() + " "
            element = element.next_sibling

    # If no description found next to heading, look for a lead paragraph
    if not description and content_element:
        lead_para = content_element.find(['p', 'div'], class_=lambda c: c and any(
            cls in c for cls in ['lead', 'intro', 'description', 'summary']))
        if lead_para:
            description = lead_para.get_text().strip()

    # Extract sections (headers and their content)
    sections = []
    headings = content_element.find_all(['h1', 'h2', 'h3'])

    for heading in headings:
        heading_text = heading.get_text().strip()

        # Skip empty headings
        if not heading_text:
            continue

        # Extract content until next heading
        content = ""
        element = heading.next_sibling

        while element and (not hasattr(element, 'name') or element.name not in ['h1', 'h2', 'h3']):
            if hasattr(element, 'name') and element.name in ['p', 'ul', 'ol', 'div', 'span']:
                element_text = element.get_text().strip()
                if element_text:
                    content += element_text + " "
            element = element.next_sibling

        if content:
            sections.append({
                "heading": heading_text,
                "content": content.strip()
            })

    # Build structured content
    structured_content = ""

    # Add main heading and description
    if main_heading_text:
        structured_content += f"{main_heading_text}\n\n"
    if description:
        structured_content += f"{description}\n\n"

    # Add all sections
    for section in sections:
        structured_content += f"{section['heading']}\n{section['content']}\n\n"

    # Clean up the content
    structured_content = clean_content(structured_content)

    return {
        "Page Title": title if title else "No Title Found",
        "Page Meta Data": meta_desc if meta_desc else "No Meta Description Found",
        "Page Content": structured_content[:5000]  # Limit to 5000 chars to avoid excessive text
    }


def clean_content(text):
    """Clean the extracted content."""
    # Fix spacing issues
    text = re.sub(r'\s+', ' ', text)

    # Fix special characters like "Â"
    text = text.replace('Â', '')

    # Remove duplicate spaces
    text = re.sub(r' +', ' ', text)

    # Remove excessive newlines but preserve paragraph structure
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove button text
    text = re.sub(r'(?:Get Access|Sign In|Log In|Sign Up|Learn More|See the Demo|Buy Now)\b', '', text)

    # Remove copyright and legal statements
    text = re.sub(r'Copyright ©.*', '', text)
    text = re.sub(r'All rights reserved\..*', '', text)

    return text.strip()

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
            st.write(product_info["Page Title"])

            st.subheader("📝 Page Meta Data")
            st.write(product_info["Page Meta Data"])

            st.subheader("📜 Page Content")
            st.text_area("Extracted Content", product_info["Page Content"], height=300)
        else:
            st.error("Failed to fetch the page. Please check the URL and try again.")
    else:
        st.warning("Please enter a valid URL.")

