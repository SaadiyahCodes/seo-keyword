import streamlit as st
import pandas as pd

def show_progress(current_step, total_steps, step_names):
    """Display clean progress indicator"""
    
    cols = st.columns(total_steps)
    for i, (col, name) in enumerate(zip(cols, step_names), 1):
        with col:
            if i < current_step:
                st.markdown(f"**:green[{i}. {name}]**")
            elif i == current_step:
                st.markdown(f"**{i}. {name}**")
            else:
                st.markdown(f":gray[{i}. {name}]")
    
    st.markdown("---")


def render_deduplication_step(keywords_df, brand_name=None, step_key="traffic"):
    """Reusable deduplication UI component"""
    from utils.prompts import generate_deduplication_prompt
    import json
    
    st.header("Deduplication")
    
    st.info(
        "Remove duplicates where only word order changed, and filter out brand names and low-value variations."
    )
    
    if st.button("Generate Deduplication Prompt", key=f"gen_dedup_{step_key}"):
        dedup_prompt = generate_deduplication_prompt(
            keywords_df['Keyword'].tolist(),
            brand_name=brand_name
        )
        
        st.subheader("Copy to ChatGPT:")
        st.code(dedup_prompt, language=None)
        st.text_area("Click to copy:", dedup_prompt, height=100, key=f"dedup_prompt_copy_{step_key}")
    
    st.markdown("---")
    st.subheader("Paste Response:")
    
    dedup_response = st.text_area(
        "JSON from ChatGPT", 
        height=300, 
        key=f"dedup_json_{step_key}",
        placeholder='{\n  "kept_keywords": [...],\n  "removed": {...},\n  "dedup_summary": "..."\n}'
    )
    
    if st.button("Apply Deduplication", type="secondary", key=f"apply_dedup_{step_key}"):
        try:
            dedup_data = json.loads(dedup_response)
            
            # Filter dataframe to only kept keywords
            cleaned_df = keywords_df[
                keywords_df['Keyword'].isin(dedup_data['kept_keywords'])
            ].copy()
            
            # Show summary
            with st.expander("Deduplication Summary", expanded=True):
                st.success(dedup_data['dedup_summary'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Kept", len(dedup_data['kept_keywords']))
                with col2:
                    st.metric("Duplicates Removed", len(dedup_data['removed'].get('duplicates', [])))
                with col3:
                    st.metric("Brands Removed", len(dedup_data['removed'].get('brands', [])))
                
                if dedup_data['removed'].get('duplicates'):
                    st.markdown("**Removed Duplicates:**")
                    st.caption(', '.join(dedup_data['removed']['duplicates'][:10]))
                
                if dedup_data['removed'].get('brands'):
                    st.markdown("**Removed Brands:**")
                    st.caption(', '.join(dedup_data['removed']['brands']))
            
            return cleaned_df, dedup_data
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            return None, None
    
    return None, None

def render_dual_csv_upload(step_key="traffic"):
    """Reusable component for uploading GKP + Semrush CSVs"""
    from utils.gkp_processing import process_gkp_csv, process_semrush_csv
    
    st.subheader("Upload Keyword Data")
    
    col1, col2 = st.columns(2)
    
    gkp_file = None
    semrush_file = None
    combined_df = None
    
    with col1:
        st.markdown("#### Google Keyword Planner")
        gkp_file = st.file_uploader(
            "Upload GKP CSV",
            type=['csv'],
            key=f"{step_key}_gkp_csv",
            help="Export from Google Keyword Planner (UTF-16 format)"
        )
    
    with col2:
        st.markdown("#### Semrush")
        semrush_file = st.file_uploader(
            "Upload Semrush CSV",
            type=['csv'],
            key=f"{step_key}_semrush_csv",
            help="Export from Semrush Keyword Research (Tab-separated)"
        )
    
    st.caption("Upload at least ONE CSV. If both are uploaded, they will be combined.")
    
    # Process files
    gkp_df = None
    semrush_df = None
    
    if gkp_file:
        try:
            gkp_df = process_gkp_csv(gkp_file)
            st.success(f"✓ GKP: {len(gkp_df)} keywords")
        except Exception as e:
            st.error(f"GKP Error: {e}")
    
    if semrush_file:
        try:
            semrush_df = process_semrush_csv(semrush_file)
            st.success(f"✓ Semrush: {len(semrush_df)} keywords")
        except Exception as e:
            st.error(f"Semrush Error: {e}")
    
    # Combine if both exist
    if gkp_df is not None and semrush_df is not None:
        combined_df = pd.concat([gkp_df, semrush_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['Keyword'], keep='first')
        combined_df = combined_df.reset_index(drop=True)
        st.success(f"Combined: {len(combined_df)} unique keywords")
        
        with st.expander("Preview Combined Data"):
            st.dataframe(combined_df.head(10), use_container_width=True)
        
        return combined_df
    
    elif gkp_df is not None:
        st.success(f"Using GKP data: {len(gkp_df)} keywords")
        
        with st.expander("Preview Keywords"):
            st.dataframe(gkp_df.head(10), use_container_width=True)
        
        return gkp_df
    
    elif semrush_df is not None:
        st.success(f"Using Semrush data: {len(semrush_df)} keywords")
        
        with st.expander("Preview Keywords"):
            st.dataframe(semrush_df.head(10), use_container_width=True)
        
        return semrush_df
    
    else:
        return None