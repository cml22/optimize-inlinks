import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urlparse, urljoin
import logging

# --- Configuration settings ---
output_file = 'linking_opportunities.csv'
google_url = "https://www.google.com/search"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                  "AppleWebKit/537.36 (KHTML, like Gecko) " +
                  "Chrome/91.0.4472.124 Safari/537.36"
}
delay_between_requests = 2  # seconds

# Initialize logging
logging.basicConfig(
    filename='linking_debug.log',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Function to perform a Google search and retrieve results for a specific keyword
def google_search(query, site_url=None, num_results=10):
    try:
        search_query = f'{query} site:{site_url}' if site_url else query
        params = {"q": search_query, "num": num_results}
        response = requests.get(google_url, headers=headers, params=params)
        response.raise_for_status()  # Check for HTTP errors

        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        for g in soup.find_all('div', class_='tF2Cxc'):
            a_tag = g.find('a', href=True)
            if a_tag:
                link = a_tag['href']
                # Ensure the link is within the specified directory
                if urlparse(link).path.startswith(urlparse(site_url).path):
                    links.append(link)
        logging.info(f"Google search for '{search_query}' returned {len(links)} links")
        return links
    except requests.RequestException as e:
        logging.error(f"HTTP error during Google search for '{query}': {e}")
        return []
    except Exception as e:
        logging.error(f"Error during Google search for '{query}': {e}")
        return []

# Function to check if a source page links to the target page and if the anchor is optimized
def check_existing_link(source_url, target_url, keyword):
    try:
        response = requests.get(source_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        target_path = urlparse(target_url).path.lower()
        keyword_lower = keyword.lower()

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            normalized_href = urljoin(source_url, href)
            parsed_href = urlparse(normalized_href)
            if parsed_href.path.lower() == target_path:
                anchor_text = a_tag.get_text().strip().lower()
                if anchor_text == keyword_lower:
                    return (True, 'Yes')
                else:
                    return (True, 'No')
        return (False, 'No')
    except requests.RequestException as e:
        logging.warning(f"HTTP error accessing '{source_url}': {e}")
        return (False, 'No')
    except Exception as e:
        logging.warning(f"Error parsing '{source_url}': {e}")
        return (False, 'No')

# Detect linking opportunities by linking all pages to the top 1 result
def detect_linking_opportunities(keywords, site_url):
    linking_opportunities = []

    for idx, keyword in enumerate(keywords, start=1):
        logging.info(f"Processing keyword {idx}/{len(keywords)}: '{keyword}'")
        links = google_search(keyword, site_url)

        if links:
            top_link = links[0]
            for link in links[1:]:
                exists, anchor_optimized = check_existing_link(link, top_link, keyword)
                if not exists:
                    linking_opportunities.append([keyword, link, top_link, "Add a link", 'Not Applicable'])
                    logging.info(f"Link opportunity: '{link}' → '{top_link}' for keyword '{keyword}' (Add Link)")
                elif anchor_optimized == 'No':
                    linking_opportunities.append([keyword, link, top_link, "Optimize anchor text", 'No'])
                    logging.info(f"Anchor optimization needed: '{link}' links to '{top_link}' with non-optimized anchor for keyword '{keyword}'")
        else:
            logging.info(f"No links found for keyword '{keyword}'.")

        time.sleep(delay_between_requests)

    return linking_opportunities

# Streamlit UI and execution
st.title("Internal Linking Opportunities Detection Tool")
st.write("### Please enter the information below to start the analysis.")

site_url = st.text_input("Enter the target site URL for the `site:` command")
keywords_input = st.text_area("Keywords (one per line)")
if st.button("Start Analysis"):
    if not keywords_input or not site_url:
        st.warning("Please enter a URL and keywords.")
    else:
        keywords = [line.strip() for line in keywords_input.splitlines() if line.strip()]
        opportunities = detect_linking_opportunities(keywords, site_url)
        
        if opportunities:
            df = pd.DataFrame(opportunities, columns=["Keyword", "Source Page", "Target Page", "Required Action", "Anchor Optimized"])
            st.dataframe(df)

            # Provide download link
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Results as CSV",
                data=csv,
                file_name=output_file,
                mime="text/csv"
            )
        else:
            st.write("No internal linking opportunities found.")

# Documentation displayed at the bottom
st.write("---")
st.write("### About This Tool")
st.write("""
This internal linking detection tool helps identify opportunities for creating internal links
by analyzing Google search results for specific keywords. It checks if the top-ranking pages
are interlinked and whether the anchor text is optimized for the target keywords.
Recommended actions include adding internal links or optimizing anchor text.

**How It Works:**
1. Enter your site URL and a list of keywords.
2. The tool searches Google results for each keyword and finds the most relevant pages.
3. It analyzes existing links between these pages and suggests optimization actions.

For questions or assistance, contact me by visiting the site of [Charles Migaud, SEO Consultant Lille](https://charles-migaud.fr/consultant-seo-lille).
""")
