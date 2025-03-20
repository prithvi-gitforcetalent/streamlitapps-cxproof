import streamlit as st
import json
import requests
import cloudscraper
from bs4 import BeautifulSoup
from googlesearch import search
from urllib.parse import urlparse


def normalize_url(url):
    """Ensure only the homepage URL is returned, stripping any subpages."""

    # Add https:// if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

        # Parse the URL
    parsed_url = urlparse(url)

    # If the input was incorrectly formatted, handle it safely
    if not parsed_url.netloc:
        return "Invalid URL"

    # Construct base URL (only scheme + domain)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"

    return base_url


def scrape_title(website_url):
    scraper = cloudscraper.create_scraper()
    output = []
    try:
        response = scraper.get(website_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title').text if soup.find('title') else 'No title found'
        output.append(f"Title: {title_tag}")
    except Exception as e:
        output.append(f"An error occurred: {e}")

    return "\n".join(output)

def scrape_meta_content(website_url):
    scraper = cloudscraper.create_scraper()  # Create a cloudscraper instance
    output = []
    try:
        response = scraper.get(website_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        meta_tags = soup.find_all('meta')
        content_list = [tag.get('content') for tag in meta_tags if tag.get('content')]

        for idx, content in enumerate(content_list, start=1):
            output.append(f"{idx}. {content}")

    except Exception as e:
        output.append(f"An error occurred: {e}")

    return "\n".join(output)





def find_linkedin_about_section(website_url):
    try:
        # Your Google API key and Custom Search Engine ID

        api_key = st.secrets["googlecloudconsole"]["api_key"] if "googlecloudconsole" in st.secrets else None

        cse_id = st.secrets["googlecloudconsole"]["cse_id"] if "googlecloudconsole" in st.secrets else None

        # Create the search query
        query = f"{website_url} LinkedIn company page"

        # Make the API request
        search_url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cse_id}&q={query}"
        response = requests.get(search_url)

        if response.status_code != 200:
            return f"Google API error: {response.status_code}"

        # Parse the response
        search_results = response.json()

        # Check if we got any results
        if "items" not in search_results or not search_results["items"]:
            return "No LinkedIn page found in search results."

        # Get the first result that contains linkedin.com
        linkedin_url = None
        for item in search_results["items"]:
            if "linkedin.com/company" in item["link"]:
                linkedin_url = item["link"]
                break

        if not linkedin_url:
            return "No LinkedIn company page found in search results."

        st.write(f"Found LinkedIn URL: {linkedin_url}")

        # Continue with your existing LinkedIn scraping code...
        scraper = cloudscraper.create_scraper()
        response = scraper.get(linkedin_url)

        # Rest of your existing code...
    except Exception as e:
        return f"An error occurred: {str(e)}"

st.set_page_config(
    page_title="Company Data Extractor"
)


# Streamlit UI
st.title("Company Data Extractor")




# Input URL
user_input = st.text_input("Enter a company website URL:")



if st.button("Extract Data"):
    if user_input:
        # Normalize the input URL to extract only the homepage
        website_url = normalize_url(user_input)
        st.write("## Results")
        st.write(f"**Processed URL:** {website_url}")

        # Get and display Title content
        title = scrape_title(website_url)
        st.write("### Title:")
        st.write(title)

        # Get and display Meta content
        meta_content = scrape_meta_content(website_url)
        st.write("### Meta Tags Content:")
        st.write(meta_content)


        # Get and display LinkedIn About section
        linkedin_about = find_linkedin_about_section(website_url)
        st.write("### LinkedIn About Section:")
        st.write(linkedin_about)


    else:
        st.warning("Please enter a valid URL.")
