import streamlit as st
import json
import requests
import cloudscraper
from bs4 import BeautifulSoup
from googlesearch import search
from urllib.parse import urlparse
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
        # Load service account info from Streamlit secrets
        # You should store this service account JSON in your Streamlit secrets.toml
        import json
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        #Get CSE ID from Streamlit secrets
        cse_id = st.secrets["googlecloudconsole"]["cse_id"] if "googlecloudconsole" in st.secrets else None

        if not cse_id:
            return "Custom Search Engine ID not configured. Please add it to the app secrets."

        # Replace the hardcoded credentials with this code
        service_account_info = st.secrets["service_account"] if "service_account" in st.secrets else None

        if not service_account_info:
            return "Service account credentials not configured. Please add them to the app secrets."




        # Create credentials and service
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/cse']
        )

        # Build the service
        service = build('customsearch', 'v1', credentials=credentials)

        # Create the search query
        query = f"{website_url} LinkedIn company page"

        # Execute the search
        result = service.cse().list(q=query, cx=cse_id).execute()

        # Check if we got any results
        if "items" not in result or not result["items"]:
            return "No LinkedIn page found in search results."

        # Get the first result that contains linkedin.com/company
        linkedin_url = None
        for item in result["items"]:
            if "linkedin.com/company" in item["link"]:
                linkedin_url = item["link"]
                break

        if not linkedin_url:
            return "No LinkedIn company page found in search results."

        st.write(f"Found LinkedIn URL: {linkedin_url}")

        # Use cloudscraper to get the LinkedIn page
        scraper = cloudscraper.create_scraper()
        response = scraper.get(linkedin_url)

        if response.status_code != 200:
            return f"Failed to fetch LinkedIn page. Status code: {response.status_code}"

        # Parse the LinkedIn page and try multiple methods to find the About section
        soup = BeautifulSoup(response.text, 'html.parser')

        # Method 1: Try JSON-LD
        script = soup.find('script', type='application/ld+json')
        if script and script.string:
            try:
                data = json.loads(script.string)
                # Try different JSON paths that might contain the about info
                if "@graph" in data:
                    organization_data = data.get("@graph", [])[0]
                    about_text = organization_data.get("description")
                    if about_text:
                        return about_text

                # Direct access attempt
                about_text = data.get("description")
                if about_text:
                    return about_text
            except (json.JSONDecodeError, IndexError, KeyError):
                pass  # Continue to other methods if this fails

        # Method 2: Try common HTML elements that might contain about info
        about_section = soup.find('section', {'class': 'about-us'}) or \
                        soup.find('section', {'id': 'about-us'}) or \
                        soup.find('div', {'class': 'org-about-us-organization-description'}) or \
                        soup.find('p', {'class': 'break-words'})

        if about_section:
            return about_section.text.strip()

        # Method 3: Look for "About" section using text cues
        about_headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5'], string=lambda s: s and 'About' in s)
        for header in about_headers:
            next_sibling = header.find_next('p')
            if next_sibling:
                return next_sibling.text.strip()

        # If all methods fail
        return "About section found but could not extract content. LinkedIn may require authentication."

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
