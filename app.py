import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urlparse, urljoin
import logging

# --- Configuration initiale ---
output_file = 'opportunites_maillage.csv'         # Fichier de sortie pour les opportunités
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                  "AppleWebKit/537.36 (KHTML, like Gecko) " +
                  "Chrome/91.0.4472.124 Safari/537.36"
}
delay_between_requests = 2  # Délai entre les requêtes en secondes

# Configuration de la journalisation
logging.basicConfig(
    filename='maillage_debug.log',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Fonction de recherche Google pour un mot-clé spécifique
def google_search(query, site, google_domain, num_results=10):
    try:
        search_query = f'{query} site:{site}' if site else query
        url = f"https://{google_domain}/search"
        params = {"q": search_query, "num": num_results}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        for g in soup.find_all('div', class_='tF2Cxc'):
            a_tag = g.find('a', href=True)
            if a_tag:
                link = a_tag['href']
                links.append(link)
        logging.info(f"Google search for '{search_query}' returned {len(links)} links")
        return links
    except requests.RequestException as e:
        logging.error(f"HTTP error during Google search for '{query}': {e}")
        return []
    except Exception as e:
        logging.error(f"Error during Google search for '{query}': {e}")
        return []

# Vérifier si une page source contient un lien vers la page cible avec une ancre optimisée
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
                    return (True, 'Oui')  # Lien existe et l'ancre est optimisée
                else:
                    return (True, 'Non')  # Lien existe mais ancre non optimisée
        return (False, 'Non')  # Lien n'existe pas
    except requests.RequestException as e:
        logging.warning(f"HTTP error accessing '{source_url}': {e}")
        return (False, 'Non')
    except Exception as e:
        logging.warning(f"Error parsing '{source_url}': {e}")
        return (False, 'Non')

# Détecter les opportunités de maillage interne
def detect_maillage(keywords, site, google_domain):
    maillage_opportunities = []

    for idx, keyword in enumerate(keywords, start=1):
        st.write(f"[{idx}/{len(keywords)}] Recherche pour le mot-clé : {keyword}")
        logging.info(f"Processing keyword {idx}/{len(keywords)}: '{keyword}'")
        links = google_search(keyword, site, google_domain)

        if len(links) > 0:
            top_link = links[0]
            for link in links[1:]:
                exists, anchor_optimized = check_existing_link(link, top_link, keyword)
                if not exists:
                    action = "Ajouter un lien"
                    maillage_opportunities.append([keyword, link, top_link, action, 'Non Applicable'])
                    logging.info(f"Link opportunity: '{link}' → '{top_link}' for keyword '{keyword}' (Add Link)")
                else:
                    if anchor_optimized == 'Non':
                        action = "Optimiser l'ancre"
                        maillage_opportunities.append([keyword, link, top_link, action, 'Non'])
                        logging.info(f"Anchor optimization needed: '{link}' already links to '{top_link}' with non-optimized anchor for keyword '{keyword}'")
                    else:
                        logging.info(f"Existing optimized link found: '{link}' already links to '{top_link}' with optimized anchor for keyword '{keyword}'")
        else:
            logging.info(f"No links found for keyword '{keyword}'.")

        time.sleep(delay_between_requests)

    return maillage_opportunities

# Exporter les résultats vers un fichier CSV
def export_to_csv(maillage_opportunities, output_file):
    try:
        df = pd.DataFrame(maillage_opportunities, columns=["Mot-Clé", "Page Source", "Page Cible", "Action Requise", "Anchor Optimisé"])
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logging.info(f"Exported {len(maillage_opportunities)} opportunities to '{output_file}'")
        return output_file
    except Exception as e:
        logging.error(f"Error exporting to CSV: {e}")
        raise

# Interface principale Streamlit
def main():
    st.title("Outil de Détection d'Opportunités de Maillage Interne")
    st.write("Entrez vos mots-clés (un par ligne) :")

    # Zone de texte pour saisir les mots-clés
    keywords_input = st.text_area("Mots-clés", placeholder="Mots-clés, un par ligne...")
    
    # Champ de texte pour entrer l'URL ou le site à analyser
    site = st.text_input("Site à analyser (ex: charles-migaud.fr)", value="charles-migaud.fr")
    
    # Sélection de la langue de recherche
    language = st.selectbox("Langue de recherche", ["fr", "en", "es", "de"])
    
    # Sélection du domaine Google
    google_domain = st.selectbox("Moteur de recherche", ["google.fr", "google.com", "google.es", "google.de"])

    if st.button("Lancer l'analyse"):
        if keywords_input.strip():
            keywords = [line.strip() for line in keywords_input.split('\n') if line.strip()]
            if not keywords:
                st.warning("Veuillez entrer au moins un mot-clé.")
            else:
                st.write("Détection des opportunités de maillage en cours...")
                maillage_opportunities = detect_maillage(keywords, site, google_domain)

                if maillage_opportunities:
                    output_path = export_to_csv(maillage_opportunities, output_file)
                    st.success(f"Opportunités de maillage exportées dans : {output_path}")
                    st.download_button(
                        label="Télécharger les résultats",
                        data=open(output_path, 'rb').read(),
                        file_name="opportunites_maillage.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Aucune opportunité de maillage interne trouvée.")
        else:
            st.warning("Veuillez entrer des mots-clés dans la zone de texte.")

if __name__ == "__main__":
    main()
