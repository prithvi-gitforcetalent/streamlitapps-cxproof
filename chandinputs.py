import streamlit as st
import json
import requests
import cloudscraper
from bs4 import BeautifulSoup
from googlesearch import search


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
        # Step 1: Perform a Google search for "WEBSITE URL + LinkedIn"
        query = f"{website_url} LinkedIn"
        search_results = search(query, num_results=1)  # Get the first result
        linkedin_url = next(search_results, None)

        if not linkedin_url:
            return "No LinkedIn page found in the search results."

        # Step 2: Fetch the LinkedIn page
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(linkedin_url, headers=headers)
        if response.status_code != 200:
            return f"Failed to fetch LinkedIn page. Status code: {response.status_code}"

        # Step 3: Parse the LinkedIn page and find the "About" section
        soup = BeautifulSoup(response.text, 'html.parser')
        script = soup.find('script', type='application/ld+json')

        if script:
            try:
                data = json.loads(script.string)
                organization_data = data.get("@graph", [])[0]  # Get first element of @graph
                about_text = organization_data.get("description", "No about section found.")
                return about_text

            except json.JSONDecodeError:
                return "Error decoding JSON."
            except (IndexError, KeyError):
                return "Key not found in JSON."

        return "No JSON-LD script found."

    except Exception as e:
        return f"An error occurred: {e}"


# Streamlit UI
st.title("Company Data Extractor")

# Input URL
website_url = st.text_input("Enter a company website URL:")

if st.button("Extract Data"):
    if website_url:
        st.write("## Results")
        st.write(f"**URL:** {website_url}")

        # Get and display LinkedIn About section
        linkedin_about = find_linkedin_about_section(website_url)
        st.write("### LinkedIn About Section:")
        st.write(linkedin_about)

        # Get and display Meta content
        meta_content = scrape_meta_content(website_url)
        st.write("### Meta Tags Content:")
        st.write(meta_content)
    else:
        st.warning("Please enter a valid URL.")
