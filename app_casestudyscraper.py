import streamlit as st
import uuid
import json
from openai import OpenAI
from urllib.parse import urljoin
import langdetect
import cloudscraper
from bs4 import BeautifulSoup
import re
import time
import random
from urllib.parse import urlparse

# Set page title and layout
st.set_page_config(page_title="Company Case Study Scraper", layout="wide")


OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Helper functions for case study extraction
def extract_case_study(url):
    """
    Extract the title and body content from a case study URL.

    Args:
        url (str): The URL of the case study to analyze

    Returns:
        dict: A dictionary containing the title and body of the case study
              Example: {'title': 'Company X Success Story', 'body': 'Full text content...'}
    """
    try:
        # Create a cloudscraper session to bypass potential protections
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

        # Add a small random delay to avoid being blocked
        time.sleep(random.uniform(1, 3))

        response = scraper.get(url, timeout=15)

        if response.status_code != 200:
            return {'title': '', 'body': '', 'error': f"HTTP error {response.status_code}"}

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract domain for domain-specific parsing strategies
        domain = urlparse(url).netloc

        # Extract title - using multiple strategies to find the best match
        title = extract_title(soup, domain)

        # Extract body content - using multiple strategies to find the best match
        body = extract_body(soup, domain)

        if not title and not body:
            return {'title': '', 'body': '', 'error': "No content extracted"}

        return {
            'title': title,
            'body': body,
            'url': url
        }

    except Exception as e:
        return {'title': '', 'body': '', 'error': str(e)}


def extract_title(soup, domain):
    """
    Extract the title of the case study using various strategies.

    Args:
        soup (BeautifulSoup): Parsed HTML
        domain (str): Website domain for domain-specific strategies

    Returns:
        str: The extracted title
    """
    title = ""

    # Strategy 1: Look for schema.org markup
    schema_name = soup.find('meta', {'property': 'og:title'})
    if schema_name and schema_name.get('content'):
        title = schema_name.get('content').strip()
        return title

    # Strategy 2: Look for article headline schema
    headline = soup.find('meta', {'property': 'article:title'})
    if headline and headline.get('content'):
        title = headline.get('content').strip()
        return title

    # Strategy 3: H1 tag is often the title
    h1_tags = soup.find_all('h1')
    if h1_tags:
        # If multiple H1s, get the most prominent one (usually the first)
        potential_titles = [h1.get_text().strip() for h1 in h1_tags if h1.get_text().strip()]
        if potential_titles:
            title = potential_titles[0]
            return title

    # Strategy 4: Look for common title class names
    title_classes = ['title', 'article-title', 'entry-title', 'post-title', 'headline',
                     'story-title', 'case-study-title', 'cs-title', 'customer-story-title',
                     'success-story-title', 'page-title', 'main-title']

    for cls in title_classes:
        title_elem = soup.find(class_=re.compile(cls, re.I))
        if title_elem:
            title = title_elem.get_text().strip()
            return title

    # Strategy 5: Look for elements with ID that might be a title
    title_ids = ['title', 'article-title', 'post-title', 'headline', 'page-title']
    for id_value in title_ids:
        title_elem = soup.find(id=re.compile(id_value, re.I))
        if title_elem:
            title = title_elem.get_text().strip()
            return title

    # Strategy 6: Fall back to page title if all else fails
    if soup.title:
        title = soup.title.get_text().strip()
        # Try to clean up the title (often contains site name etc)
        title = re.sub(r'\s*\|.*$', '', title)  # Remove pipe and everything after
        title = re.sub(r'\s*-.*$', '', title)  # Remove dash and everything after
        return title

    return title


def extract_body(soup, domain):
    """
    Extract the body content of the case study using various strategies.

    Args:
        soup (BeautifulSoup): Parsed HTML
        domain (str): Website domain for domain-specific strategies

    Returns:
        str: The extracted body content
    """
    # First, remove elements that are unlikely to be part of the main content
    for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
        element.extract()

    body_content = ""

    # Strategy 1: Look for schema.org markup for article body
    article_body = soup.find('div', {'itemprop': 'articleBody'})
    if article_body:
        body_content = clean_content(article_body.get_text())
        if len(body_content) > 200:  # Minimum size check
            return body_content

    # Strategy 2: Look for common content class names
    content_classes = ['content', 'article-content', 'entry-content', 'post-content',
                       'case-study-content', 'customer-story', 'success-story',
                       'case-study-body', 'story-content', 'main-content', 'article-body',
                       'story', 'customer-story-content', 'cs-content', 'post-body']

    for cls in content_classes:
        content_elem = soup.find(class_=re.compile(cls, re.I))
        if content_elem:
            content_text = clean_content(content_elem.get_text())
            if len(content_text) > 200:  # Minimum size check
                body_content = content_text
                return body_content

    # Strategy 3: Look for elements with ID that might be content
    content_ids = ['content', 'article-content', 'post-content', 'main-content']
    for id_value in content_ids:
        content_elem = soup.find(id=re.compile(id_value, re.I))
        if content_elem:
            content_text = clean_content(content_elem.get_text())
            if len(content_text) > 200:  # Minimum size check
                body_content = content_text
                return body_content

    # Strategy 4: Look for article tag
    article = soup.find('article')
    if article:
        content_text = clean_content(article.get_text())
        if len(content_text) > 200:  # Minimum size check
            body_content = content_text
            return body_content

    # Strategy 5: Look for main tag
    main = soup.find('main')
    if main:
        content_text = clean_content(main.get_text())
        if len(content_text) > 200:  # Minimum size check
            body_content = content_text
            return body_content

    # Strategy 6: Look for largest text block (fallback)
    paragraphs = soup.find_all('p')
    if paragraphs:
        # Get the parent that contains the most paragraphs
        parents = {}
        for p in paragraphs:
            if p.parent:
                parent_str = str(p.parent.name) + str(p.parent.get('class', '')) + str(p.parent.get('id', ''))
                if parent_str in parents:
                    parents[parent_str]['count'] += 1
                    parents[parent_str]['parent'] = p.parent
                else:
                    parents[parent_str] = {'count': 1, 'parent': p.parent}

        if parents:
            # Find the parent with the most paragraphs
            main_parent = max(parents.values(), key=lambda x: x['count'])
            content_text = clean_content(main_parent['parent'].get_text())
            if len(content_text) > 200:  # Minimum size check
                body_content = content_text
                return body_content

    # Strategy 7: Just concatenate all paragraphs as a last resort
    if not body_content:
        all_paragraphs = [p.get_text().strip() for p in soup.find_all('p') if p.get_text().strip()]
        if all_paragraphs:
            body_content = "\n\n".join(all_paragraphs)
            return body_content

    return body_content


def clean_content(text):
    """
    Clean up extracted content.

    Args:
        text (str): Raw extracted text

    Returns:
        str: Cleaned text
    """
    # Replace multiple newlines with just two
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Replace multiple spaces with a single space
    text = re.sub(r'\s{2,}', ' ', text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def detect_website_language(url):
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

        response = scraper.get(url, timeout=15)

        if response.status_code != 200:
            return {'code': 'unknown', 'name': 'Unknown', 'confidence': 0.0}

        # Check HTTP headers for language info
        content_language = response.headers.get('Content-Language')
        if content_language:
            # Extract the primary language if multiple are specified
            primary_lang = content_language.split(',')[0].strip().split('-')[0].lower()
            if primary_lang:
                return get_language_details(primary_lang, confidence=0.9)

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Check HTML lang attribute
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            html_lang = html_tag.get('lang').strip().split('-')[0].lower()
            if html_lang:
                return get_language_details(html_lang, confidence=0.85)

        # Check meta tags
        meta_lang = None
        for meta in soup.find_all('meta'):
            if meta.get('http-equiv', '').lower() == 'content-language' and meta.get('content'):
                meta_lang = meta.get('content').strip().split('-')[0].lower()
                if meta_lang:
                    return get_language_details(meta_lang, confidence=0.8)

        # Extract text content for language detection
        # Remove script and style elements
        for script in soup(['script', 'style', 'code', 'pre']):
            script.extract()

        # Get visible text
        text = soup.get_text(separator=' ')

        # Clean the text (remove extra spaces, numbers, URLs, etc.)
        text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
        text = re.sub(r'https?://\S+', '', text)  # Remove URLs
        text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
        text = text.strip()

        if not text:
            return {'code': 'unknown', 'name': 'Unknown', 'confidence': 0.0}

        # Use a sample of text for detection (first 2000 chars should be enough)
        sample_text = text[:2000]

        # Detect language
        try:
            # Get detailed language detection with probabilities
            detection = langdetect.detect_langs(sample_text)

            if detection:
                primary_detection = detection[0]
                lang_code = primary_detection.lang
                confidence = primary_detection.prob

                return get_language_details(lang_code, confidence)

        except langdetect.lang_detect_exception.LangDetectException as e:
            pass

        return {'code': 'unknown', 'name': 'Unknown', 'confidence': 0.0}

    except Exception as e:
        return {'code': 'unknown', 'name': 'Unknown', 'confidence': 0.0}


def get_language_details(lang_code, confidence=0.0):
    """
    Get full language name from language code.

    Args:
        lang_code (str): ISO 639-1 language code
        confidence (float): Detection confidence

    Returns:
        dict: Language details including code, name and confidence
    """
    # Map of ISO 639-1 language codes to full names
    language_map = {
        'af': 'Afrikaans',
        'ar': 'Arabic',
        'bg': 'Bulgarian',
        'bn': 'Bengali',
        'ca': 'Catalan',
        'cs': 'Czech',
        'cy': 'Welsh',
        'da': 'Danish',
        'de': 'German',
        'el': 'Greek',
        'en': 'English',
        'es': 'Spanish',
        'et': 'Estonian',
        'fa': 'Persian',
        'fi': 'Finnish',
        'fr': 'French',
        'gu': 'Gujarati',
        'he': 'Hebrew',
        'hi': 'Hindi',
        'hr': 'Croatian',
        'hu': 'Hungarian',
        'id': 'Indonesian',
        'it': 'Italian',
        'ja': 'Japanese',
        'kn': 'Kannada',
        'ko': 'Korean',
        'lt': 'Lithuanian',
        'lv': 'Latvian',
        'mk': 'Macedonian',
        'ml': 'Malayalam',
        'mr': 'Marathi',
        'ne': 'Nepali',
        'nl': 'Dutch',
        'no': 'Norwegian',
        'pa': 'Punjabi',
        'pl': 'Polish',
        'pt': 'Portuguese',
        'ro': 'Romanian',
        'ru': 'Russian',
        'sk': 'Slovak',
        'sl': 'Slovenian',
        'so': 'Somali',
        'sq': 'Albanian',
        'sv': 'Swedish',
        'sw': 'Swahili',
        'ta': 'Tamil',
        'te': 'Telugu',
        'th': 'Thai',
        'tl': 'Tagalog',
        'tr': 'Turkish',
        'uk': 'Ukrainian',
        'ur': 'Urdu',
        'vi': 'Vietnamese',
        'zh-cn': 'Chinese (Simplified)',
        'zh-tw': 'Chinese (Traditional)',
        'zh': 'Chinese'
    }

    language_name = language_map.get(lang_code.lower(), 'Unknown')

    return {
        'code': lang_code.lower(),
        'name': language_name,
        'confidence': confidence
    }


def get_case_study_urls(base_url, keywords, max_results):
    """
    Process sitemaps one at a time and yield matching URLs as they're found.
    Stops after yielding max_results VALID URLs.

    Args:
        base_url: The website base URL
        keywords: List of keywords to match in URLs
        max_results: Maximum number of VALID URLs to yield

    Yields:
        Valid matching URLs as they are found, up to max_results
    """
    with st.spinner(f"Searching for case studies on {base_url}..."):
        status_placeholder = st.empty()
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

        # Get potential sitemap URLs
        sitemap_urls = []

        # First try to find sitemaps from robots.txt
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            status_placeholder.write("Checking robots.txt...")
            response = scraper.get(robots_url, timeout=10)
            if response.status_code == 200:
                robots_text = response.text
                status_placeholder.write("Successfully retrieved robots.txt")

                # Look for sitemap entries in robots.txt
                sitemap_urls = re.findall(r'(?i)sitemap:\s*(https?://[^\s]+)', robots_text)
                status_placeholder.write(f"Found {len(sitemap_urls)} sitemaps in robots.txt")
        except Exception as e:
            status_placeholder.write(f"Error fetching robots.txt: {str(e)}")

        # If no sitemaps found in robots.txt, try common locations
        if not sitemap_urls:
            sitemap_urls = [
                urljoin(base_url, '/sitemap.xml'),
                urljoin(base_url, '/sitemap_index.xml'),
                urljoin(base_url, '/sitemap-index.xml')
            ]
            status_placeholder.write(f"Using default sitemap locations")

        processed_sitemaps = set()

        # Keep track of how many VALID URLs we've yielded
        valid_url_count = 0

        # Process one sitemap at a time
        for sitemap_url in sitemap_urls:
            # Stop if we've reached the maximum number of VALID results
            if valid_url_count >= max_results:
                status_placeholder.write(f"Found {valid_url_count} case studies")
                break

            status_placeholder.write(f"Processing sitemap: {sitemap_url}")

            # Process the main sitemap and yield results
            for url in process_sitemap_and_yield_urls(
                    scraper, sitemap_url, keywords, processed_sitemaps,
                    yield_matches=True, max_results=max_results, current_valid_count=valid_url_count,
                    status_placeholder=status_placeholder
            ):
                status_placeholder.write(f"Checking if URL is in English: {url}")
                if check_url_is_english(url):
                    yield url
                    valid_url_count += 1
                    status_placeholder.write(f"Found case study {valid_url_count}/{max_results}: {url}")

                    # Stop if we've reached the maximum number of VALID results
                    if valid_url_count >= max_results:
                        status_placeholder.write(f"Found {valid_url_count} case studies - completed search")
                        break
                else:
                    status_placeholder.write(f"Skipping non-English page: {url}")


def process_sitemap_and_yield_urls(scraper, sitemap_url, keywords, processed_sitemaps,
                                   yield_matches=True, max_results=5, current_valid_count=0,
                                   status_placeholder=None):
    """
    Process a single sitemap and yield matching URLs as they're found.

    Args:
        scraper: The cloudscraper session
        sitemap_url: URL of the sitemap to process
        keywords: List of keywords to match
        processed_sitemaps: Set of already processed sitemap URLs
        yield_matches: Whether to yield matches (True) or collect and return them (False)
        max_results: Maximum number of VALID URLs to process
        current_valid_count: Current count of VALID URLs found
        status_placeholder: Streamlit placeholder for status updates

    Yields:
        Matching URLs as they are found (if yield_matches=True)
    Returns:
        List of matching URLs (if yield_matches=False)
    """
    if sitemap_url in processed_sitemaps:
        if yield_matches:
            return []  # Return empty iterable instead of None
        else:
            return []

    processed_sitemaps.add(sitemap_url)
    matching_urls = [] if not yield_matches else None

    try:
        response = scraper.get(sitemap_url, timeout=10)

        if response.status_code != 200:
            if status_placeholder:
                status_placeholder.write(f"Failed to fetch sitemap: {sitemap_url}, Status: {response.status_code}")
            return [] if not yield_matches else None

        # Check if it's XML content
        content_type = response.headers.get('Content-Type', '')
        if 'xml' not in content_type.lower() and not sitemap_url.endswith('.xml'):
            if status_placeholder:
                status_placeholder.write(f"Not an XML sitemap: {sitemap_url}")
            return [] if not yield_matches else None

        # Parse XML content
        soup = BeautifulSoup(response.content, 'xml')

        # Check if it's a sitemap index
        sitemap_tags = soup.find_all('sitemap')
        if sitemap_tags:
            # This is a sitemap index, process each sitemap
            if status_placeholder:
                status_placeholder.write(f"Found sitemap index with {len(sitemap_tags)} child sitemaps")
            for sitemap_tag in sitemap_tags:
                loc_tag = sitemap_tag.find('loc')
                if loc_tag:
                    child_sitemap_url = loc_tag.text.strip()
                    if status_placeholder:
                        status_placeholder.write(f"Processing child sitemap: {child_sitemap_url}")

                    # Recursively process child sitemap
                    if yield_matches:
                        for url in process_sitemap_and_yield_urls(
                                scraper, child_sitemap_url, keywords, processed_sitemaps,
                                yield_matches=True, max_results=max_results,
                                current_valid_count=current_valid_count,
                                status_placeholder=status_placeholder
                        ):
                            # Just yield potential matches - validation is done in main function
                            yield url
                    else:
                        child_urls = process_sitemap_and_yield_urls(
                            scraper, child_sitemap_url, keywords, processed_sitemaps,
                            yield_matches=False, max_results=max_results,
                            current_valid_count=current_valid_count,
                            status_placeholder=status_placeholder
                        )

                        # No need to filter here - we'll collect all potential matches
                        # and let the caller validate
                        matching_urls.extend(child_urls)
        else:
            # This is a regular sitemap, extract URLs
            url_tags = soup.find_all('url')
            if status_placeholder:
                status_placeholder.write(f"Processing regular sitemap with {len(url_tags)} URLs")

            # Check each URL against keywords
            for url_tag in url_tags:
                loc_tag = url_tag.find('loc')
                if loc_tag:
                    url = loc_tag.text.strip()
                    if is_matching_url(url, keywords):
                        if status_placeholder:
                            status_placeholder.write(f"Found matching URL: {url}")
                        if yield_matches:
                            # Just yield potential matches - validation is done in main function
                            yield url
                        else:
                            # For non-yielding case, collect all potential matches
                            matching_urls.append(url)

    except Exception as e:
        if status_placeholder:
            status_placeholder.write(f"Error processing sitemap {sitemap_url}: {str(e)}")

    if not yield_matches:
        if status_placeholder:
            status_placeholder.write(f"Found {len(matching_urls)} potentially matching URLs in sitemap: {sitemap_url}")
        return matching_urls


def is_matching_url(url, keywords):
    """
    Check if a URL strictly matches the pattern: companyurl.com/keyword/something
    where 'something':
    - is at least 5 characters
    - doesn't contain any keywords
    - doesn't contain the word "customer"
    - isn't another keyword

    Args:
        url: The URL to check
        keywords: List of keywords to match

    Returns:
        True if the URL matches the required pattern, False otherwise
    """
    url_lower = url.lower()
    min_segment_length = 5  # Minimum length requirement for the segment after keyword

    for keyword in keywords:
        keyword_lower = keyword.lower()

        # Check for pattern: /keyword/something
        pattern = f"/{keyword_lower}/"
        if pattern in url_lower:
            # Get the part after the keyword
            parts = url_lower.split(pattern)
            if len(parts) > 1:
                after_keyword = parts[1].split("/")[0]  # Get the next path segment

                # Check if after_keyword meets minimum length requirement
                if len(after_keyword) >= min_segment_length:
                    # 1. Check if after_keyword is another keyword
                    is_another_keyword = False
                    for k in keywords:
                        if k.lower() == after_keyword:
                            is_another_keyword = True
                            break

                    if is_another_keyword:
                        continue

                    # 2. Check if after_keyword contains any keywords
                    contains_keyword = False
                    for k in keywords:
                        if k.lower() in after_keyword:
                            contains_keyword = True
                            break

                    if contains_keyword:
                        continue

                    # 3. Check if after_keyword contains "customer"
                    if "customer" in after_keyword:
                        continue

                    # All checks passed - this is a valid match
                    return True

    # No valid match found
    return False


def check_url_is_english(url):
    result = detect_website_language(url)
    if result['name'] == "English":
        return True
    else:
        return False


def process_case_studies_with_ai(case_studies, prompt, model="gpt-4o"):
    """
    Process case studies information with AI.

    Args:
        case_studies (list): List of case study dictionaries
        prompt (str): Prompt for the AI
        model (str): OpenAI model to use

    Returns:
        str: AI response
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Format case studies content for the AI
    content = "Here are the case studies I found:\n\n"

    for i, case_study in enumerate(case_studies, 1):
        content += f"--- Case Study {i} ---\n"
        content += f"Title: {case_study['title']}\n"
        content += f"URL: {case_study['url']}\n"
        content += f"Content:\n{case_study['body'][:10000]}\n\n"  # Limit body content to avoid token limits

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": f"{content}\n\n{prompt}"
                }
            ],
            max_tokens=2000
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error processing with AI: {str(e)}"


def display_case_studies(case_studies):
    """Display the case studies in expandable sections"""
    for i, case_study in enumerate(case_studies, 1):
        with st.expander(f"Case Study {i}: {case_study['title']}"):
            st.write(f"**URL:** {case_study['url']}")
            st.write(f"**Title:** {case_study['title']}")

            # Display a preview of the body (first 500 chars)
            if len(case_study['body']) > 500:
                st.write(f"**Content Preview:** {case_study['body'][:500]}...")
            else:
                st.write(f"**Content:** {case_study['body']}")

            if 'error' in case_study and case_study['error']:
                st.error(f"Error: {case_study['error']}")

# Main Streamlit app
st.title("Company Case Study Scraper 📊")

# Layout: Case study scraping on Left | AI Analysis on Right
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Find Case Studies 🔍")

    # User inputs
    company_url = st.text_input("Enter company URL:", "https://salesforce.com")
    num_case_studies = st.number_input("Number of case studies to find:", min_value=1, max_value=20, value=5)

    # Define keywords to look for
    CASE_STUDY_KEYWORDS = [
        "customer-success-stories", "success-stories", "case-study", "case-studies",
        "customers", "customer", "customer-success", "customer-stories", "client-stories",
        "success-story", "customer-story"
    ]

    # Scrape button
    if st.button("Find Case Studies"):
        # Process sitemaps and get matching URLs
        try:
            matching_urls = list(get_case_study_urls(company_url, CASE_STUDY_KEYWORDS, int(num_case_studies)))

            if matching_urls:
                st.session_state["case_study_urls"] = matching_urls

                st.success(f"Found {len(matching_urls)} case study URLs, processing {len(matching_urls) - 1}!")
                st.info("Note: The first URL will be skipped as it often doesn't match what we want as a case study.")

                # Extract content from each URL
                case_studies = []

                with st.spinner("Extracting content from case studies..."):
                    progress_bar = st.progress(0)


                    # Start from index 1 (second URL) instead of 0
                    for i, url in enumerate(matching_urls[1:], 1):

                        st.write(f"Extracting content from: {url}")
                        case_study = extract_case_study(url)
                        case_studies.append(case_study)
                        progress_bar.progress((i + 1) / len(matching_urls))

                st.session_state["case_studies"] = case_studies

                # Display case studies using the function
                display_case_studies(case_studies)
            else:
                st.warning("No case studies found. Try a different company URL.")

        except Exception as e:
            st.error(f"Error finding case studies: {str(e)}")

    # Always display case studies if they exist in session state (this is the key part)
    elif "case_studies" in st.session_state:
        display_case_studies(st.session_state["case_studies"])

with col2:
    st.subheader("AI Analysis 🧠")

    # Model selection
    model = st.selectbox("Select AI Model:", ["gpt-4o", "gpt-4o-mini"])

    # Prompt input
    prompt = st.text_area(
        "Enter prompt for AI Analysis (default: summarize information about the company):",
        value="Please read all of these case studies and summarize information you learned about the company"
    )

    # AI analysis button
    if st.button("Analyze with AI"):
        if "case_studies" in st.session_state:
            case_studies = st.session_state["case_studies"]
            if case_studies:
                # Prepare prompt with all the case study content
                result = process_case_studies_with_ai(case_studies, prompt, model)

                # Display the result
                st.subheader("AI Analysis Result 🧠")
                st.write(result)
            else:
                st.warning("No case studies available to analyze. Please scrape case studies first.")
        else:
            st.warning("Please scrape case studies first.")
