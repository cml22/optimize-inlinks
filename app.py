import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urlparse, urljoin
import logging
import os

# --- Configuration settings (à modifier selon vos besoins) ---
keyword_file = 'motscles.txt'                     # Chemin vers le fichier de mots-clés
site = "webloom.fr"                               # Votre site (à changer)
output_file = 'opportunites_maillage.csv'         # Fichier de sortie pour les opportunités
url = "https://www.google.fr/search"              # URL de recherche Google (à adapter selon le pays)
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

# Charger les mots-clés depuis un fichier texte
def load_keywords(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
        logging.info(f"Loaded {len(keywords)} keywords from {file_path}")
        return keywords
    except FileNotFoundError:
        logging.error(f"Keyword file not found: {file_path}")
        raise
    except Exception as e:
        logging.error(f"Error loading keywords: {e}")
        raise

# Effectuer une recherche Google pour récupérer des résultats pour un mot-clé spécifique
def google_search(query, site=None, num_results=10):
    try:
        search_query = f'{query} site:{site}' if site else query
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
def detect_maillage(keywords, site):
    maillage_opportunities = []

    for idx, keyword in enumerate(keywords, start=1):
        print(f"[{idx}/{len(keywords)}] Recherche pour le mot-clé : {keyword}")
        logging.info(f"Processing keyword {idx}/{len(keywords)}: '{keyword}'")
        links = google_search(keyword, site)

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
        print(f"Opportunités de maillage interne exportées dans : {output_file}")
        logging.info(f"Exported {len(maillage_opportunities)} opportunities to '{output_file}'")
    except Exception as e:
        logging.error(f"Error exporting to CSV: {e}")
        raise

# Fonction principale
def main():
    # Supprimer le fichier de sortie s'il existe déjà
    if os.path.exists(output_file):
        os.remove(output_file)

    try:
        # Charger les mots-clés
        keywords = load_keywords(keyword_file)

        if not keywords:
            print(f"Aucun mot-clé trouvé dans {keyword_file}.")
            logging.warning(f"No keywords found in '{keyword_file}'. Exiting.")
            return

        # Détecter les opportunités de maillage interne
        maillage_opportunities = detect_maillage(keywords, site)

        if maillage_opportunities:
            # Exporter les résultats vers un fichier CSV
            export_to_csv(maillage_opportunities, output_file)
        else:
            print("Aucune opportunité de maillage interne trouvée.")
            logging.info("No linking opportunities found.")
    except Exception as e:
        print(f"Une erreur est survenue : {e}")
        logging.critical(f"Critical error in main: {e}")

if __name__ == "__main__":
    main()
