import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import time

st.set_page_config(page_title="SERP Research", page_icon="🔍", layout="wide")

st.title("SERP Competitor Research")
st.caption("Analyze top competitors for any keyword - independent tool")

if st.button("← Back to Home"):
    st.switch_page("main.py")

st.markdown("---")

# Initialize session state
if 'serp_results' not in st.session_state:
    st.session_state.serp_results = None
if 'competitor_df' not in st.session_state:
    st.session_state.competitor_df = None

def scrape_google_serp(keyword, num_results=10, serpapi_key=None):
    """Scrape SERP"""
    if serpapi_key:
        try:
            params = {"q": keyword, "num": num_results, "api_key": serpapi_key, "engine": "google", "gl": "ae", "hl": "en"}
            response = requests.get("https://serpapi.com/search", params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            results = [{'title': r.get('title', ''), 'url': r.get('link', '')} for r in data.get('organic_results', [])[:num_results]]
            return results if results else None
        except Exception as e:
            st.error(f"SerpAPI error: {e}")
            return None
    else:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        search_url = f"https://www.google.com/search?q={quote_plus(keyword)}&num={num_results}&gl=ae"
        try:
            session = requests.Session()
            response = session.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            search_divs = soup.find_all('div', class_='g') or soup.select('div.Gx5Zad')
            
            for g in search_divs:
                title_elem = g.find('h3')
                title = title_elem.get_text(strip=True) if title_elem else ''
                link_elem = g.find('a')
                url = ''
                if link_elem and 'href' in link_elem.attrs:
                    url = link_elem['href']
                    if url.startswith('/url?q='):
                        url = url.split('/url?q=')[1].split('&')[0]
                    elif url.startswith('/search'):
                        continue
                if url and title and url.startswith('http'):
                    results.append({'title': title, 'url': url})
            
            if not results:
                st.warning("No results found. Try using SerpAPI.")
            return results[:num_results] if results else None
        except Exception as e:
            st.error(f"Scraping error: {e}")
            return None

def extract_headings_from_url(url):
    """Extract H1/H2 from URL"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        h1_tags = [h1.get_text(strip=True) for h1 in soup.find_all('h1')]
        h2_tags = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
        return {'h1': h1_tags, 'h2': h2_tags, 'h1_h2_combined': ', '.join(h1_tags + h2_tags)}
    except Exception as e:
        return {'h1': [], 'h2': [], 'h1_h2_combined': f'Error: {str(e)}'}

# Main UI
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Keyword Research")
    
    serp_keyword = st.text_input(
        "Keyword to research:",
        placeholder="e.g., airport assistance dubai",
        key="serp_keyword"
    )
    
    serp_num = st.slider(
        "Number of results to scrape:",
        min_value=5,
        max_value=20,
        value=10,
        key="serp_num"
    )

with col2:
    st.header("SerpAPI Setup")
    
    with st.expander("Configure SerpAPI (Optional)"):
        st.caption("Get 100 free searches/month at [serpapi.com](https://serpapi.com)")
        serpapi_key = st.text_input("API Key", type="password", key="serpapi_key")
        if serpapi_key:
            st.session_state.serpapi_key = serpapi_key
            st.success("✓ API key saved")

st.markdown("---")

if st.button("Scrape SERP", type="primary", disabled=not serp_keyword, key="scrape_serp"):
    with st.spinner(f"Scraping top {serp_num} results for '{serp_keyword}'..."):
        api_key = st.session_state.get('serpapi_key', None)
        serp_results = scrape_google_serp(serp_keyword, serp_num, serpapi_key=api_key)
        
        if not serp_results:
            st.error("Failed to scrape results")
            if not api_key:
                st.warning("Consider adding a SerpAPI key for more reliable results")
        else:
            st.session_state.serp_results = serp_results
            
            competitor_data = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, result in enumerate(serp_results):
                status_text.text(f"Extracting headings from result {idx + 1}/{len(serp_results)}...")
                headings = extract_headings_from_url(result['url'])
                competitor_data.append({
                    'URL': result['url'],
                    'Title': result['title'],
                    'Keyword': serp_keyword,
                    'H1/H2': headings['h1_h2_combined'],
                    'Notes': ''
                })
                progress_bar.progress((idx + 1) / len(serp_results))
                time.sleep(0.5)  # Be polite to servers
            
            st.session_state.competitor_df = pd.DataFrame(competitor_data)
            progress_bar.empty()
            status_text.empty()
            st.success(f"✓ Scraped {len(serp_results)} results")

# Display results
if st.session_state.competitor_df is not None and not st.session_state.competitor_df.empty:
    st.markdown("---")
    st.header("Results")
    
    st.dataframe(st.session_state.competitor_df, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        csv = st.session_state.competitor_df.to_csv(index=False)
        st.download_button(
            "↓ Download CSV",
            csv,
            f"serp_{serp_keyword.replace(' ', '_')}.csv",
            "text/csv",
            key="download_serp_csv"
        )
    
    with col2:
        if st.button("Clear Results", key="clear_serp"):
            st.session_state.serp_results = None
            st.session_state.competitor_df = None
            st.rerun()