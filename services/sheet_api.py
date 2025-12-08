import gspread
import google.auth
import json
from datetime import datetime

# スプレッドシートID
SPREADSHEET_ID = '1emj5sW_saJpydDTva7mH5pi00YA2QIloCi_rKx_cbdU'

def get_client():
    """Google Sheets クライアントを取得"""
    credentials, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return gspread.authorize(credentials)

def get_spreadsheet():
    """スプレッドシートを開く"""
    gc = get_client()
    return gc.open_by_key(SPREADSHEET_ID)

# ============ Players (選手マスタ) ============

def get_all_players():
    """全選手を取得"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Players')
    except gspread.exceptions.WorksheetNotFound:
        return []

    records = worksheet.get_all_records()
    # activeがTRUEの選手のみフィルタ
    return [p for p in records if str(p.get('active', 'TRUE')).upper() == 'TRUE']

def get_player_by_id(player_id):
    """IDで選手を取得"""
    players = get_all_players()
    for player in players:
        if str(player.get('id')) == str(player_id):
            return player
    return None

def add_player(name, group, best_5000m='', target_time=''):
    """選手を追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Players')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Players', rows=100, cols=6)
        worksheet.append_row(['id', 'name', 'group', 'best_5000m', 'target_time', 'active'])

    # 新しいIDを生成
    all_values = worksheet.get_all_values()
    new_id = len(all_values)  # ヘッダーを含む行数 = 次のID

    worksheet.append_row([new_id, name, group, best_5000m, target_time, 'TRUE'])
    return new_id

# ============ Records (記録データ) ============

def get_all_records():
    """全記録を取得"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Records')
    except gspread.exceptions.WorksheetNotFound:
        return []

    return worksheet.get_all_records()

def get_records_by_player(player_id):
    """選手IDで記録を取得"""
    records = get_all_records()
    return [r for r in records if str(r.get('player_id')) == str(player_id)]

def add_record(player_id, event, time, memo=''):
    """記録を追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Records')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Records', rows=1000, cols=5)
        worksheet.append_row(['date', 'player_id', 'event', 'time', 'memo'])

    date = datetime.now().strftime('%Y/%m/%d')
    worksheet.append_row([date, player_id, event, time, memo])

# ============ Simulations (区間オーダー案) ============

def get_all_simulations():
    """全シミュレーションを取得"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Simulations')
    except gspread.exceptions.WorksheetNotFound:
        return []

    records = worksheet.get_all_records()
    for r in records:
        if r.get('order_data'):
            try:
                r['order_data'] = json.loads(r['order_data'])
            except json.JSONDecodeError:
                r['order_data'] = {}
    return records

def save_simulation(title, order_data):
    """シミュレーションを保存"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Simulations')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Simulations', rows=100, cols=3)
        worksheet.append_row(['created_at', 'title', 'order_data'])

    created_at = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    order_json = json.dumps(order_data, ensure_ascii=False)
    worksheet.append_row([created_at, title, order_json])
