import streamlit as st
import pandas as pd
import json
import time
from utils.gkp_processing import process_gkp_csv
from utils.gsheet_sync import connect_to_gsheet, update_unfiltered_tab, create_simplified_layering_tab, add_match_formulas
from utils.prompts import generate_conversion_clustering_prompt, generate_conversion_deduplication_prompt
from utils.ui_components import show_progress, render_dual_csv_upload

st.set_page_config(page_title="Conversion Blog", page_icon="💰", layout="wide")

if 'conv_step' not in st.session_state:
    st.session_state.conv_step = 1
if 'conv_product_context' not in st.session_state:
    st.session_state.conv_product_context = {}
if 'conv_keywords_df' not in st.session_state:
    st.session_state.conv_keywords_df = None
if 'conv_clusters' not in st.session_state:
    st.session_state.conv_clusters = {}

st.title("Conversion Blog Workflow")
st.caption("Remove objections - Drive sales through product validation")

if st.button("← Back to Home"):
    st.switch_page("main.py")

st.markdown("---")

show_progress(
    st.session_state.conv_step, 5,
    ["Product Context", "GKP Upload", "Deduplication", "Clustering", "Output"]
)

#step 1: product context input
if st.session_state.conv_step >=1:
    st.header("Step 1: Product Context")
    col1, col2 = st.columns(2)

    with col1:
        product_name = st.text_input(
            "Product Name*",
            value=st.session_state.conv_product_context.get('product_name', ''),
            placeholder="e.g., The Body Shop Vitamin C Serum"
        )
        
        brand_name = st.text_input(
            "Brand Name*",
            value=st.session_state.conv_product_context.get('brand_name', ''),
            placeholder="e.g., The Body Shop"
        )

        product_category = st.text_input(
            "Product Category*",
            value=st.session_state.conv_product_context.get('product_category', ''),
            placeholder="e.g., Face Serums, Wireless Earbuds, Running Shoes"
        )

    with col2:
        competitor_products = st.text_area(
            "Competitor Products (one per line)",
            value=st.session_state.conv_product_context.get('competitors_text', ''),
            placeholder="The Ordinary Vitamin C\nCeraVe Vitamin C\nLUSH Suncare",
            height=120
        )

        content_goal = st.text_input(
            "Content Goal*",
            value=st.session_state.conv_product_context.get('content_goal', ''),
            placeholder="e.g., Is [Product] worth buying? [Product] vs competitors",
        )

    with st.expander("Product Research Notes (Optional)"):
        st.caption("paste product specs, customer reviews, common complaints, FAQs")
        product_notes = st.text_area(
            "Research notes",
            value=st.session_state.conv_product_context.get('product_notes', ''),
            height=150,
            placeholder="Common reviews: 'works well but pricey', Specs: 15ml bottle, Price: AED 145"
        )

    #save context
    if st.button("Save Product Context", type="secondary", key="save_product_context"):
        st.session_state.conv_product_context = {
            'product_name': product_name,
            'brand_name': brand_name,
            'product_category': product_category,
            'competitor_products': [c.strip() for c in competitor_products.split('\n') if c.strip()],
            'competitors_text': competitor_products,
            'content_goal': content_goal,
            'product_notes': product_notes
        }
        st.success("✓ Product context saved")
    
    button_disabled = not product_name or not brand_name or not product_category or not content_goal
    if button_disabled:
        st.warning("Fill in required fields (marked with *) to continue")
    
    if st.button("Continue →", type="primary", disabled=button_disabled, key="conv_step1_continue"):
        if not st.session_state.conv_product_context:
            st.session_state.conv_product_context = {
                'product_name': product_name,
                'brand_name': brand_name,
                'product_category': product_category,
                'competitor_products': [c.strip() for c in competitor_products.split('\n') if c.strip()],
                'competitors_text': competitor_products,
                'content_goal': content_goal,
                'product_notes': product_notes
            }
        st.session_state.conv_step = 2
        st.rerun()

# Step 2: GKP Upload
if st.session_state.conv_step >= 2:
    st.markdown("---")
    
    show_progress(st.session_state.conv_step, 5,
                 ["Product Context", "GKP Upload", "Deduplication", "Clustering", "Output"])
    
    st.header("Step 2: Upload Keyword Data")
    
    st.info(
        "Search for your product name, brand + product, competitor products, and objection keywords "
        "in Google Keyword Planner or Semrush. Export the CSV and upload it here."
    )
    
    uploaded_df = render_dual_csv_upload(step_key="conv")
    if uploaded_df is not None:
        st.session_state.conv_keywords_df = uploaded_df
    
    with st.expander("Google Sheets Setup (Optional)"):
        creds_file = st.file_uploader("Service Account JSON", type=['json'], key='conv_creds_upload')
        sheet_url = st.text_input(
            "Google Sheet URL", 
            key="conv_sheet_url_input",
            value=st.session_state.get('conv_sheet_url', '')
        )
        if creds_file and sheet_url:
            try:
                creds_data = json.load(creds_file)
                st.session_state.conv_gsheet_creds = creds_data
                st.session_state.conv_sheet_url = sheet_url
                st.success("✓ Google Sheets configured")
            except Exception as e:
                st.error(f"Error: {e}")
    
    button_disabled = st.session_state.conv_keywords_df is None
    if button_disabled:
        st.warning("Upload at least one CSV to continue")
    
    if st.button("Continue →", type="primary", disabled=button_disabled, key="conv_step2_continue"):
        st.session_state.conv_step = 3
        st.rerun()

# Step 3: Deduplication
if st.session_state.conv_step >= 3:
    st.markdown("---")
    
    show_progress(st.session_state.conv_step, 5,
                 ["Product Context", "GKP Upload", "Deduplication", "Clustering", "Output"])
    
    st.header("Step 3: Deduplication")
    
    st.info(
        "For conversion blogs, we KEEP brand name variations and meaningful product variations. "
        "We only remove exact duplicates and flag competitor products."
    )
    
    if st.button("Generate Deduplication Prompt", key="gen_dedup_conv"):
        dedup_prompt = generate_conversion_deduplication_prompt(
            st.session_state.conv_keywords_df['Keyword'].tolist(),
            st.session_state.conv_product_context.get('brand_name'),
            st.session_state.conv_product_context.get('product_name'),
            st.session_state.conv_product_context.get('competitor_products', [])
        )
        
        st.subheader("Copy to ChatGPT:")
        st.code(dedup_prompt, language=None)
        st.text_area("Click to copy:", dedup_prompt, height=100, key="dedup_prompt_copy_conv")
    
    st.markdown("---")
    st.subheader("Paste Response:")
    
    dedup_response = st.text_area(
        "JSON from ChatGPT", 
        height=300, 
        key="dedup_json_conv",
        placeholder='{\n  "kept_keywords": [...],\n  "removed": {...},\n  "competitor_keywords": [...],\n  "dedup_summary": "..."\n}'
    )
    
    if st.button("Apply Deduplication", type="secondary", key="apply_dedup_conv"):
        try:
            dedup_data = json.loads(dedup_response)
            
            # Filter dataframe to only kept keywords
            cleaned_df = st.session_state.conv_keywords_df[
                st.session_state.conv_keywords_df['Keyword'].isin(dedup_data['kept_keywords'])
            ].copy()
            
            st.session_state.conv_keywords_df = cleaned_df
            st.session_state.conv_dedup_data = dedup_data
            
            # Show summary
            with st.expander("Deduplication Summary", expanded=True):
                st.success(dedup_data['dedup_summary'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Kept", len(dedup_data['kept_keywords']))
                with col2:
                    st.metric("Exact Duplicates Removed", len(dedup_data['removed'].get('exact_duplicates', [])))
                with col3:
                    st.metric("Competitor Keywords", len(dedup_data.get('competitor_keywords', [])))
                
                if dedup_data['removed'].get('exact_duplicates'):
                    st.markdown("**Removed Exact Duplicates:**")
                    st.caption(', '.join(dedup_data['removed']['exact_duplicates'][:10]))
                
                if dedup_data.get('competitor_keywords'):
                    st.markdown("**Competitor Keywords (kept for comparison clusters):**")
                    st.caption(', '.join(dedup_data['competitor_keywords'][:10]))
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
    
    if st.button("Continue to Clustering →", type="primary", key="conv_step3_continue"):
        if 'conv_dedup_data' not in st.session_state:
            st.warning("Please apply deduplication first")
        else:
            st.session_state.conv_step = 4
            st.rerun()

# Step 4: AI Clustering
if st.session_state.conv_step >= 4:
    st.markdown("---")
    
    show_progress(st.session_state.conv_step, 5,
                 ["Product Context", "GKP Upload", "Deduplication", "Clustering", "Output"])
    
    st.header("Step 4: Conversion-Aware Clustering")
    
    st.info(
        "Clustering by OBJECTION TYPE to help remove purchase barriers. "
        "Examples: Price Concerns, Efficacy Doubts, Direct Comparisons, Safety/Side Effects."
    )
    
    clustering_prompt = generate_conversion_clustering_prompt(
        st.session_state.conv_product_context,
        st.session_state.conv_keywords_df['Keyword'].tolist()
    )
    
    st.subheader("Copy to ChatGPT:")
    st.code(clustering_prompt, language=None)
    st.text_area("Click to copy:", clustering_prompt, height=100, key="conv_cluster_prompt_copy")
    
    st.markdown("---")
    st.subheader("Paste Response:")
    
    cluster_response = st.text_area("JSON from ChatGPT", height=300, key="conv_cluster_json")
    
    parse_button = st.button("Parse & Preview", type="secondary", key="conv_parse_clusters")
    
    if parse_button and cluster_response:
        try:
            clusters = json.loads(cluster_response)
            st.success(f"✓ Parsed {len(clusters.get('clusters', []))} clusters")
            
            with st.expander("Preview Clusters", expanded=True):
                for cluster in clusters.get('clusters', []):
                    st.write(f"**{cluster.get('cluster_name')}**")
                    
                    if cluster.get('objection_type'):
                        st.caption(f"Objection: {cluster.get('objection_type')}")
                    
                    st.caption(f"Role: {cluster.get('role')} | Placement: {cluster.get('placement')}")
                    
                    keywords = cluster.get('keywords', [])
                    high_count = sum(1 for kw in keywords if kw.get('priority') == 'HIGH')
                    med_count = sum(1 for kw in keywords if kw.get('priority') == 'MEDIUM')
                    low_count = sum(1 for kw in keywords if kw.get('priority') == 'LOW')
                    ai_count = sum(1 for kw in keywords if kw.get('source') == 'AI Suggested')
                    
                    st.caption(f"Keywords: HIGH: {high_count}, MED: {med_count}, LOW: {low_count} | AI Suggested: {ai_count}")
                    st.markdown("---")
                
                if clusters.get('missing_faq_opportunities'):
                    st.write("**Missing FAQ Opportunities:**")
                    for faq in clusters.get('missing_faq_opportunities', [])[:5]:
                        st.write(f"• {faq}")
                
                if clusters.get('conversion_angles'):
                    st.write("**Conversion Angles:**")
                    for angle in clusters.get('conversion_angles', []):
                        st.write(f"• {angle}")
            
            st.session_state.conv_clusters = clusters
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
    
    generate_disabled = 'conv_clusters' not in st.session_state or not st.session_state.conv_clusters
    if generate_disabled and cluster_response:
        st.info("Click 'Parse & Preview' first")
    elif generate_disabled:
        st.info("Paste JSON response above")
    
    if st.button("Generate Output →", type="primary", disabled=generate_disabled, key="conv_step4_continue"):
        st.session_state.conv_step = 5
        st.rerun()

# Step 5: Generate Output
if st.session_state.conv_step >= 5:
    st.markdown("---")
    
    show_progress(st.session_state.conv_step, 5,
                 ["Product Context", "GKP Upload", "Deduplication", "Clustering", "Output"])
    
    st.header("Step 5: Generate Output")
    
    if st.session_state.conv_clusters:
        # Create CSV data
        layering_data = []
        for cluster in st.session_state.conv_clusters.get('clusters', []):
            # Add objection type to notes
            notes_parts = []
            if cluster.get('objection_type'):
                notes_parts.append(f"Objection: {cluster.get('objection_type')}")
            if cluster.get('coverage_notes'):
                notes_parts.append(cluster.get('coverage_notes'))
            
            notes = ' | '.join(notes_parts)
            
            layering_data.append({
                'Sub-Intent Layer': cluster.get('cluster_name'),
                'Role': cluster.get('role'),
                'Placement': cluster.get('placement'),
                'Keyword': '',
                'Priority': '',
                'Source': '',
                'Notes': notes
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
            st.download_button("↓ Download Layering CSV", csv, "conversion_layering.csv", "text/csv", key="conv_download_layering")
        with col2:
            unfiltered_csv = st.session_state.conv_keywords_df.to_csv(index=False)
            st.download_button("↓ Download Unfiltered CSV", unfiltered_csv, "conversion_unfiltered.csv", "text/csv", key="conv_download_unfiltered")
        
        # Conversion Angles Section
        if st.session_state.conv_clusters.get('conversion_angles'):
            st.markdown("---")
            st.subheader("Conversion Angles")
            st.caption("Use these as article titles or H2 headers to drive purchase decisions")
            
            for angle in st.session_state.conv_clusters.get('conversion_angles', []):
                st.write(f"• {angle}")
        
        # Google Sheets Sync
        if hasattr(st.session_state, 'conv_gsheet_creds') and hasattr(st.session_state, 'conv_sheet_url'):
            st.markdown("---")
            if st.button("Sync to Google Sheets", type="primary", key="conv_sync"):
                with st.spinner("Syncing to Google Sheets..."):
                    try:
                        sheet = connect_to_gsheet(st.session_state.conv_gsheet_creds, st.session_state.conv_sheet_url)
                        
                        with st.spinner("1/3: Updating UnfilteredKeywords tab..."):
                            update_unfiltered_tab(sheet, st.session_state.conv_keywords_df)
                            time.sleep(1)
                            st.success("✓ UnfilteredKeywords tab updated")
                        
                        with st.spinner("2/3: Creating Layers tab..."):
                            create_simplified_layering_tab(sheet, st.session_state.conv_clusters, st.session_state.conv_keywords_df)
                            time.sleep(1)
                            st.success("✓ Layers tab created")
                        
                        with st.spinner("3/3: Adding Match formulas..."):
                            add_match_formulas(sheet, st.session_state.conv_keywords_df)
                            st.success("✓ Match formulas added")
                        
                        st.balloons()
                        st.success("Sync complete!")
                        st.markdown(f"[Open Google Sheet]({st.session_state.conv_sheet_url})")
                        
                    except Exception as e:
                        st.error(f"Sync error: {e}")
        else:
            st.info("Configure Google Sheets in Step 2 to enable syncing")
    
    if st.button("Start Over", key="conv_restart"):
        for key in list(st.session_state.keys()):
            if key.startswith('conv_'):
                del st.session_state[key]
        st.session_state.conv_step = 1
        st.rerun()
