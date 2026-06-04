import streamlit as st
import pandas as pd
import json
import time
from utils.gkp_processing import process_gkp_csv
from utils.gsheet_sync import connect_to_gsheet, update_unfiltered_tab, create_simplified_layering_tab, add_match_formulas
from utils.prompts import (
    generate_archetype_prompt, 
    generate_validation_keywords_prompt,
    generate_positioning_clustering_prompt
)
from utils.ui_components import show_progress, render_deduplication_step, render_dual_csv_upload

st.set_page_config(page_title="Positioning Blog", page_icon="🎯", layout="wide")

# Initialize session state
if 'pos_step' not in st.session_state:
    st.session_state.pos_step = 1
if 'pos_brand_context' not in st.session_state:
    st.session_state.pos_brand_context = {}
if 'pos_archetypes' not in st.session_state:
    st.session_state.pos_archetypes = {}
if 'pos_manual_research' not in st.session_state:
    st.session_state.pos_manual_research = {}
if 'pos_validation_keywords' not in st.session_state:
    st.session_state.pos_validation_keywords = []
if 'pos_keywords_df' not in st.session_state:
    st.session_state.pos_keywords_df = None
if 'pos_clusters' not in st.session_state:
    st.session_state.pos_clusters = {}

st.title("Positioning Blog Workflow")
st.caption("Brand + Problem - Build trust and position brands as solutions")

if st.button("← Back to Home"):
    st.switch_page("main.py")

st.markdown("---")

# Progress indicator
show_progress(
    st.session_state.pos_step,
    9,
    ["Brand Context", "Archetypes", "Manual Research", "Validation Keywords", 
     "GKP Upload", "Deduplication", "Clustering", "Angles", "Output"]
)

# Step 1: Brand Context Input
if st.session_state.pos_step >= 1:
    st.header("Step 1: Brand Context")
    
    col1, col2 = st.columns(2)
    
    with col1:
        brand_name = st.text_input(
            "Brand Name*", 
            value=st.session_state.pos_brand_context.get('brand_name', ''),
            placeholder="e.g., Marhaba"
        )
        
        industry = st.text_input(
            "Industry*",
            value=st.session_state.pos_brand_context.get('industry', ''),
            placeholder="e.g., Airport Services"
        )
        
        target_market = st.text_input(
            "Target Market",
            value=st.session_state.pos_brand_context.get('target_market', ''),
            placeholder="e.g., UAE travelers, families, business travelers"
        )
    
    with col2:
        services = st.text_area(
            "Core Services (one per line)",
            value=st.session_state.pos_brand_context.get('services_text', ''),
            placeholder="Meet & greet\nLounge access\nFast track immigration\nWheelchair assistance",
            height=120
        )
        
        content_goal = st.text_input(
            "Content Topic/Goal*",
            value=st.session_state.pos_brand_context.get('content_goal', ''),
            placeholder="e.g., Airport stress for elderly travelers"
        )
    
    with st.expander("Brand Research Notes (Optional)"):
        brand_notes = st.text_area(
            "Paste any brand research, USPs, FAQs, or reviews here",
            value=st.session_state.pos_brand_context.get('brand_notes', ''),
            height=150,
            placeholder="Any additional context about the brand, unique selling points, customer testimonials, etc."
        )
    
    # Save brand context
    if st.button("Save Brand Context", type="secondary", key="save_brand_context"):
        st.session_state.pos_brand_context = {
            'brand_name': brand_name,
            'industry': industry,
            'services': [s.strip() for s in services.split('\n') if s.strip()],
            'services_text': services,
            'target_market': target_market,
            'content_goal': content_goal,
            'brand_notes': brand_notes
        }
        st.success("✓ Brand context saved")
    
    button_disabled = not brand_name or not industry or not content_goal
    if button_disabled:
        st.warning("Fill in required fields (marked with *) to continue")
    
    if st.button("Continue →", type="primary", disabled=button_disabled, key="pos_step1_continue"):
        if not st.session_state.pos_brand_context:
            st.session_state.pos_brand_context = {
                'brand_name': brand_name,
                'industry': industry,
                'services': [s.strip() for s in services.split('\n') if s.strip()],
                'services_text': services,
                'target_market': target_market,
                'content_goal': content_goal,
                'brand_notes': brand_notes
            }
        st.session_state.pos_step = 2
        st.rerun()

# Step 2: User Archetype Research
if st.session_state.pos_step >= 2:
    st.markdown("---")
    
    show_progress(st.session_state.pos_step, 9, 
                 ["Brand Context", "Archetypes", "Manual Research", "Validation Keywords", 
                  "GKP Upload", "Deduplication", "Clustering", "Angles", "Output"])
    
    st.header("Step 2: User Archetype Research")
    
    st.info(
        "Identify 3-5 user archetypes who would benefit from these services. "
        "For each archetype, define their pain points, emotional needs, and stressful scenarios."
    )
    
    archetype_prompt = generate_archetype_prompt(st.session_state.pos_brand_context)
    
    st.subheader("Copy to ChatGPT:")
    st.code(archetype_prompt, language=None)
    st.text_area("Click to copy:", archetype_prompt, height=100, key="archetype_prompt_copy")
    
    st.markdown("---")
    st.subheader("Paste Response:")
    
    archetype_response = st.text_area(
        "JSON from ChatGPT", 
        height=300, 
        key="archetype_json",
        placeholder='{\n  "Families with Young Children": {\n    "who": "...",\n    "pain_points": [...],\n    ...\n  }\n}'
    )
    
    if st.button("Parse Archetypes", type="secondary", key="parse_archetypes"):
        try:
            archetypes = json.loads(archetype_response)
            st.session_state.pos_archetypes = archetypes
            
            st.success(f"✓ Parsed {len(archetypes)} archetypes")
            
            with st.expander("Preview Archetypes", expanded=True):
                for archetype_name, data in archetypes.items():
                    st.write(f"**{archetype_name}**")
                    st.caption(f"Who: {data.get('who', 'N/A')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Pain Points:**")
                        for pp in data.get('pain_points', [])[:3]:
                            st.write(f"• {pp}")
                    with col2:
                        st.markdown("**Emotional Needs:**")
                        for en in data.get('emotional_needs', [])[:3]:
                            st.write(f"• {en}")
                    
                    st.markdown("---")
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
    
    continue_disabled = 'pos_archetypes' not in st.session_state or not st.session_state.pos_archetypes
    if continue_disabled and archetype_response:
        st.info("Click 'Parse Archetypes' first")
    elif continue_disabled:
        st.info("Paste JSON response above")
    
    if st.button("Continue →", type="primary", disabled=continue_disabled, key="pos_step2_continue"):
        st.session_state.pos_step = 3
        st.rerun()

# Step 3: Manual Research Checklist
if st.session_state.pos_step >= 3:
    st.markdown("---")
    
    show_progress(st.session_state.pos_step, 9,
                 ["Brand Context", "Archetypes", "Manual Research", "Validation Keywords", 
                  "GKP Upload", "Deduplication", "Clustering", "Angles", "Output"])
    
    st.header("Step 3: Manual Research (Human Intelligence)")
    
    st.info(
        "Goal: Find recurring emotional friction, logistical stress, and natural user language. "
        "This step requires human judgment to identify real emotional wording and hidden frustrations."
    )
    
    # Generate checklist for EACH archetype
    for archetype_name in st.session_state.pos_archetypes.keys():
        with st.expander(f"Research Checklist: {archetype_name}", expanded=False):
            
            # 1. Google Autosuggest
            st.markdown("#### 1. Google Autosuggest")
            st.caption("Type these queries and record what Google suggests")
            
            base_query = f"{st.session_state.pos_brand_context['content_goal']} {archetype_name.lower()}"
            st.code(f"{base_query}\n{base_query} tips\n{base_query} how to")
            
            findings_auto = st.text_area(
                "Autosuggest findings",
                key=f"auto_{archetype_name}",
                placeholder="Example: 'airport with toddlers tips', 'dubai airport family lounge', 'traveling with infants checklist'",
                height=100
            )
            
            # 2. People Also Ask
            st.markdown("#### 2. People Also Ask (PAA)")
            st.caption("Extract: fears, concerns, confusion, comparison questions")
            
            findings_paa = st.text_area(
                "PAA findings",
                key=f"paa_{archetype_name}",
                placeholder="Example: 'How to get through airport security with baby?', 'Is Dubai airport child-friendly?'",
                height=100
            )
            
            # 3. AnswerThePublic
            st.markdown("#### 3. AnswerThePublic")
            st.caption("Search your main keywords and extract question modifiers, emotional modifiers, concern phrasing")
            
            atp_query = f"{st.session_state.pos_brand_context['content_goal'].split()[0]} airport"
            if len(archetype_name.split()) > 0:
                atp_query += f" {archetype_name.split()[0].lower()}"
            
            st.code(f"answerthepublic.com → Search: {atp_query}")
            
            st.markdown(
                "**Look for:**\n"
                "- Questions: 'how to', 'can I', 'what if', 'is it safe'\n"
                "- Comparisons: 'vs', 'or', 'better than'\n"
                "- Prepositions: 'with', 'without', 'for', 'near'"
            )
            
            findings_atp = st.text_area(
                "AnswerThePublic findings",
                key=f"atp_{archetype_name}",
                placeholder="Example: 'airport assistance with wheelchair', 'fast track vs lounge', 'meet and greet for elderly'",
                height=100
            )
            
            # 4. Reddit/Forums
            st.markdown("#### 4. Reddit/Forums")
            st.caption("Extract: emotional wording, real frustrations, hidden pain points")
            
            reddit_queries = [
                f"{st.session_state.pos_brand_context['content_goal']} reddit",
                f"dubai airport {archetype_name.lower()} reddit"
            ]
            st.code('\n'.join(reddit_queries))
            
            findings_reddit = st.text_area(
                "Reddit/Forum findings",
                key=f"reddit_{archetype_name}",
                placeholder="Example: 'nightmare navigating with stroller', 'security lines are exhausting with kids', 'wish we had help'",
                height=100
            )
            
            # 5. YouTube/TikTok
            st.markdown("#### 5. YouTube/TikTok")
            st.caption("Search: airport hacks, travel tips. Extract: repeated frustrations, practical solutions")
            
            video_queries = [
                f"airport hacks {archetype_name.lower()}",
                f"dubai airport tips"
            ]
            st.code('\n'.join(video_queries))
            
            findings_video = st.text_area(
                "Video findings",
                key=f"video_{archetype_name}",
                placeholder="Example: 'everyone mentions long walks', 'common complaint: confusing signage', 'tip: book assistance in advance'",
                height=100
            )
    
    st.markdown("---")
    
    # Save button at bottom
    if st.button("Save Research Findings", type="primary", key="save_research"):
        st.session_state.pos_manual_research = {
            archetype: {
                'autosuggest': st.session_state.get(f"auto_{archetype}", ""),
                'paa': st.session_state.get(f"paa_{archetype}", ""),
                'answerthepublic': st.session_state.get(f"atp_{archetype}", ""),
                'reddit': st.session_state.get(f"reddit_{archetype}", ""),
                'video': st.session_state.get(f"video_{archetype}", "")
            }
            for archetype in st.session_state.pos_archetypes.keys()
        }
        st.success("✓ Research findings saved")
    
    continue_disabled = 'pos_manual_research' not in st.session_state or not st.session_state.pos_manual_research
    if continue_disabled:
        st.info("Click 'Save Research Findings' to continue")
    
    if st.button("Continue →", type="primary", disabled=continue_disabled, key="pos_step3_continue"):
        st.session_state.pos_step = 4
        st.rerun()

# Step 4: Generate SEO Validation Keywords
if st.session_state.pos_step >= 4:
    st.markdown("---")
    
    show_progress(st.session_state.pos_step, 9,
                 ["Brand Context", "Archetypes", "Manual Research", "Validation Keywords", 
                  "GKP Upload", "Deduplication", "Clustering", "Angles", "Output"])
    
    st.header("Step 4: SEO Validation Keywords")
    
    st.info(
        "Generate keyword seeds to search in Google Keyword Planner. "
        "These bridge psychology (from archetypes) to SEO language (for GKP)."
    )
    
    validation_prompt = generate_validation_keywords_prompt(
        st.session_state.pos_brand_context,
        st.session_state.pos_archetypes,
        st.session_state.pos_manual_research
    )
    
    st.subheader("Copy to ChatGPT:")
    st.code(validation_prompt, language=None)
    st.text_area("Click to copy:", validation_prompt, height=100, key="validation_prompt_copy")
    
    st.markdown("---")
    st.subheader("Paste Response:")
    
    validation_response = st.text_area(
        "JSON from ChatGPT",
        height=300,
        key="validation_json",
        placeholder='{\n  "keyword_seeds": [...],\n  "rationale": "..."\n}'
    )
    
    if st.button("Parse Keywords", type="secondary", key="parse_validation"):
        try:
            validation_data = json.loads(validation_response)
            st.session_state.pos_validation_keywords = validation_data.get('keyword_seeds', [])
            
            st.success(f"✓ {len(st.session_state.pos_validation_keywords)} seed keywords generated")
            
            if validation_data.get('rationale'):
                st.info(f"Strategy: {validation_data['rationale']}")
            
            with st.expander("Preview Keywords", expanded=True):
                for i, kw in enumerate(st.session_state.pos_validation_keywords, 1):
                    st.write(f"{i}. {kw}")
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
    
    # Export for GKP
    if st.session_state.pos_validation_keywords:
        seeds_text = '\n'.join(st.session_state.pos_validation_keywords)
        st.download_button(
            "↓ Download Seeds for GKP",
            seeds_text,
            "gkp_seeds.txt",
            "text/plain",
            key="download_seeds"
        )
        
        st.markdown("---")
        st.info(
            "**Next Steps:**\n\n"
            "1. Download the seed keywords above\n"
            "2. Go to Google Keyword Planner\n"
            "3. Search these seeds and export the CSV\n"
            "4. Upload the GKP CSV in the next step"
        )
    
    continue_disabled = not st.session_state.pos_validation_keywords
    if continue_disabled and validation_response:
        st.info("Click 'Parse Keywords' first")
    elif continue_disabled:
        st.info("Paste JSON response above")
    
    if st.button("Continue →", type="primary", disabled=continue_disabled, key="pos_step4_continue"):
        st.session_state.pos_step = 5
        st.rerun()

# Step 5: GKP Upload
if st.session_state.pos_step >= 5:
    st.markdown("---")
    
    show_progress(st.session_state.pos_step, 9,
                 ["Brand Context", "Archetypes", "Manual Research", "Validation Keywords", 
                  "GKP Upload", "Deduplication", "Clustering", "Angles", "Output"])
    
    st.header("Step 5: Upload Keyword Data")
    
    st.info("Search the seed keywords in Google Keyword Planner or Semrush, export the CSV, and upload it here")
    
    uploaded_df = render_dual_csv_upload(step_key="pos")
    if uploaded_df is not None:
        st.session_state.pos_keywords_df = uploaded_df
    
    with st.expander("Google Sheets Setup (Optional)"):
        creds_file = st.file_uploader("Service Account JSON", type=['json'], key='pos_creds_upload')
        sheet_url = st.text_input(
            "Google Sheet URL", 
            key="pos_sheet_url_input",
            value=st.session_state.get('pos_sheet_url', '')
        )
        if creds_file and sheet_url:
            try:
                creds_data = json.load(creds_file)
                st.session_state.pos_gsheet_creds = creds_data
                st.session_state.pos_sheet_url = sheet_url
                st.success("✓ Google Sheets configured")
            except Exception as e:
                st.error(f"Error: {e}")
    
    button_disabled = st.session_state.pos_keywords_df is None
    if button_disabled:
        st.warning("Upload at least one CSV to continue")
    
    if st.button("Continue →", type="primary", disabled=button_disabled, key="pos_step5_continue"):
        st.session_state.pos_step = 6
        st.rerun()

# Step 6: Deduplication
if st.session_state.pos_step >= 6:
    st.markdown("---")
    
    show_progress(st.session_state.pos_step, 9,
                 ["Brand Context", "Archetypes", "Manual Research", "Validation Keywords", 
                  "GKP Upload", "Deduplication", "Clustering", "Angles", "Output"])
    
    cleaned_df, dedup_data = render_deduplication_step(
        st.session_state.pos_keywords_df,
        brand_name=st.session_state.pos_brand_context.get('brand_name'),
        step_key="pos"
    )
    
    if cleaned_df is not None:
        st.session_state.pos_keywords_df = cleaned_df
        st.session_state.pos_dedup_data = dedup_data
    
    if st.button("Continue to Clustering →", type="primary", key="pos_step6_continue"):
        if 'pos_dedup_data' not in st.session_state:
            st.warning("Please apply deduplication first")
        else:
            st.session_state.pos_step = 7
            st.rerun()

# Step 7: Positioning-Aware Clustering
if st.session_state.pos_step >= 7:
    st.markdown("---")
    
    show_progress(st.session_state.pos_step, 9,
                 ["Brand Context", "Archetypes", "Manual Research", "Validation Keywords", 
                  "GKP Upload", "Deduplication", "Clustering", "Angles", "Output"])
    
    st.header("Step 7: Positioning-Aware Clustering")
    
    clustering_prompt = generate_positioning_clustering_prompt(
        st.session_state.pos_brand_context,
        st.session_state.pos_keywords_df['Keyword'].tolist(),
        st.session_state.pos_archetypes
    )
    
    st.subheader("Copy to ChatGPT:")
    st.code(clustering_prompt, language=None)
    st.text_area("Click to copy:", clustering_prompt, height=100, key="pos_cluster_prompt_copy")
    
    st.markdown("---")
    st.subheader("Paste Response:")
    
    cluster_response = st.text_area("JSON from ChatGPT", height=300, key="pos_cluster_json")
    
    parse_button = st.button("Parse & Preview", type="secondary", key="pos_parse_clusters")
    
    if parse_button and cluster_response:
        try:
            clusters = json.loads(cluster_response)
            st.success(f"✓ Parsed {len(clusters.get('clusters', []))} clusters")
            
            with st.expander("Preview Clusters", expanded=True):
                for cluster in clusters.get('clusters', []):
                    st.write(f"**{cluster.get('cluster_name')}**")
                    
                    if cluster.get('linked_archetype'):
                        st.caption(f"Archetype: {cluster.get('linked_archetype')}")
                    
                    st.caption(f"Role: {cluster.get('role')} | Placement: {cluster.get('placement')}")
                    
                    if cluster.get('positioning_angle'):
                        st.write(f"*Angle: {cluster.get('positioning_angle')}*")
                    
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
                
                if clusters.get('positioning_hooks'):
                    st.write("**Positioning Hooks:**")
                    for hook in clusters.get('positioning_hooks', []):
                        st.write(f"• {hook}")
            
            st.session_state.pos_clusters = clusters
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
    
    continue_disabled = 'pos_clusters' not in st.session_state or not st.session_state.pos_clusters
    if continue_disabled and cluster_response:
        st.info("Click 'Parse & Preview' first")
    elif continue_disabled:
        st.info("Paste JSON response above")
    
    if st.button("Continue →", type="primary", disabled=continue_disabled, key="pos_step7_continue"):
        st.session_state.pos_step = 8
        st.rerun()

# Step 8: Positioning Angles
if st.session_state.pos_step >= 8:
    st.markdown("---")
    
    show_progress(st.session_state.pos_step, 9,
                 ["Brand Context", "Archetypes", "Manual Research", "Validation Keywords", 
                  "GKP Upload", "Deduplication", "Clustering", "Angles", "Output"])
    
    st.header("Step 8: Content Angles & Positioning Hooks")
    
    if st.session_state.pos_clusters:
        
        # Show positioning hooks
        if st.session_state.pos_clusters.get('positioning_hooks'):
            st.subheader("Positioning Hooks")
            st.caption("Use these angles to position the brand as the solution")
            
            for hook in st.session_state.pos_clusters.get('positioning_hooks', []):
                st.write(f"• {hook}")
            
            st.markdown("---")
        
        # Show cluster-specific angles
        st.subheader("Cluster-Specific Angles")
        st.caption("Each cluster has a positioning angle that connects the pain point to the brand")
        
        for cluster in st.session_state.pos_clusters.get('clusters', []):
            if cluster.get('positioning_angle'):
                archetype = cluster.get('linked_archetype', 'General')
                angle = cluster.get('positioning_angle')
                cluster_name = cluster.get('cluster_name')
                
                st.write(f"**{cluster_name}** ({archetype})")
                st.write(f"→ {angle}")
                st.markdown("---")
        
        # Suggested titles
        st.subheader("Suggested Article Titles")
        st.caption("Based on archetypes and pain points")
        
        for archetype_name, archetype_data in st.session_state.pos_archetypes.items():
            pain_point = archetype_data.get('pain_points', [''])[0]
            brand_name = st.session_state.pos_brand_context.get('brand_name')
            
            title_suggestion = f"{pain_point}? How {brand_name} Can Help"
            st.write(f"• {title_suggestion}")
    
    if st.button("Generate Output →", type="primary", key="pos_step8_continue"):
        st.session_state.pos_step = 9
        st.rerun()

# Step 9: Generate Output
if st.session_state.pos_step >= 9:
    st.markdown("---")
    
    show_progress(st.session_state.pos_step, 9,
                 ["Brand Context", "Archetypes", "Manual Research", "Validation Keywords", 
                  "GKP Upload", "Deduplication", "Clustering", "Angles", "Output"])
    
    st.header("Step 9: Generate Output")
    
    if st.session_state.pos_clusters:
        # Create CSV data (same format as traffic blog)
        layering_data = []
        for cluster in st.session_state.pos_clusters.get('clusters', []):
            # Add archetype and positioning angle to notes
            notes_parts = []
            if cluster.get('linked_archetype'):
                notes_parts.append(f"Archetype: {cluster.get('linked_archetype')}")
            if cluster.get('positioning_angle'):
                notes_parts.append(f"Angle: {cluster.get('positioning_angle')}")
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
            st.download_button("↓ Download Layering CSV", csv, "positioning_layering.csv", "text/csv", key="pos_download_layering")
        with col2:
            unfiltered_csv = st.session_state.pos_keywords_df.to_csv(index=False)
            st.download_button("↓ Download Unfiltered CSV", unfiltered_csv, "positioning_unfiltered.csv", "text/csv", key="pos_download_unfiltered")
        
        # Google Sheets Sync (identical to traffic blog - COPY/PASTE from Traffic Blog Step 4)
        if hasattr(st.session_state, 'pos_gsheet_creds') and hasattr(st.session_state, 'pos_sheet_url'):
            st.markdown("---")
            if st.button("Sync to Google Sheets", type="primary", key="pos_sync"):
                with st.spinner("Syncing to Google Sheets..."):
                    try:
                        sheet = connect_to_gsheet(st.session_state.pos_gsheet_creds, st.session_state.pos_sheet_url)
                        
                        with st.spinner("1/3: Updating UnfilteredKeywords tab..."):
                            update_unfiltered_tab(sheet, st.session_state.pos_keywords_df)
                            time.sleep(1)
                            st.success("✓ UnfilteredKeywords tab updated")
                        
                        with st.spinner("2/3: Creating Layers tab..."):
                            create_simplified_layering_tab(sheet, st.session_state.pos_clusters, st.session_state.pos_keywords_df)
                            time.sleep(1)
                            st.success("✓ Layers tab created")
                        
                        with st.spinner("3/3: Adding Match formulas..."):
                            add_match_formulas(sheet, st.session_state.pos_keywords_df)
                            st.success("✓ Match formulas added")
                        
                        st.balloons()
                        st.success("Sync complete!")
                        st.markdown(f"[Open Google Sheet]({st.session_state.pos_sheet_url})")
                        
                    except Exception as e:
                        st.error(f"Sync error: {e}")
        else:
            st.info("Configure Google Sheets in Step 5 to enable syncing")
    
    if st.button("Start Over", key="pos_restart"):
        for key in list(st.session_state.keys()):
            if key.startswith('pos_'):
                del st.session_state[key]
        st.session_state.pos_step = 1
        st.rerun()