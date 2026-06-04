import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from io import StringIO
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus
import time

# Page config
st.set_page_config(page_title="SEO Keyword Clustering Tool", page_icon="🔍", layout="wide")

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'keywords_df' not in st.session_state:
    st.session_state.keywords_df = None
if 'topic' not in st.session_state:
    st.session_state.topic = ""
if 'brand_name' not in st.session_state:
    st.session_state.brand_name = ""
if 'blog_type' not in st.session_state:
    st.session_state.blog_type = "traffic"

def process_gkp_csv(csv_file):
    """Process GKP CSV: skip first 2 rows, extract Keyword & Volume columns"""
    df = pd.read_csv(csv_file, encoding="utf-16", sep="\t", skiprows=2)
    df.columns = df.columns.str.strip().str.lower().str.replace("\ufeff", "", regex=True)
    
    keyword_col = [c for c in df.columns if "keyword" in c][0]
    volume_col = [c for c in df.columns if "avg" in c or "search" in c][0]
    
    keywords = df[keyword_col].astype(str).str.strip().tolist()
    volumes = df[volume_col].astype(str).str.replace(',', '').str.replace(' ', '').str.strip().tolist()
    
    volumes_clean = []
    for v in volumes:
        try:
            volumes_clean.append(int(float(v)))
        except:
            volumes_clean.append(0)
    
    df_clean = pd.DataFrame({'Keyword': keywords, 'Volume': volumes_clean})
    df_clean = df_clean[df_clean['Keyword'].notna()]
    df_clean = df_clean[df_clean['Keyword'] != 'nan']
    df_clean = df_clean[df_clean['Keyword'] != '']
    df_clean = df_clean.drop_duplicates(subset=['Keyword'], keep='first')
    df_clean = df_clean.reset_index(drop=True)
    df_clean['Keyword'] = df_clean['Keyword'].astype(str)
    df_clean['Volume'] = df_clean['Volume'].astype('int64')
    
    return df_clean

def connect_to_gsheet(credentials_dict, sheet_url):
    """Connect to Google Sheets"""
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_url(sheet_url)

def update_unfiltered_tab(sheet, df):
    """Update UnfilteredKeywords tab"""
    try:
        worksheet = sheet.worksheet("UnfilteredKeywords")
        worksheet.clear()
    except:
        worksheet = sheet.add_worksheet(title="UnfilteredKeywords", rows=max(len(df)+100, 1000), cols=3)
    
    worksheet.update('A1:C1', [['Keyword', 'Volume', 'Match']])
    worksheet.format('A1:C1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })
    
    if len(df) > 0:
        data = df[['Keyword', 'Volume']].values.tolist()
        worksheet.update(f'A2:B{len(data)+1}', data)
    
    return worksheet

def create_simplified_layering_tab(sheet, clusters_data, unfiltered_df):
    """Create simplified Layering tab with keyword-level priority and lighter colors"""
    try:
        worksheet = sheet.worksheet("Layers")
        worksheet.clear()
    except:
        worksheet = sheet.add_worksheet(title="Layers", rows=2000, cols=7)
    
    headers = ['Sub-Intent Layer', 'Keyword', 'Volume', 'K.D', 'Priority', 'Source', 'Notes']
    worksheet.update('A1:G1', [headers])
    
    worksheet.format('A1:G1', {
        'textFormat': {'bold': True, 'fontSize': 11},
        'backgroundColor': {'red': 0.2, 'green': 0.3, 'blue': 0.5},
        'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
    })
    
    current_row = 2
    
    for cluster in clusters_data.get('clusters', []):
        cluster_name = cluster.get('cluster_name', 'Unnamed Cluster')
        role = cluster.get('role', '')
        placement = cluster.get('placement', '')
        coverage_notes = cluster.get('coverage_notes', '')
        keywords = cluster.get('keywords', [])
        
        cluster_data = []
        
        # Cluster header - all metadata in Notes column
        cluster_data.append([
            cluster_name, '', '', '', '', '',
            f"{role} | {placement} | {coverage_notes}"
        ])
        
        # Keywords with individual priorities
        for kw_obj in keywords:
            keyword = kw_obj.get('keyword', '')
            source = kw_obj.get('source', 'GKP')
            priority = kw_obj.get('priority', 'MEDIUM')
            
            cluster_data.append([
                '', keyword,
                f'=IFERROR(VLOOKUP(B{current_row+1},UnfilteredKeywords!A:B,2,FALSE),"-")',
                '', priority, source, ''
            ])
            current_row += 1
        
        start_row = current_row - len(keywords)
        worksheet.update(range_name=f'A{start_row}:G{current_row}', values=cluster_data, value_input_option='USER_ENTERED')
        
        # Cluster header - light blue-gray
        worksheet.format(f'A{start_row}:G{start_row}', {
            'textFormat': {'bold': True, 'fontSize': 11},
            'backgroundColor': {'red': 0.85, 'green': 0.92, 'blue': 0.95}
        })
        
        # Color keywords by priority - LIGHTER COLORS
        priority_colors = {
            'HIGH': {'red': 1.0, 'green': 0.85, 'blue': 0.85},    # Light pink
            'MEDIUM': {'red': 1.0, 'green': 0.95, 'blue': 0.8},   # Light yellow
            'LOW': {'red': 0.95, 'green': 0.95, 'blue': 0.95}     # Light gray
        }
        
        for idx, kw_obj in enumerate(keywords):
            row_num = start_row + 1 + idx
            kw_priority = kw_obj.get('priority', 'MEDIUM')
            bg_color = priority_colors.get(kw_priority, priority_colors['MEDIUM'])
            
            worksheet.format(f'A{row_num}:G{row_num}', {'backgroundColor': bg_color})
            
            if kw_obj.get('source') == 'AI Suggested':
                worksheet.format(f'B{row_num}:B{row_num}', {'textFormat': {'italic': True}})
        
        worksheet.format(f'A{current_row}:G{current_row}', {
            'borders': {'bottom': {'style': 'SOLID_MEDIUM', 'color': {'red': 0, 'green': 0, 'blue': 0}}}
        })
        
        current_row += 1
    
    # FAQ section
    faq_opportunities = clusters_data.get('missing_faq_opportunities', [])
    if faq_opportunities:
        current_row += 1
        worksheet.update(f'A{current_row}:G{current_row}', [[
            'MISSING FAQ OPPORTUNITIES', '', '', '', 'MEDIUM', 'AI Suggested',
            'Consider adding to FAQ section'
        ]])
        worksheet.format(f'A{current_row}:G{current_row}', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.85, 'green': 0.95, 'blue': 0.85}  # Light green
        })
        current_row += 1
        
        faq_data = [['', faq, '-', '', 'MEDIUM', 'AI Suggested', ''] for faq in faq_opportunities]
        worksheet.update(range_name=f'A{current_row}:G{current_row + len(faq_data) - 1}', values=faq_data, value_input_option='USER_ENTERED')
        
        for i in range(len(faq_data)):
            worksheet.format(f'A{current_row + i}:G{current_row + i}', {
                'backgroundColor': {'red': 0.95, 'green': 1.0, 'blue': 0.95}
            })
    
    return worksheet

def add_match_formulas(sheet, df):
    """Add Match formulas after Layers tab exists"""
    try:
        worksheet = sheet.worksheet("UnfilteredKeywords")
        if len(df) > 0:
            match_formulas = [[f'=COUNTIF(Layers!B:B,A{i})'] for i in range(2, len(df) + 2)]
            worksheet.update(range_name=f'C2:C{len(df)+1}', values=match_formulas, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        st.error(f"Error adding Match formulas: {e}")
        return False

def generate_improved_prompt(topic, keywords_list, blog_type, brand_name=""):
    """Generate improved prompt with deduplication and keyword-level priority"""
    
    brand_clause = f"besides {brand_name}" if brand_name else ""
    
    blog_instructions = {
        'traffic': "🎯 TRAFFIC BLOG: Broad commercial intent, comparisons, 'Best X' lists",
        'positioning': "🎯 POSITIONING BLOG: Brand + Problem solution, pain points, trust-building",
        'conversion': "🎯 CONVERSION BLOG: Remove objections, product validation, comparisons"
    }
    
    blog_context = blog_instructions.get(blog_type, blog_instructions['traffic'])
    
    prompt = f"""You are an SEO strategist for QYUBIC, a discount savings startup in UAE.

{blog_context}

TOPIC: {topic}

# CRITICAL TASKS:

## 1. DEDUPLICATE KEYWORDS FIRST
Remove duplicates where only word order changed:
- "cheap glasses online" vs "glasses online cheap" → KEEP ONLY ONE (more natural)
- "affordable prescription glasses" vs "prescription affordable glasses" → KEEP ONLY ONE
- Keep semantic variations: "cheap" vs "affordable" = BOTH (different words)

## 2. DETECT BRAND NAMES
Flag potential brands as LOW priority:
- "rx glasses" = might be RxGlasses brand → LOW
- "warby parker", "zenni optical" = brands → Remove or LOW
- [{brand_clause if brand_clause else "N/A"}] = Remove

## 3. CLUSTER BY USER PSYCHOLOGY
Group by: "What problem/anxiety is the user solving?"
Create 6-10 sub-intent clusters.

## 4. KEYWORD-LEVEL PRIORITY (CRITICAL!)
Assign priority to EACH keyword individually:

**HIGH**: Core intent, strong volume, clear need
**MEDIUM**: Supporting term, moderate value
**LOW**: Weak variation, potential brand, unclear intent, very low/no volume

Example:
- "cheap glasses online" → HIGH (strong intent)
- "affordable prescription glasses" → HIGH (strong intent)
- "discount eyeglasses online" → MEDIUM (synonym)
- "cheapest varifocal glasses" → LOW (too specific)
- "rx glasses" → LOW (possible brand)

## 5. ADD AI-SUGGESTED COVERAGE (ADD 3-5 PER MAJOR CLUSTER!)
Fill semantic gaps - concepts readers expect to see:

Eyeglasses: "PD measurement", "virtual try-on", "return policy", "lens types", "anti-reflective coating"
Skincare: "hyaluronic acid", "niacinamide", "UAE climate factors", "morning/night routine"
Electronics: "processor specs", "battery life", "warranty coverage", "gaming performance"

RULES:
- Add 3-5 per major cluster (not just 1!)
- Must be logically necessary
- Tag as "source": "AI Suggested"
- Set priority: HIGH if crucial, MEDIUM if supporting

## 6. OUTPUT JSON:
{{
  "clusters": [
    {{
      "cluster_name": "Online Ordering Anxiety",
      "role": "Core Pain Point",
      "placement": "H2",
      "keywords": [
        {{"keyword": "can i trust online eyewear", "source": "GKP", "priority": "HIGH"}},
        {{"keyword": "virtual try-on accuracy", "source": "AI Suggested", "priority": "HIGH"}},
        {{"keyword": "return policy glasses", "source": "AI Suggested", "priority": "HIGH"}},
        {{"keyword": "customer reviews", "source": "AI Suggested", "priority": "MEDIUM"}},
        {{"keyword": "fraud protection", "source": "AI Suggested", "priority": "MEDIUM"}}
      ],
      "coverage_notes": "Main user anxiety"
    }}
  ],
  "missing_faq_opportunities": [
    "What if glasses don't fit?",
    "Can I return prescription glasses?",
    "How accurate is virtual try-on?",
    "Do online glasses have warranties?",
    "How long for prescription verification?"
  ],
  "deduplication_notes": "Removed X duplicates"
}}

KEYWORDS TO CLUSTER:
{', '.join(keywords_list)}

RETURN ONLY VALID JSON. NO MARKDOWN, NO EXPLANATION."""
    
    return prompt

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
                st.warning("⚠️ No results. Try SerpAPI.")
            return results[:num_results] if results else None
        except Exception as e:
            st.error(f"Error: {e}")
            return None

def extract_headings_from_url(url):
    """Extract H1/H2"""
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

# Main App
st.title("🔍 SEO Keyword Clustering Tool")

if 'keywords_df' in st.session_state:
    if st.button("🗑️ Clear & Start Fresh"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.step = 1
        st.rerun()

st.markdown("---")

# Step 1
if st.session_state.step >= 1:
    st.header("Step 1: Upload & Configure")
    
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file = st.file_uploader("Upload GKP CSV", type=['csv'])
        if uploaded_file:
            try:
                df = process_gkp_csv(uploaded_file)
                st.session_state.keywords_df = df
                st.success(f"✅ {len(df)} keywords")
                st.table(df.head(10))
            except Exception as e:
                st.error(f"Error: {e}")
    
    with col2:
        st.session_state.topic = st.text_input("Content Topic", value=st.session_state.topic)
        
        blog_type_options = {
            "Traffic Blog": "traffic",
            "Positioning Blog": "positioning",
            "Conversion Blog": "conversion"
        }
        selected_blog_type = st.selectbox(
            "Blog Type",
            options=list(blog_type_options.keys()),
            index=list(blog_type_options.values()).index(st.session_state.blog_type)
        )
        st.session_state.blog_type = blog_type_options[selected_blog_type]
        
        blog_descriptions = {
            "traffic": "📊 'Best X in UAE' - brings traffic",
            "positioning": "🎯 Brand + Problem - builds trust",
            "conversion": "💰 Removes objections - drives sales"
        }
        st.info(blog_descriptions[st.session_state.blog_type])
        
        if st.session_state.blog_type == "positioning":
            st.session_state.brand_name = st.text_input("Brand Name", value=st.session_state.brand_name)
        
        with st.expander("🔧 Google Sheets Setup"):
            creds_file = st.file_uploader("Service Account JSON", type=['json'], key='creds')
            sheet_url = st.text_input("Sheet URL")
            if creds_file and sheet_url:
                try:
                    creds_data = json.load(creds_file)
                    st.session_state.gsheet_creds = creds_data
                    st.session_state.sheet_url = sheet_url
                    st.success("✅ Configured!")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    button_disabled = st.session_state.keywords_df is None or not st.session_state.topic
    if button_disabled:
        st.warning("⚠️ Upload CSV and enter topic")
    
    if st.button("Continue →", type="primary", disabled=button_disabled):
        st.session_state.step = 2
        st.rerun()

# Step 2
if st.session_state.step >= 2:
    st.markdown("---")
    st.header("Step 2: AI Clustering")
    
    chatgpt_prompt = generate_improved_prompt(
        st.session_state.topic,
        st.session_state.keywords_df['Keyword'].tolist(),
        st.session_state.blog_type,
        st.session_state.brand_name
    )
    
    st.subheader("📋 Copy to ChatGPT:")
    st.code(chatgpt_prompt, language=None)
    st.text_area("Click to copy:", chatgpt_prompt, height=100, key="prompt_copy")
    
    st.markdown("---")
    st.subheader("📥 Paste Response:")
    
    chatgpt_response = st.text_area("JSON from ChatGPT", height=300, key="chatgpt_json")
    
    parse_button = st.button("Parse & Preview", type="secondary")
    
    if parse_button and chatgpt_response:
        try:
            clusters = json.loads(chatgpt_response)
            st.success(f"✅ Parsed {len(clusters.get('clusters', []))} clusters!")
            
            with st.expander("Preview", expanded=True):
                for cluster in clusters.get('clusters', []):
                    st.write(f"**{cluster.get('cluster_name')}** - {cluster.get('role')}")
                    
                    keywords = cluster.get('keywords', [])
                    high_count = sum(1 for kw in keywords if kw.get('priority') == 'HIGH')
                    med_count = sum(1 for kw in keywords if kw.get('priority') == 'MEDIUM')
                    low_count = sum(1 for kw in keywords if kw.get('priority') == 'LOW')
                    ai_count = sum(1 for kw in keywords if kw.get('source') == 'AI Suggested')
                    
                    st.caption(f"📍 {cluster.get('placement')} | HIGH: {high_count}, MED: {med_count}, LOW: {low_count} | AI: {ai_count}")
                    
                if clusters.get('missing_faq_opportunities'):
                    st.write("**FAQs:**")
                    for faq in clusters.get('missing_faq_opportunities', [])[:5]:
                        st.write(f"• {faq}")
                
                if clusters.get('deduplication_notes'):
                    st.info(f"ℹ️ {clusters.get('deduplication_notes')}")
            
            st.session_state.enhanced_clusters = clusters
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
    
    generate_disabled = 'enhanced_clusters' not in st.session_state
    if generate_disabled and chatgpt_response:
        st.info("💡 Click 'Parse & Preview' first")
    elif generate_disabled:
        st.info("💡 Paste JSON above")
    
    if st.button("Generate Output →", type="primary", disabled=generate_disabled):
        st.session_state.step = 3
        st.rerun()

# Step 3
if st.session_state.step >= 3:
    st.markdown("---")
    st.header("Step 3: Generate Output")
    
    if st.session_state.enhanced_clusters:
        # CSV download
        layering_data = []
        for cluster in st.session_state.enhanced_clusters.get('clusters', []):
            layering_data.append({
                'Sub-Intent Layer': cluster.get('cluster_name'),
                'Role': cluster.get('role'),
                'Placement': cluster.get('placement'),
                'Keyword': '',
                'Priority': '',
                'Source': '',
                'Notes': cluster.get('coverage_notes', '')
            })
            
            for kw_obj in cluster.get('keywords', []):
                layering_data.append({
                    'Sub-Intent Layer': '',
                    'Role': '',
                    'Placement': '',
                    'Keyword': kw_obj.get('keyword'),
                    'Priority': kw_obj.get('priority', 'MEDIUM'),
                    'Source': kw_obj.get('source', 'GKP'),
                    'Notes': ''
                })
        
        layering_df = pd.DataFrame(layering_data)
        
        st.subheader("📊 Preview:")
        st.dataframe(layering_df, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            csv = layering_df.to_csv(index=False)
            st.download_button("📥 Download Layering CSV", csv, "layering.csv", "text/csv")
        with col2:
            unfiltered_csv = st.session_state.keywords_df.to_csv(index=False)
            st.download_button("📥 Download Unfiltered CSV", unfiltered_csv, "unfiltered.csv", "text/csv")
        
        # Sync
        if hasattr(st.session_state, 'gsheet_creds') and hasattr(st.session_state, 'sheet_url'):
            st.markdown("---")
            if st.button("🔄 Sync to Google Sheets", type="primary"):
                with st.spinner("Syncing..."):
                    try:
                        sheet = connect_to_gsheet(st.session_state.gsheet_creds, st.session_state.sheet_url)
                        
                        with st.spinner("1/3: UnfilteredKeywords..."):
                            update_unfiltered_tab(sheet, st.session_state.keywords_df)
                            time.sleep(1)
                            st.success("✅ 1/3")
                        
                        with st.spinner("2/3: Layers..."):
                            create_simplified_layering_tab(sheet, st.session_state.enhanced_clusters, st.session_state.keywords_df)
                            time.sleep(1)
                            st.success("✅ 2/3")
                        
                        with st.spinner("3/3: Formulas..."):
                            add_match_formulas(sheet, st.session_state.keywords_df)
                            st.success("✅ 3/3")
                        
                        st.balloons()
                        st.success("🎉 Done!")
                        st.markdown(f"[Open Sheet]({st.session_state.sheet_url})")
                        
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info("💡 Configure Google Sheets in Step 1")
    
    if st.button("🔄 Start Over"):
        st.session_state.step = 1
        st.rerun()

# Sidebar - SERP Tool
with st.sidebar:
    st.header("📚 Quick Guide")
    st.markdown("1. Upload CSV\n2. Copy to ChatGPT\n3. Generate output")
    
    st.markdown("---")
    st.subheader("🔍 SERP Research")
    
    with st.expander("⚙️ SerpAPI Setup"):
        st.markdown("100 free/month at [serpapi.com](https://serpapi.com)")
        serpapi_key = st.text_input("API Key", type="password", key="serpapi_key")
        if serpapi_key:
            st.session_state.serpapi_key = serpapi_key
            st.success("✅ Saved")
    
    serp_keyword = st.text_input("Keyword:", key="serp_kw")
    serp_num = st.number_input("Results:", 5, 20, 10, key="serp_num")
    
    if st.button("🔍 Scrape", type="primary", disabled=not serp_keyword):
        with st.spinner("Scraping..."):
            api_key = st.session_state.get('serpapi_key', None)
            serp_results = scrape_google_serp(serp_keyword, serp_num, serpapi_key=api_key)
            
            if not serp_results:
                st.error("❌ Failed")
                if not api_key:
                    st.warning("💡 Add API key")
            else:
                competitor_data = []
                progress = st.progress(0)
                
                for idx, result in enumerate(serp_results):
                    headings = extract_headings_from_url(result['url'])
                    competitor_data.append({
                        'URL': result['url'],
                        'Keyword': serp_keyword,
                        'H1/H2': headings['h1_h2_combined'],
                        'Notes': ''
                    })
                    progress.progress((idx + 1) / len(serp_results))
                    time.sleep(0.5)
                
                st.session_state.competitor_df = pd.DataFrame(competitor_data)
                progress.empty()
                st.success("✅ Done!")
    
    if 'competitor_df' in st.session_state and st.session_state.competitor_df is not None:
        st.success(f"📊 {len(st.session_state.competitor_df)} results")
        csv = st.session_state.competitor_df.to_csv(index=False)
        st.download_button("📥 Download", csv, f"serp_{serp_keyword}.csv", "text/csv")