import streamlit as st
import pandas as pd
import json
import time
from utils.gkp_processing import process_gkp_csv
from utils.gsheet_sync import connect_to_gsheet, update_unfiltered_tab, create_simplified_layering_tab, add_match_formulas
from utils.prompts import generate_traffic_clustering_prompt
from utils.ui_components import show_progress, render_deduplication_step, render_dual_csv_upload

st.set_page_config(page_title="Traffic Blog", page_icon="📊", layout="wide")

# Initialize session state
if 'traffic_step' not in st.session_state:
    st.session_state.traffic_step = 1
if 'traffic_keywords_df' not in st.session_state:
    st.session_state.traffic_keywords_df = None
if 'traffic_topic' not in st.session_state:
    st.session_state.traffic_topic = ""
if 'traffic_brand_name' not in st.session_state:
    st.session_state.traffic_brand_name = ""

st.title("Traffic Blog Workflow")
st.caption("'Best X in UAE' - Drive traffic through broad commercial searches")

if st.button("← Back to Home"):
    st.switch_page("main.py")

st.markdown("---")

# Progress indicator
show_progress(
    st.session_state.traffic_step,
    4,
    ["Upload & Configure", "Deduplication", "AI Clustering", "Generate Output"]
)

# Step 1: Upload & Configure
if st.session_state.traffic_step >= 1:
    st.header("Step 1: Upload & Configure")
    
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_df = render_dual_csv_upload(step_key="traffic")
        if uploaded_df is not None:
            st.session_state.traffic_keywords_df = uploaded_df
    
    with col2:
        st.session_state.traffic_topic = st.text_input(
            "Content Topic", 
            value=st.session_state.traffic_topic,
            placeholder="e.g., Best Hair Serums in UAE"
        )
        
        st.session_state.traffic_brand_name = st.text_input(
            "Brand Name (optional - for filtering)",
            value=st.session_state.traffic_brand_name,
            placeholder="e.g., QYUBIC"
        )
        
        with st.expander("Google Sheets Setup (Optional)"):
            creds_file = st.file_uploader("Service Account JSON", type=['json'], key='traffic_creds_upload')
            sheet_url = st.text_input(
                "Google Sheet URL", 
                key="traffic_sheet_url_input",
                value=st.session_state.get('traffic_sheet_url', '')
            )
            if creds_file and sheet_url:
                try:
                    creds_data = json.load(creds_file)
                    st.session_state.traffic_gsheet_creds = creds_data
                    st.session_state.traffic_sheet_url = sheet_url
                    st.success("✓ Google Sheets configured")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    button_disabled = st.session_state.traffic_keywords_df is None or not st.session_state.traffic_topic
    if button_disabled:
        st.warning("Upload at least one CSV and enter topic to continue")
    
    if st.button("Continue →", type="primary", disabled=button_disabled, key="traffic_step1_continue"):
        st.session_state.traffic_step = 2
        st.rerun()

# Step 2: Deduplication
if st.session_state.traffic_step >= 2:
    st.markdown("---")
    
    show_progress(st.session_state.traffic_step, 4, ["Upload & Configure", "Deduplication", "AI Clustering", "Generate Output"])
    
    cleaned_df, dedup_data = render_deduplication_step(
        st.session_state.traffic_keywords_df,
        brand_name=st.session_state.traffic_brand_name if st.session_state.traffic_brand_name else None,
        step_key="traffic"
    )
    
    if cleaned_df is not None:
        st.session_state.traffic_keywords_df = cleaned_df
        st.session_state.traffic_dedup_data = dedup_data
    
    if st.button("Continue to Clustering →", type="primary", key="traffic_step2_continue"):
        if 'traffic_dedup_data' not in st.session_state:
            st.warning("Please apply deduplication first")
        else:
            st.session_state.traffic_step = 3
            st.rerun()

# Step 3: AI Clustering
if st.session_state.traffic_step >= 3:
    st.markdown("---")
    
    show_progress(st.session_state.traffic_step, 4, ["Upload & Configure", "Deduplication", "AI Clustering", "Generate Output"])
    
    st.header("Step 3: AI Clustering")
    
    clustering_prompt = generate_traffic_clustering_prompt(
        st.session_state.traffic_topic,
        st.session_state.traffic_keywords_df['Keyword'].tolist(),
        st.session_state.traffic_brand_name
    )
    
    st.subheader("Copy to ChatGPT:")
    st.code(clustering_prompt, language=None)
    
    st.markdown("---")
    st.subheader("Paste Response:")
    
    cluster_response = st.text_area("JSON from ChatGPT", height=300, key="traffic_cluster_json")
    
    parse_button = st.button("Parse & Preview", type="secondary", key="traffic_parse_clusters")
    
    if parse_button and cluster_response:
        try:
            clusters = json.loads(cluster_response)
            st.success(f"✓ Parsed {len(clusters.get('clusters', []))} clusters")
            
            with st.expander("Preview Clusters", expanded=True):
                for cluster in clusters.get('clusters', []):
                    st.write(f"**{cluster.get('cluster_name')}** - {cluster.get('role')}")
                    
                    keywords = cluster.get('keywords', [])
                    high_count = sum(1 for kw in keywords if kw.get('priority') == 'HIGH')
                    med_count = sum(1 for kw in keywords if kw.get('priority') == 'MEDIUM')
                    low_count = sum(1 for kw in keywords if kw.get('priority') == 'LOW')
                    ai_count = sum(1 for kw in keywords if kw.get('source') == 'AI Suggested')
                    
                    st.caption(f"{cluster.get('placement')} | HIGH: {high_count}, MED: {med_count}, LOW: {low_count} | AI Suggested: {ai_count}")
                
                if clusters.get('missing_faq_opportunities'):
                    st.write("**Missing FAQ Opportunities:**")
                    for faq in clusters.get('missing_faq_opportunities', [])[:5]:
                        st.write(f"• {faq}")
            
            st.session_state.traffic_clusters = clusters
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
    
    generate_disabled = 'traffic_clusters' not in st.session_state
    if generate_disabled and cluster_response:
        st.info("Click 'Parse & Preview' first")
    elif generate_disabled:
        st.info("Paste JSON response above")
    
    if st.button("Generate Output →", type="primary", disabled=generate_disabled, key="traffic_step3_continue"):
        st.session_state.traffic_step = 4
        st.rerun()

# Step 4: Generate Output
if st.session_state.traffic_step >= 4:
    st.markdown("---")
    
    show_progress(st.session_state.traffic_step, 4, ["Upload & Configure", "Deduplication", "AI Clustering", "Generate Output"])
    
    st.header("Step 4: Generate Output")
    
    if st.session_state.traffic_clusters:
        # Create CSV data
        layering_data = []
        for cluster in st.session_state.traffic_clusters.get('clusters', []):
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
        
        st.subheader("Preview:")
        st.dataframe(layering_df, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            csv = layering_df.to_csv(index=False)
            st.download_button("↓ Download Layering CSV", csv, "layering.csv", "text/csv", key="traffic_download_layering")
        with col2:
            unfiltered_csv = st.session_state.traffic_keywords_df.to_csv(index=False)
            st.download_button("↓ Download Unfiltered CSV", unfiltered_csv, "unfiltered.csv", "text/csv", key="traffic_download_unfiltered")
        
        # Google Sheets Sync
        if hasattr(st.session_state, 'traffic_gsheet_creds') and hasattr(st.session_state, 'traffic_sheet_url'):
            st.markdown("---")
            if st.button("Sync to Google Sheets", type="primary", key="traffic_sync"):
                with st.spinner("Syncing to Google Sheets..."):
                    try:
                        sheet = connect_to_gsheet(st.session_state.traffic_gsheet_creds, st.session_state.traffic_sheet_url)
                        
                        with st.spinner("1/3: Updating UnfilteredKeywords tab..."):
                            update_unfiltered_tab(sheet, st.session_state.traffic_keywords_df)
                            time.sleep(1)
                            st.success("✓ UnfilteredKeywords tab updated")
                        
                        with st.spinner("2/3: Creating Layers tab..."):
                            create_simplified_layering_tab(sheet, st.session_state.traffic_clusters, st.session_state.traffic_keywords_df)
                            time.sleep(1)
                            st.success("✓ Layers tab created")
                        
                        with st.spinner("3/3: Adding Match formulas..."):
                            add_match_formulas(sheet, st.session_state.traffic_keywords_df)
                            st.success("✓ Match formulas added")
                        
                        st.balloons()
                        st.success("Sync complete!")
                        st.markdown(f"[Open Google Sheet]({st.session_state.traffic_sheet_url})")
                        
                    except Exception as e:
                        st.error(f"Sync error: {e}")
        else:
            st.info("Configure Google Sheets in Step 1 to enable syncing")
    
    if st.button("Start Over", key="traffic_restart"):
        for key in list(st.session_state.keys()):
            if key.startswith('traffic_'):
                del st.session_state[key]
        st.session_state.traffic_step = 1
        st.rerun()