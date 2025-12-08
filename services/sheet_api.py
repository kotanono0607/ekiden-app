import gspread
import google.auth
import json
from datetime import datetime
import time

# スプレッドシートID
SPREADSHEET_ID = '1emj5sW_saJpydDTva7mH5pi00YA2QIloCi_rKx_cbdU'

# ============ キャッシュ機能 ============
# APIレート制限対策（60リクエスト/分）

_cache = {}
CACHE_TTL = 30  # キャッシュ有効期間（秒）

def _get_cache(key):
    """キャッシュからデータを取得"""
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
    return None

def _set_cache(key, data):
    """キャッシュにデータを保存"""
    _cache[key] = (data, time.time())

def clear_cache():
    """キャッシュをクリア"""
    global _cache
    _cache = {}

# ============ カラム名の正規化 ============
# スプレッドシートの実際のカラム名をアプリの内部名にマッピング

COLUMN_MAPPING = {
    'registration_number': 'id',
    'affiliation': 'group',
}

def normalize_player(player):
    """スプレッドシートのカラム名をアプリ内部の名前に変換"""
    normalized = {}
    for key, value in player.items():
        # マッピングがあれば変換、なければそのまま
        new_key = COLUMN_MAPPING.get(key, key)
        normalized[new_key] = value
    return normalized

def normalize_players(players):
    """選手リストを正規化"""
    return [normalize_player(p) for p in players]

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
# 拡張カラム: id, name, group, best_5000m, target_time, active, grade, school, height, weight, message, photo_url

def get_all_players():
    """全選手を取得（キャッシュ付き）"""
    cached = _get_cache('all_players')
    if cached is not None:
        return cached

    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Players')
    except gspread.exceptions.WorksheetNotFound:
        return []

    records = worksheet.get_all_records()
    # カラム名を正規化
    records = normalize_players(records)
    # activeがTRUEの選手のみフィルタ
    result = [p for p in records if str(p.get('active', 'TRUE')).upper() == 'TRUE']
    _set_cache('all_players', result)
    return result

def get_all_players_including_inactive():
    """引退選手も含む全選手を取得（キャッシュ付き）"""
    cached = _get_cache('all_players_inactive')
    if cached is not None:
        return cached

    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Players')
    except gspread.exceptions.WorksheetNotFound:
        return []
    records = worksheet.get_all_records()
    # カラム名を正規化
    result = normalize_players(records)
    _set_cache('all_players_inactive', result)
    return result

def get_player_by_id(player_id):
    """IDで選手を取得"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Players')
    except gspread.exceptions.WorksheetNotFound:
        return None

    records = worksheet.get_all_records()
    # カラム名を正規化
    records = normalize_players(records)
    for player in records:
        if str(player.get('id')) == str(player_id):
            return player
    return None

def add_player(name, group, best_5000m='', target_time='', grade='', school='', height='', weight='', message='', photo_url=''):
    """選手を追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Players')
        headers = worksheet.row_values(1)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Players', rows=100, cols=12)
        headers = ['id', 'name', 'group', 'best_5000m', 'target_time', 'active', 'grade', 'school', 'height', 'weight', 'message', 'photo_url']
        worksheet.append_row(headers)

    # ヘッダーに新しいカラムがなければ追加
    required_headers = ['id', 'name', 'group', 'best_5000m', 'target_time', 'active', 'grade', 'school', 'height', 'weight', 'message', 'photo_url']
    if len(headers) < len(required_headers):
        worksheet.update('A1:L1', [required_headers])

    # 新しいIDを生成
    all_values = worksheet.get_all_values()
    new_id = len(all_values)

    worksheet.append_row([new_id, name, group, best_5000m, target_time, 'TRUE', grade, school, height, weight, message, photo_url])
    clear_cache()  # キャッシュクリア
    return new_id

def update_player(player_id, name, group, best_5000m='', target_time='', active='TRUE', grade='', school='', height='', weight='', message='', photo_url=''):
    """選手を更新"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Players')
    except gspread.exceptions.WorksheetNotFound:
        return False

    # IDで行を検索
    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i == 0:  # ヘッダーをスキップ
            continue
        if str(row[0]) == str(player_id):
            # 行を更新
            row_num = i + 1
            worksheet.update(f'A{row_num}:L{row_num}', [[player_id, name, group, best_5000m, target_time, active, grade, school, height, weight, message, photo_url]])
            clear_cache()  # キャッシュクリア
            return True
    return False

def delete_player(player_id):
    """選手を削除（実際には非アクティブに）"""
    player = get_player_by_id(player_id)
    if player:
        return update_player(
            player_id,
            player.get('name', ''),
            player.get('group', ''),
            player.get('best_5000m', ''),
            player.get('target_time', ''),
            'FALSE',
            player.get('grade', ''),
            player.get('school', ''),
            player.get('height', ''),
            player.get('weight', ''),
            player.get('message', ''),
            player.get('photo_url', '')
        )
    return False

# ============ Records (記録データ) ============

def get_all_records():
    """全記録を取得（キャッシュ付き）"""
    cached = _get_cache('all_records')
    if cached is not None:
        return cached

    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Records')
    except gspread.exceptions.WorksheetNotFound:
        return []

    records = worksheet.get_all_records()
    # 行番号を追加（編集・削除用）
    for i, record in enumerate(records):
        record['row_index'] = i + 2  # ヘッダー行 + 0-indexed
    _set_cache('all_records', records)
    return records

def get_records_by_player(player_id):
    """選手IDで記録を取得"""
    records = get_all_records()
    return [r for r in records if str(r.get('player_id')) == str(player_id)]

def add_record(player_id, event, time, memo='', date=None):
    """記録を追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Records')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Records', rows=1000, cols=5)
        worksheet.append_row(['date', 'player_id', 'event', 'time', 'memo'])

    if date is None:
        date = datetime.now().strftime('%Y/%m/%d')
    else:
        # YYYY-MM-DD形式をYYYY/MM/DDに変換
        date = date.replace('-', '/')

    worksheet.append_row([date, player_id, event, time, memo])
    clear_cache()  # キャッシュクリア

def update_record(row_index, date, player_id, event, time, memo=''):
    """記録を更新"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Records')
    except gspread.exceptions.WorksheetNotFound:
        return False

    date = date.replace('-', '/')
    worksheet.update(f'A{row_index}:E{row_index}', [[date, player_id, event, time, memo]])
    clear_cache()  # キャッシュクリア
    return True

def delete_record(row_index):
    """記録を削除"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Records')
    except gspread.exceptions.WorksheetNotFound:
        return False

    worksheet.delete_rows(row_index)
    clear_cache()  # キャッシュクリア
    return True

def get_record_by_row(row_index):
    """行番号で記録を取得"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Records')
    except gspread.exceptions.WorksheetNotFound:
        return None

    row = worksheet.row_values(row_index)
    if len(row) >= 4:
        return {
            'date': row[0],
            'player_id': row[1],
            'event': row[2],
            'time': row[3],
            'memo': row[4] if len(row) > 4 else '',
            'row_index': row_index
        }
    return None

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

# ============ 統計機能 ============

def get_team_statistics():
    """チーム統計を取得"""
    players = get_all_players()
    records = get_all_records()

    stats = {
        'total_players': len(players),
        'total_records': len(records),
        'groups': {},
        'recent_records': [],
        'event_counts': {}
    }

    # グループ別人数
    for player in players:
        group = player.get('group', '未分類')
        stats['groups'][group] = stats['groups'].get(group, 0) + 1

    # 種目別記録数
    for record in records:
        event = record.get('event', '不明')
        stats['event_counts'][event] = stats['event_counts'].get(event, 0) + 1

    # 最近の記録（最新10件）
    sorted_records = sorted(records, key=lambda x: x.get('date', ''), reverse=True)
    stats['recent_records'] = sorted_records[:10]

    return stats

def get_personal_bests(player_id):
    """選手の種目別自己ベストを取得"""
    records = get_records_by_player(player_id)
    pbs = {}

    # タイムを秒に変換する関数
    def time_to_seconds(time_str):
        parts = time_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return float('inf')

    for record in records:
        event = record.get('event', '')
        time = record.get('time', '')
        date = record.get('date', '')

        if event and time:
            current_seconds = time_to_seconds(time)
            if event not in pbs or current_seconds < time_to_seconds(pbs[event]['time']):
                pbs[event] = {'time': time, 'date': date}

    return pbs
