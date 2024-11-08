import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse, urljoin
import time

# --- Configuration settings ---
site = "votre-site.fr"  # Remplacez par votre propre site
url = "https://www.google.fr/search"  # URL de recherche Google (modifiez pour votre locale)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                  "AppleWebKit/537.36 (KHTML, like Gecko) " +
                  "Chrome/91.0.4472.124 Safari/537.36"
}
delay_between_requests = 2  # Délai entre les requêtes pour éviter le blocage

# Fonction pour charger les mots-clés depuis le fichier uploadé
def load_keywords(file):
    try:
        keywords = [line.decode('utf-8').strip() for line in file if line.strip()]
        return keywords
    except Exception as e:
        st.error(f"Erreur lors du chargement des mots-clés : {e}")
        return []

# Fonction pour effectuer une recherche Google
def google_search(query, site=None, num_results=10):
    search_query = f'{query} site:{site}' if site else query
    params = {"q": search_query, "num": num_results}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        for g in soup.find_all('div', class_='tF2Cxc'):
            a_tag = g.find('a', href=True)
            if a_tag:
                link = a_tag['href']
                links.append(link)
        return links
    except requests.RequestException as e:
        st.warning(f"Erreur HTTP pendant la recherche Google pour '{query}': {e}")
        return []

# Fonction pour vérifier si une page source possède un lien vers la page cible avec le bon texte d’ancre
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
                return (True, 'Oui' if anchor_text == keyword_lower else 'Non')
        return (False, 'Non')
    except requests.RequestException:
        return (False, 'Non')
    except Exception:
        return (False, 'Non')

# Fonction pour détecter les opportunités de maillage interne
def detect_maillage(keywords, site):
    maillage_opportunities = []
    for idx, keyword in enumerate(keywords, start=1):
        st.write(f"[{idx}/{len(keywords)}] Recherche pour le mot-clé : {keyword}")
        links = google_search(keyword, site)

        if links:
            top_link = links[0]  # Le premier résultat (cible principale)
            for link in links[1:]:
                exists, anchor_optimized = check_existing_link(link, top_link, keyword)
                if not exists:
                    maillage_opportunities.append([keyword, link, top_link, "Ajouter un lien", 'Non Applicable'])
                elif anchor_optimized == 'Non':
                    maillage_opportunities.append([keyword, link, top_link, "Optimiser l'ancre", 'Non'])
        time.sleep(delay_between_requests)  # Pause pour éviter d'être bloqué
    return maillage_opportunities

# Fonction pour exporter les résultats en CSV
def export_to_csv(maillage_opportunities):
    df = pd.DataFrame(maillage_opportunities, columns=["Mot-Clé", "Page Source", "Page Cible", "Action Requise", "Anchor Optimisé"])
    return df

# Interface Streamlit
def main():
    st.title("Détection d'Opportunités de Maillage Interne")
    
    # Téléchargement du fichier de mots-clés
    uploaded_file = st.file_uploader("Télécharger un fichier de mots-clés (.txt)", type="txt")
    if uploaded_file:
        keywords = load_keywords(uploaded_file)
        
        if keywords:
            st.write(f"{len(keywords)} mots-clés chargés.")
            # Exécution de la détection de maillage
            maillage_opportunities = detect_maillage(keywords, site)

            # Affichage et export des résultats
            if maillage_opportunities:
                st.write("Opportunités de maillage détectées :")
                df = export_to_csv(maillage_opportunities)
                st.dataframe(df)

                # Bouton pour télécharger le CSV
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("Télécharger les opportunités en CSV", csv, "opportunites_maillage.csv", "text/csv", key='download-csv')
            else:
                st.write("Aucune opportunité de maillage interne trouvée.")

if __name__ == "__main__":
    main()
