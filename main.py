import streamlit as st

st.set_page_config(
    page_title="SEO Keyword Clustering Tool",
    page_icon="🔍",
    layout="wide"
)

st.title("SEO Keyword Clustering Tool")
st.caption("QYUBIC - Discount Savings Startup UAE")

st.markdown("---")

st.header("Select Your Content Type")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Traffic Blog")
    st.write("**'Best X in UAE'** - Drive traffic through broad commercial searches")
    st.write("**Start with:** GKP Export")
    if st.button("Start Traffic Blog Workflow", type="primary", use_container_width=True):
        st.switch_page("pages/traffic_blog.py")
    
    st.markdown("---")
    
    st.subheader("Positioning Blog")
    st.write("**Brand + Problem** - Build trust and position brands as solutions")
    st.write("**Start with:** Brand Research")
    if st.button("Start Positioning Blog Workflow", type="primary", use_container_width=True):
        st.switch_page("pages/positioning_blog.py")

with col2:
    st.subheader("SERP Research")
    st.write("**Competitor Analysis** - Analyze top 10 competitors for any keyword")
    st.write("**Independent tool** - Use for any content type")
    if st.button("Start SERP Research", type="primary", use_container_width=True):
        st.switch_page("pages/serp_research.py")
    
    st.markdown("---")
    
    st.subheader("Conversion Blog")
    st.write("**Remove Objections** - Drive sales through product validation")
    st.write("**Start with:** Product Research")
    if st.button("Start Conversion Blog Workflow", type="primary", use_container_width=True):
        st.switch_page("pages/conversion_blog.py")

st.markdown("---")

st.info(
    "**Quick Guide:**\n\n"
    "1. **Traffic Blog:** Upload GKP CSV → Deduplicate → Cluster → Export\n\n"
    "2. **Positioning Blog:** Brand Context → Archetypes → Manual Research → "
    "Validation Keywords → GKP Upload → Deduplicate → Cluster → Export\n\n"
    "3. **SERP Research:** Enter keyword → Scrape top results → Extract headings → Export"
)