import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urlparse, urljoin
import logging
from io import StringIO

# --- Configuration settings ---
google_url = "https://www.google.com/search"  # Google search URL (default is google.com)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                  "AppleWebKit/537.36 (KHTML, like Gecko) " +
                  "Chrome/91.0.4472.124 Safari/537.36"
}
delay_between_requests = 2  # seconds

# Setup logging
logging.basicConfig(
    filename='maillage_debug.log',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Streamlit interface for input
st.title("Détection d'opportunités de maillage interne")
site = st.text_input("Entrez l'URL de votre site (ex: https://charles-migaud.fr/consultant-seo-lille/:")
keywords_input = st.text_area("Entrez vos mots-clés (un par ligne) :")
keywords = keywords_input.splitlines()

# Function to perform Google search
def google_search(query, site):
    params = {
        'q': f"site:{site} {query}",
        'hl': 'fr',  # French results (default)
    }
    try:
        response = requests.get(google_url, headers=headers, params=params)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        for a_tag in soup.find_all('a', href=True):
            link = a_tag['href']
            if link.startswith('/url?q='):
                full_url = link[7:].split('&')[0]  # Extract full URL from Google's result
                if site in full_url:  # Ensure the link is from the same domain
                    links.append(full_url)
        return links
    except Exception as e:
        logging.error(f"Erreur lors de la recherche Google: {e}")
        return []

# Function to detect link opportunities
def detect_maillage(keywords, site):
    maillage_opportunities = []

    # Get base path of the site
    base_url = urlparse(site)
    base_path = base_url.path

    for idx, keyword in enumerate(keywords, start=1):
        st.write(f"[{idx}/{len(keywords)}] Recherche pour le mot-clé : {keyword}")
        logging.info(f"Processing keyword {idx}/{len(keywords)}: '{keyword}'")
        links = google_search(keyword, site)

        if len(links) > 0:
            top_link = links[0]  # The top 1 link
            for link in links[1:]:
                # Filter links based on the base path of the site
                parsed_link = urlparse(link)
                if parsed_link.path.startswith(base_path):  # Match the base path
                    maillage_opportunities.append([keyword, link, top_link, 'Ajouter un lien', 'Non Applicable'])
                    logging.info(f"Link opportunity: '{link}' → '{top_link}' for keyword '{keyword}' (Add Link)")
        else:
            logging.info(f"Aucun lien trouvé pour le mot-clé '{keyword}'.")

        time.sleep(delay_between_requests)  # Pause to avoid being blocked

    return maillage_opportunities

# Displaying results
if site and keywords_input:
    maillage_results = detect_maillage(keywords, site)
    
    if maillage_results:
        df = pd.DataFrame(maillage_results, columns=['Mot-clé', 'Lien', 'Top 1 Lien', 'Action', 'État de l’Ancre'])
        
        # Show results in a table
        st.dataframe(df)

        # Provide download option as CSV
        csv = df.to_csv(index=False)
        st.download_button(
            label="Télécharger les résultats (CSV)",
            data=csv,
            file_name="opportunites_maillage.csv",
            mime="text/csv"
        )
    else:
        st.write("Aucune opportunité de maillage trouvée.")
else:
    st.write("Veuillez entrer une URL de site et des mots-clés.")
