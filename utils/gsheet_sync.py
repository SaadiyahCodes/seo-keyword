import gspread
from google.oauth2.service_account import Credentials
import time

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
    """Create simplified Layering tab - cluster headers + borders only"""
    try:
        worksheet = sheet.worksheet("Layers")
        worksheet.clear()
    except:
        worksheet = sheet.add_worksheet(title="Layers", rows=2000, cols=7)
    
    headers = ['Sub-Intent Layer', 'Keyword', 'Volume', 'K.D', 'Priority', 'Source', 'Notes']
    worksheet.update('A1:G1', [headers])
    
    # Format header
    worksheet.format('A1:G1', {
        'textFormat': {'bold': True, 'fontSize': 11},
        'backgroundColor': {'red': 0.2, 'green': 0.3, 'blue': 0.5},
        'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
    })
    
    current_row = 2
    all_cluster_data = []
    cluster_header_rows = []  # Track which rows are cluster headers
    cluster_end_rows = []     # Track which rows need bottom borders
    
    # Collect ALL data first
    for cluster in clusters_data.get('clusters', []):
        cluster_name = cluster.get('cluster_name', 'Unnamed Cluster')
        role = cluster.get('role', '')
        placement = cluster.get('placement', '')
        coverage_notes = cluster.get('coverage_notes', '')
        keywords = cluster.get('keywords', [])
        
        # Mark this row as a cluster header
        cluster_header_rows.append(current_row)
        
        # Cluster header row
        all_cluster_data.append([
            cluster_name, '', '', '', '', '',
            f"{role} | {placement} | {coverage_notes}"
        ])
        current_row += 1
        
        # Keyword rows
        for kw_obj in keywords:
            keyword = kw_obj.get('keyword', '')
            source = kw_obj.get('source', 'GKP')
            priority = kw_obj.get('priority', 'MEDIUM')
            
            all_cluster_data.append([
                '', keyword,
                f'=IFERROR(VLOOKUP(B{current_row},UnfilteredKeywords!A:B,2,FALSE),"-")',
                '', priority, source, ''
            ])
            current_row += 1
        
        # Mark the last keyword row for bottom border
        cluster_end_rows.append(current_row - 1)
        
        # Empty row separator
        all_cluster_data.append(['', '', '', '', '', '', ''])
        current_row += 1
    
    # FAQ section
    faq_opportunities = clusters_data.get('missing_faq_opportunities', [])
    faq_header_row = None
    if faq_opportunities:
        faq_header_row = current_row
        
        all_cluster_data.append([
            'MISSING FAQ OPPORTUNITIES', '', '', '', 'MEDIUM', 'AI Suggested',
            'Consider adding to FAQ section'
        ])
        current_row += 1
        
        for faq in faq_opportunities:
            all_cluster_data.append(['', faq, '-', '', 'MEDIUM', 'AI Suggested', ''])
            current_row += 1
    
    # SINGLE WRITE for ALL data (1 API call)
    if all_cluster_data:
        worksheet.update(
            range_name=f'A2:G{len(all_cluster_data) + 1}',
            values=all_cluster_data,
            value_input_option='USER_ENTERED'
        )
    
    # Format cluster headers (1 API call per cluster header)
    for row_num in cluster_header_rows:
        worksheet.format(f'A{row_num}:G{row_num}', {
            'textFormat': {'bold': True, 'fontSize': 11},
            'backgroundColor': {'red': 0.85, 'green': 0.92, 'blue': 0.95}
        })
        time.sleep(0.3)  # Small delay between format calls
    
    # Add bottom borders (1 API call per cluster)
    for row_num in cluster_end_rows:
        worksheet.format(f'A{row_num}:G{row_num}', {
            'borders': {
                'bottom': {'style': 'SOLID_MEDIUM', 'color': {'red': 0, 'green': 0, 'blue': 0}}
            }
        })
        time.sleep(0.3)  # Small delay between format calls
    
    # Format FAQ header if exists (1 API call)
    if faq_header_row:
        worksheet.format(f'A{faq_header_row}:G{faq_header_row}', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.85, 'green': 0.95, 'blue': 0.85}
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
        return False