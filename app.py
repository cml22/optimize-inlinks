import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urlparse, urljoin
import logging
from io import StringIO

# --- Documentation en Frontend ---
st.title("Outil de Détection d'Opportunités de Maillage Interne")
st.markdown("""
**Auteur** : Charles Migaud - Consultant SEO [https://charles-migaud.fr/consultant-seo-lille/]

### Objectif
Cet outil Streamlit est conçu pour détecter des opportunités de maillage interne sur un site Web spécifique, en s'appuyant sur une liste de mots-clés fournie par l'utilisateur. Il permet d'auditer la structure des liens internes pour chaque mot-clé et suggère des actions d'optimisation du maillage. Les utilisateurs peuvent analyser leurs pages Web pour s'assurer qu'elles sont correctement reliées, en fonction de chaque mot-clé, au sein d'un répertoire spécifique.

### Fonctionnement
1. **Entrée de l'utilisateur :**
   - **URL cible (répertoire)** : L'utilisateur spécifie l'URL du répertoire du site à analyser (par exemple, `https://www.exemple.com/fr/services/`).
   - **Liste de mots-clés** : L'utilisateur fournit une liste de mots-clés à analyser, un mot-clé par ligne.

2. **Recherche Google :** Pour chaque mot-clé, l'outil effectue une recherche Google avec la commande `site:` pour limiter les résultats au répertoire spécifié.
3. **Analyse des Liens :**
   - **Page cible (Top 1)** : La première page retournée (Top 1) pour chaque mot-clé est définie comme la "Page Cible" pour ce mot-clé.
   - **Opportunités de lien** : Pour chaque lien des résultats suivants, l'outil vérifie si ce lien contient déjà un lien vers la "Page Cible" :
     - **Ajouter un lien** : Si aucun lien n'existe entre la source et la cible, l'outil recommande d'ajouter un lien.
     - **Optimiser l'ancre** : Si le lien existe mais que l'ancre n'est pas optimisée avec le mot-clé, l'outil recommande d'optimiser l'ancre.

4. **Résultats** : L'outil génère un tableau récapitulatif des opportunités, incluant :
   - **Mot-Clé** : Le mot-clé associé à l'opportunité de lien.
   - **Page Source** : La page source potentielle pour le lien interne.
   - **Page Cible** : La page vers laquelle le lien interne devrait pointer.
   - **Action Requise** : Une action suggérée, soit "Ajouter un lien" si aucun lien n'existe, soit "Optimiser l'ancre" si le lien existe mais n'est pas optimisé.
   - **Anchor Optimisé** : Indique si l'ancre actuelle est optimisée ou non avec le mot-clé.

5. **Exportation** : Les utilisateurs peuvent télécharger un fichier CSV contenant toutes les opportunités détectées pour une analyse ou une utilisation ultérieure.
""")

# --- Configuration settings ---
output_file = 'opportunites_maillage.csv'
google_url = "https://www.google.com/search"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                  "AppleWebKit/537.36 (KHTML, like Gecko) " +
                  "Chrome/91.0.4472.124 Safari/537.36"
}
delay_between_requests = 2  # seconds

# Initialize logging
logging.basicConfig(
    filename='maillage_debug.log',
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
                    return (True, 'Oui')
                else:
                    return (True, 'Non')
        return (False, 'Non')
    except requests.RequestException as e:
        logging.warning(f"HTTP error accessing '{source_url}': {e}")
        return (False, 'Non')
    except Exception as e:
        logging.warning(f"Error parsing '{source_url}': {e}")
        return (False, 'Non')

# Detect linking opportunities by linking all pages to the top 1 result
def detect_maillage(keywords, site_url):
    maillage_opportunities = []

    for idx, keyword in enumerate(keywords, start=1):
        logging.info(f"Processing keyword {idx}/{len(keywords)}: '{keyword}'")
        links = google_search(keyword, site_url)

        if links:
            top_link = links[0]
            for link in links[1:]:
                exists, anchor_optimized = check_existing_link(link, top_link, keyword)
                if not exists:
                    maillage_opportunities.append([keyword, link, top_link, "Ajouter un lien", 'Non Applicable'])
                    logging.info(f"Link opportunity: '{link}' → '{top_link}' for keyword '{keyword}' (Add Link)")
                elif anchor_optimized == 'Non':
                    maillage_opportunities.append([keyword, link, top_link, "Optimiser l'ancre", 'Non'])
                    logging.info(f"Anchor optimization needed: '{link}' links to '{top_link}' with non-optimized anchor for keyword '{keyword}'")
        else:
            logging.info(f"No links found for keyword '{keyword}'.")

        time.sleep(delay_between_requests)

    return maillage_opportunities

# Streamlit UI and execution
st.write("### Veuillez entrer les informations ci-dessous pour lancer l'analyse.")

site_url = st.text_input("Entrez l'URL du site cible pour la commande `site:`")
keywords_input = st.text_area("Mots-clés (un par ligne)")
if st.button("Lancer l'analyse"):
    if not keywords_input or not site_url:
        st.warning("Veuillez entrer une URL et des mots-clés.")
    else:
        keywords = [line.strip() for line in keywords_input.splitlines() if line.strip()]
        opportunities = detect_maillage(keywords, site_url)
        
        if opportunities:
            df = pd.DataFrame(opportunities, columns=["Mot-Clé", "Page Source", "Page Cible", "Action Requise", "Anchor Optimisé"])
            st.dataframe(df)

            # Provide download link
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Télécharger les résultats en CSV",
                data=csv,
                file_name=output_file,
                mime="text/csv"
            )
        else:
            st.write("Aucune opportunité de maillage interne trouvée.")
