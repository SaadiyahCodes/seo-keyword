import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from io import StringIO

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
    st.session_state.blog_type = "general"

def process_gkp_csv(csv_file):
    """Process GKP CSV: skip first 2 rows, extract Keyword & Volume columns"""
    # GKP exports are UTF-16 encoded with tab separators
    df = pd.read_csv(
        csv_file,
        encoding="utf-16",
        sep="\t",
        skiprows=2
    )
    
    # Clean column names (remove BOM and whitespace)
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace("\ufeff", "", regex=True)
    )
    
    # Find the correct columns dynamically
    keyword_col = [c for c in df.columns if "keyword" in c][0]
    volume_col = [c for c in df.columns if "avg" in c or "search" in c][0]
    
    # Extract only relevant columns
    df_clean = df[[keyword_col, volume_col]].copy()
    df_clean.columns = ['Keyword', 'Volume']
    
    # Clean keywords
    df_clean['Keyword'] = df_clean['Keyword'].astype(str).str.strip()
    
    # Remove any empty rows
    df_clean = df_clean.dropna(subset=['Keyword'])
    df_clean = df_clean[df_clean['Keyword'] != 'nan']
    
    # Deduplicate keywords
    df_clean = df_clean.drop_duplicates(subset=['Keyword'], keep='first')
    
    # Convert Volume to numeric, handle any non-numeric values
    df_clean['Volume'] = pd.to_numeric(df_clean['Volume'], errors='coerce').fillna(0).astype(int)
    
    return df_clean

def connect_to_gsheet(credentials_dict, sheet_url):
    """Connect to Google Sheets using service account credentials"""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Open the sheet
    sheet = client.open_by_url(sheet_url)
    return sheet

def update_unfiltered_tab(sheet, df):
    """Update the Unfiltered Keyword List tab"""
    try:
        worksheet = sheet.worksheet("UnfilteredKeywords")
    except:
        worksheet = sheet.add_worksheet(title="UnfilteredKeywords", rows=len(df)+10, cols=3)
    
    # Clear existing content
    worksheet.clear()
    
    # Set headers
    worksheet.update('A1:C1', [['Keyword', 'Volume', 'Match']])
    
    # Update keywords and volumes
    data = df[['Keyword', 'Volume']].values.tolist()
    worksheet.update(f'A2:B{len(data)+1}', data)
    
    # Add Match formula for all rows at once
    if len(data) > 0:
        match_formulas = [[f'=COUNTIF(Layers!B:B,A{i})'] for i in range(2, len(data) + 2)]
        worksheet.update(range_name=f'C2:C{len(data)+1}', values=match_formulas, value_input_option='USER_ENTERED')
    
    return True

def create_layering_tab(sheet, clusters_dict, unfiltered_df):
    """Create or update the Layering tab with clustered keywords"""
    try:
        worksheet = sheet.worksheet("Layers")
        worksheet.clear()
    except:
        worksheet = sheet.add_worksheet(title="Layers", rows=1000, cols=6)
    
    # Set headers
    headers = ['Sub-Intent Layer', 'Keyword', 'Volume', 'K.D', 'Type', 'Notes']
    worksheet.update('A1:F1', [headers])
    
    # Format header row
    worksheet.format('A1:F1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })
    
    current_row = 2
    
    # Process each cluster
    for cluster_name, keywords in clusters_dict.items():
        # Prepare cluster data (header + keywords + formulas)
        cluster_data = []
        
        # Cluster header row
        cluster_data.append([cluster_name, '', '', '', '', ''])
        
        # Keyword rows with VLOOKUP formulas
        for keyword in keywords:
            cluster_data.append(['', keyword, f'=VLOOKUP(B{current_row+1},UnfilteredKeywords!A:B,2,FALSE)', '', '', ''])
            current_row += 1
        
        # Write entire cluster at once
        start_row = current_row - len(keywords)
        worksheet.update(range_name=f'A{start_row}:F{current_row}', values=cluster_data, value_input_option='USER_ENTERED')
        
        # Format cluster header
        worksheet.format(f'A{start_row}:F{start_row}', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.85, 'green': 0.92, 'blue': 0.95}
        })
        
        # Add visual separator (border) after each cluster
        worksheet.format(f'A{current_row}:F{current_row}', {
            'borders': {
                'bottom': {'style': 'SOLID_MEDIUM', 'color': {'red': 0, 'green': 0, 'blue': 0}}
            }
        })
        
        current_row += 1
    
    return True

# Main App
st.title("🔍 SEO Keyword Clustering Tool")
st.markdown("---")

# Step 1: Upload CSV and Configure
if st.session_state.step >= 1:
    st.header("Step 1: Upload GKP Export & Configure")
    
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file = st.file_uploader("Upload GKP CSV Export", type=['csv'])
        
        if uploaded_file:
            try:
                df = process_gkp_csv(uploaded_file)
                st.session_state.keywords_df = df
                st.success(f"✅ Processed {len(df)} unique keywords")
                st.dataframe(df.head(10), use_container_width=True)
            except Exception as e:
                st.error(f"Error processing CSV: {e}")
    
    with col2:
        st.session_state.topic = st.text_input("Content Topic/Title", value=st.session_state.topic, 
                                                placeholder="e.g., Best Hydrating Cleansers in UAE")
        
        st.session_state.blog_type = st.selectbox("Blog Type", ["general", "brand blog"])
        
        if st.session_state.blog_type == "brand blog":
            st.session_state.brand_name = st.text_input("Brand Name", value=st.session_state.brand_name)
        
        # Google Sheets Configuration
        with st.expander("🔧 Google Sheets Setup (Optional - for auto-sync)"):
            st.info("To enable automatic Google Sheets sync, you'll need to upload your service account credentials JSON file.")
            
            creds_file = st.file_uploader("Upload Service Account JSON", type=['json'], key='creds_upload')
            sheet_url = st.text_input("Google Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...")
            
            if creds_file and sheet_url:
                try:
                    # Read file content only when file changes
                    creds_data = json.load(creds_file)
                    st.session_state.gsheet_creds = creds_data
                    st.session_state.sheet_url = sheet_url
                    st.success("✅ Google Sheets configured!")
                except Exception as e:
                    st.error(f"Error loading credentials: {e}")
    
    # Show button always but disable if requirements not met
    button_disabled = st.session_state.keywords_df is None or not st.session_state.topic
    
    if button_disabled:
        st.warning("⚠️ Please upload a CSV file and enter a topic to continue")
    
    if st.button("Continue to AI Clustering →", type="primary", disabled=button_disabled):
        st.session_state.step = 2
        st.rerun()

# Step 2: AI Clustering (Human Intervention)
if st.session_state.step >= 2:
    st.markdown("---")
    st.header("Step 2: AI Clustering (ChatGPT)")
    
    # Generate the prompt
    brand_clause = f"besides {st.session_state.brand_name}" if st.session_state.blog_type == "brand blog" and st.session_state.brand_name else ""
    
    chatgpt_prompt = f"""You are an SEO expert for a discount savings startup in UAE doing keyword search. Group these keywords into 6-8 sub-intent layers which identify the main problems or user pain points which will form our content outline or be covered to enrich the outline. 

Use short, clear cluster or sub-intent layer names (2–5 words max). Return the cluster names with the exact keyword names. 

FILTER OUT these low-value keywords:
- Time-based variants (7 day, 30 day, weekly, monthly, etc.) unless the time period is the core intent
- Generic location modifiers (near me, in my area, etc.)
- Ultra-specific brand combinations that aren't relevant
- Keywords with brand names [{brand_clause if brand_clause else "not applicable"}]
- Other irrelevant intent keywords

KEEP high-value keywords that represent:
- Core user problems or pain points
- Specific dietary needs or health conditions
- Product features or service types
- Clear purchase or research intent

This is the topic it has to be relevant to: {st.session_state.topic}

Keywords to cluster:
{', '.join(st.session_state.keywords_df['Keyword'].tolist())}

Return ONLY a JSON object in this format (no markdown, no explanation):
{{
  "Cluster Name 1": ["keyword1", "keyword2"],
  "Cluster Name 2": ["keyword3", "keyword4"]
}}"""
    
    st.subheader("📋 Copy this prompt to ChatGPT:")
    st.code(chatgpt_prompt, language=None)
    
    # Use a text area for easy copying
    st.text_area("Click in the box and Ctrl+A, Ctrl+C to copy:", chatgpt_prompt, height=100, key="prompt_copy")
    
    st.markdown("---")
    st.subheader("📥 Paste ChatGPT's Response Here:")
    
    chatgpt_response = st.text_area("Paste the JSON response from ChatGPT", height=300, 
                                     placeholder='{"Hydrating Cleansers": ["hydrating cleanser", "gentle cleanser"], ...}')
    
    if chatgpt_response:
        try:
            # Parse JSON response
            clusters = json.loads(chatgpt_response)
            st.success(f"✅ Parsed {len(clusters)} clusters successfully!")
            
            # Preview clusters
            with st.expander("Preview Clusters"):
                for cluster_name, keywords in clusters.items():
                    st.write(f"**{cluster_name}** ({len(keywords)} keywords)")
                    st.write(", ".join(keywords[:5]) + ("..." if len(keywords) > 5 else ""))
            
            st.session_state.clusters = clusters
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format. Please make sure ChatGPT returned valid JSON. Error: {e}")
    
    # Show button always but disable if no valid JSON parsed
    generate_disabled = not chatgpt_response or 'clusters' not in st.session_state
    
    if generate_disabled and chatgpt_response:
        st.warning("⚠️ Please paste valid JSON from ChatGPT above")
    elif generate_disabled:
        st.info("💡 Paste ChatGPT's JSON response above to continue")
    
    if st.button("Generate Layering Tab →", type="primary", disabled=generate_disabled):
        st.session_state.step = 3
        st.rerun()

# Step 3: Generate Final Output
if st.session_state.step >= 3:
    st.markdown("---")
    st.header("Step 3: Generate Layering Tab")
    
    # Option to download as CSV
    if st.session_state.clusters:
        # Create layering dataframe
        layering_data = []
        for cluster_name, keywords in st.session_state.clusters.items():
            # Add cluster header
            layering_data.append({
                'Sub-Intent Layer': cluster_name,
                'Keyword': '',
                'Volume': '',
                'K.D': '',
                'Type': '',
                'Notes': ''
            })
            
            # Add keywords
            for kw in keywords:
                # Get volume from original dataframe
                volume = st.session_state.keywords_df[
                    st.session_state.keywords_df['Keyword'] == kw
                ]['Volume'].values
                
                layering_data.append({
                    'Sub-Intent Layer': '',
                    'Keyword': kw,
                    'Volume': volume[0] if len(volume) > 0 else 0,
                    'K.D': '',
                    'Type': '',
                    'Notes': ''
                })
        
        layering_df = pd.DataFrame(layering_data)
        
        st.subheader("📊 Preview Layering Tab:")
        st.dataframe(layering_df, use_container_width=True)
        
        # Download options
        col1, col2 = st.columns(2)
        
        with col1:
            csv = layering_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Layering Tab (CSV)",
                data=csv,
                file_name="layering_tab.csv",
                mime="text/csv"
            )
        
        with col2:
            unfiltered_csv = st.session_state.keywords_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Unfiltered List (CSV)",
                data=unfiltered_csv,
                file_name="unfiltered_keywords.csv",
                mime="text/csv"
            )
        
        # Sync to Google Sheets
        if hasattr(st.session_state, 'gsheet_creds') and hasattr(st.session_state, 'sheet_url'):
            st.markdown("---")
            if st.button("🔄 Sync to Google Sheets", type="primary"):
                with st.spinner("Syncing to Google Sheets..."):
                    try:
                        sheet = connect_to_gsheet(st.session_state.gsheet_creds, st.session_state.sheet_url)
                        
                        # Update Unfiltered tab
                        update_unfiltered_tab(sheet, st.session_state.keywords_df)
                        st.success("✅ Updated 'Unfiltered Keyword List' tab")
                        
                        # Update Layering tab
                        create_layering_tab(sheet, st.session_state.clusters, st.session_state.keywords_df)
                        st.success("✅ Updated 'Layers' tab")
                        
                        st.balloons()
                        st.success("🎉 All done! Your Google Sheet is updated.")
                        
                    except Exception as e:
                        st.error(f"Error syncing to Google Sheets: {e}")
        else:
            st.info("💡 Configure Google Sheets credentials in Step 1 to enable auto-sync")
    
    if st.button("🔄 Start Over"):
        st.session_state.step = 1
        st.session_state.keywords_df = None
        st.session_state.clusters = None
        st.rerun()

# Sidebar
with st.sidebar:
    st.header("📚 How to Use")
    st.markdown("""
    **Step 1:** Upload GKP CSV
    - Export from Google Keyword Planner
    - Tool automatically processes it
    
    **Step 2:** AI Clustering
    - Copy the generated prompt
    - Paste in ChatGPT
    - Copy ChatGPT's JSON response back
    
    **Step 3:** Generate Output
    - Download CSVs or
    - Auto-sync to Google Sheets
    
    ---
    
    **Google Sheets Setup:**
    1. Create a Google Cloud project
    2. Enable Google Sheets API
    3. Create service account
    4. Download credentials JSON
    5. Share your sheet with service account email
    """)
    
    st.markdown("---")
    st.caption("Built for SEO keyword clustering workflow")