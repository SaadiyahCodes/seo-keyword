import pandas as pd

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
    
    df_clean = pd.DataFrame({
        'Keyword': keywords, 
        'Volume': volumes_clean,
        'Keyword Difficulty': [0] * len(keywords)  # Add placeholder KD column (GKP doesn't have it)
    })
    
    df_clean = df_clean[df_clean['Keyword'].notna()]
    df_clean = df_clean[df_clean['Keyword'] != 'nan']
    df_clean = df_clean[df_clean['Keyword'] != '']
    df_clean = df_clean.drop_duplicates(subset=['Keyword'], keep='first')
    df_clean = df_clean.reset_index(drop=True)
    
    df_clean['Keyword'] = df_clean['Keyword'].astype(str)
    df_clean['Volume'] = df_clean['Volume'].astype('int64')
    df_clean['Keyword Difficulty'] = df_clean['Keyword Difficulty'].astype('int64')
    
    return df_clean

def process_semrush_csv(csv_file):
    """Process Semrush CSV export"""
    df = pd.read_csv(csv_file, encoding="utf-8")
    
    # Column names in Semrush format
    keyword_col = 'Keyword'
    volume_col = 'Volume'
    kd_col = 'Keyword Difficulty'
    
    # Extract Keyword and Volume
    keywords = df[keyword_col].astype(str).str.strip().tolist()
    volumes = df[volume_col].astype(str).str.replace(',', '').str.replace(' ', '').str.strip().tolist()
    
    # Clean volumes
    volumes_clean = []
    for v in volumes:
        try:
            volumes_clean.append(int(float(v)))
        except:
            volumes_clean.append(0)
    
    # Clean KD (handle empty values)
    kd_clean = []
    for kd_val in df[kd_col]:
        try:
            kd_clean.append(int(float(str(kd_val).strip())))
        except:
            kd_clean.append(0)  # Default to 0 if empty/invalid
    
    # Create dataframe
    df_clean = pd.DataFrame({
        'Keyword': keywords, 
        'Volume': volumes_clean,
        'Keyword Difficulty': kd_clean
    })
    
    # Clean up
    df_clean = df_clean[df_clean['Keyword'].notna()]
    df_clean = df_clean[df_clean['Keyword'] != 'nan']
    df_clean = df_clean[df_clean['Keyword'] != '']
    df_clean = df_clean.drop_duplicates(subset=['Keyword'], keep='first')
    df_clean = df_clean.reset_index(drop=True)
    
    # Set types
    df_clean['Keyword'] = df_clean['Keyword'].astype(str)
    df_clean['Volume'] = df_clean['Volume'].astype('int64')
    df_clean['Keyword Difficulty'] = df_clean['Keyword Difficulty'].astype('int64')
    
    return df_clean