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
CACHE_TTL = 120  # 通常キャッシュ有効期間（秒）- 2分
CACHE_TTL_LONG = 600  # 長期キャッシュ有効期間（秒）- 10分（駅伝データ等）

# 長期キャッシュ対象のキー
LONG_CACHE_KEYS = {'ekiden_individual', 'ekiden_temperature'}

def _get_cache(key):
    """キャッシュからデータを取得"""
    if key in _cache:
        data, timestamp = _cache[key]
        ttl = CACHE_TTL_LONG if key in LONG_CACHE_KEYS else CACHE_TTL
        if time.time() - timestamp < ttl:
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

PLAYER_COLUMN_MAPPING = {
    'group': 'affiliation',  # スプレッドシートの'group'を'affiliation'に変換
    'category': 'category',
    'status': 'status',
}

RECORD_COLUMN_MAPPING = {
    'race_id': 'race_id',
}

# スプレッドシートの期待するヘッダー（仕様書準拠）
PLAYER_EXPECTED_HEADERS = [
    'id', 'registration_number', 'name_sei', 'name_mei', 'birth_date',
    'grade', 'affiliation', 'category', 'status', 'role', 'race_count',
    'pb_1500m', 'pb_3000m', 'pb_5000m', 'pb_10000m', 'pb_half', 'pb_full',
    'comment', 'is_deleted', 'created_at', 'updated_at'
]

RECORD_EXPECTED_HEADERS = [
    'record_id', 'player_id', 'race_id', 'date', 'event', 'section',
    'distance_m', 'time', 'time_sec', 'is_pb', 'is_section_record',
    'split_times_json', 'rank_in_section', 'memo', 'created_at', 'updated_at',
    'player_name', 'race_name', 'race_type'  # CSV参照用カラム
]

RACES_EXPECTED_HEADERS = [
    'race_id', 'race_name', 'short_name', 'date', 'location',
    'type', 'section_count', 'importance', 'memo', 'created_at', 'updated_at'
]

TEAM_RECORDS_EXPECTED_HEADERS = [
    'team_record_id', 'race_id', 'total_time', 'total_time_sec',
    'rank', 'total_teams', 'category', 'memo', 'created_at', 'updated_at'
]

RACE_ORDERS_EXPECTED_HEADERS = [
    'order_id', 'team_record_id', 'section_no', 'section_name',
    'player_id', 'record_id', 'memo', 'distance_m'
]

MASTERS_EXPECTED_HEADERS = [
    'type', 'code', 'name', 'sort_order', 'memo'
]

def normalize_player(player):
    """スプレッドシートのカラム名をアプリ内部の名前に変換"""
    normalized = {}
    for key, value in player.items():
        new_key = PLAYER_COLUMN_MAPPING.get(key, key)
        normalized[new_key] = value
    # name_sei + name_mei を結合して name を生成
    name_sei = normalized.get('name_sei', '')
    name_mei = normalized.get('name_mei', '')
    normalized['name'] = f"{name_sei} {name_mei}".strip()
    return normalized

def normalize_players(players):
    """選手リストを正規化"""
    return [normalize_player(p) for p in players]

def normalize_record(record):
    """記録のカラム名をアプリ内部の名前に変換"""
    normalized = {}
    for key, value in record.items():
        new_key = RECORD_COLUMN_MAPPING.get(key, key)
        normalized[new_key] = value
    return normalized

def normalize_records(records):
    """記録リストを正規化"""
    return [normalize_record(r) for r in records]

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

    # 仕様: 1行目=物理名, 2行目=論理名, 3行目以降=データ
    all_values = worksheet.get_all_values()
    if len(all_values) < 3:
        return []

    headers = all_values[0]  # 1行目: 物理名
    # 2行目(論理名)はスキップ、3行目以降がデータ
    records = []
    for row in all_values[2:]:
        record = dict(zip(headers, row))
        records.append(record)

    # カラム名を正規化
    records = normalize_players(records)
    # is_deletedがTRUEでない選手のみフィルタ
    result = [p for p in records if str(p.get('is_deleted', '')).upper() != 'TRUE']
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

    # 仕様: 1行目=物理名, 2行目=論理名, 3行目以降=データ
    all_values = worksheet.get_all_values()
    if len(all_values) < 3:
        return []

    headers = all_values[0]
    records = []
    for row in all_values[2:]:
        record = dict(zip(headers, row))
        records.append(record)

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

    # 仕様: 1行目=物理名, 2行目=論理名, 3行目以降=データ
    all_values = worksheet.get_all_values()
    if len(all_values) < 3:
        return None

    headers = all_values[0]
    for row in all_values[2:]:
        record = dict(zip(headers, row))
        player = normalize_player(record)
        if str(player.get('id')) == str(player_id):
            return player
    return None

def add_player(name_sei, name_mei, affiliation='', category='', status='現役', role='', grade='', birth_date='',
               pb_1500m='', pb_3000m='', pb_5000m='', pb_10000m='', pb_half='', pb_full='',
               comment='', registration_number=''):
    """選手を追加（仕様書準拠）"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Players')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Players', rows=500, cols=21)
        worksheet.append_row(PLAYER_EXPECTED_HEADERS)
        worksheet.append_row(['システムID', '登録番号', '姓', '名', '生年月日', '学年', '所属', '区分', '状態', '役職', '出場回数',
                              'PB 1500m', 'PB 3000m', 'PB 5000m', 'PB 10000m', 'PB ハーフ', 'PB フル',
                              '備考', '削除フラグ', '作成日時', '更新日時'])

    # 新しいIDを生成
    all_values = worksheet.get_all_values()
    new_id = f"P{len(all_values):03d}"

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # カラム順: id, registration_number, name_sei, name_mei, birth_date, grade, affiliation, category, status, role, race_count,
    #          pb_1500m, pb_3000m, pb_5000m, pb_10000m, pb_half, pb_full, comment, is_deleted, created_at, updated_at
    worksheet.append_row([
        new_id, registration_number, name_sei, name_mei, birth_date, grade, affiliation, category, status, role, 0,
        pb_1500m, pb_3000m, pb_5000m, pb_10000m, pb_half, pb_full,
        comment, 'FALSE', now, now
    ])
    clear_cache()
    return new_id

def update_player(player_id, name_sei, name_mei, affiliation='', category='', status='現役', role='', grade='', birth_date='',
                  pb_1500m='', pb_3000m='', pb_5000m='', pb_10000m='', pb_half='', pb_full='',
                  comment='', registration_number='', is_deleted='FALSE'):
    """選手を更新（仕様書準拠）"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Players')
    except gspread.exceptions.WorksheetNotFound:
        return False

    # IDで行を検索（2行目は論理名なのでスキップ）
    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:  # ヘッダー行と論理名行をスキップ
            continue
        if str(row[0]) == str(player_id):
            # race_countとcreated_atを保持
            race_count = row[10] if len(row) > 10 else 0
            created_at = row[19] if len(row) > 19 else ''
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            row_num = i + 1
            worksheet.update(f'A{row_num}:U{row_num}', [[
                player_id, registration_number, name_sei, name_mei, birth_date, grade, affiliation, category, status, role, race_count,
                pb_1500m, pb_3000m, pb_5000m, pb_10000m, pb_half, pb_full,
                comment, is_deleted, created_at, now
            ]])
            clear_cache()
            return True
    return False

def delete_player(player_id):
    """選手を削除（論理削除 - is_deletedをTRUEに設定）"""
    player = get_player_by_id(player_id)
    if player:
        return update_player(
            player_id,
            player.get('name_sei', ''),
            player.get('name_mei', ''),
            player.get('affiliation', ''),
            player.get('category', ''),
            player.get('status', ''),
            player.get('role', ''),
            player.get('grade', ''),
            player.get('birth_date', ''),
            player.get('pb_1500m', ''),
            player.get('pb_3000m', ''),
            player.get('pb_5000m', ''),
            player.get('pb_10000m', ''),
            player.get('pb_half', ''),
            player.get('pb_full', ''),
            player.get('comment', ''),
            player.get('registration_number', ''),
            is_deleted='TRUE'
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

    # 仕様: 1行目=物理名, 2行目=論理名, 3行目以降=データ
    all_values = worksheet.get_all_values()
    if len(all_values) < 3:
        return []

    headers = all_values[0]
    records = []
    for i, row in enumerate(all_values[2:]):
        record = dict(zip(headers, row))
        # 行番号を追加（編集・削除用）- データは3行目(1-indexed)から
        record['row_index'] = i + 3
        records.append(record)

    # カラム名を正規化
    records = normalize_records(records)
    _set_cache('all_records', records)
    return records

def get_records_by_player(player_id):
    """選手IDで記録を取得"""
    records = get_all_records()
    return [r for r in records if str(r.get('player_id')) == str(player_id)]

def add_record(player_id, event, time, memo='', date=None, race_id='', distance_km='',
               time_sec='', is_pb=False, is_section_record=False,
               section='', rank_in_section='', player_name='', race_name='', race_type=''):
    """記録を追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Records')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Records', rows=1000, cols=20)
        worksheet.append_row(RECORD_EXPECTED_HEADERS)

    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    # 距離をメートルに変換
    distance_m = ''
    if distance_km:
        try:
            distance_m = str(float(distance_km) * 1000)
        except:
            distance_m = distance_km

    # 新しいrecord_idを生成
    all_values = worksheet.get_all_values()
    new_record_id = f"R{len(all_values):03d}"

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # カラム順: record_id, player_id, race_id, date, event, section, distance_m, time, time_sec,
    #          is_pb, is_section_record, split_times_json, rank_in_section, memo, created_at, updated_at,
    #          player_name, race_name, race_type
    worksheet.append_row([
        new_record_id, player_id, race_id, date, event, section,
        distance_m, time, time_sec, is_pb, is_section_record,
        '', rank_in_section, memo, now, now,
        player_name, race_name, race_type
    ])
    clear_cache()  # キャッシュクリア

def update_record(row_index, date, player_id, event, time, memo='', race_id='', distance_km='',
                  time_sec='', is_pb=False, is_section_record=False,
                  section='', rank_in_section='', player_name='', race_name='', race_type=''):
    """記録を更新"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Records')
    except gspread.exceptions.WorksheetNotFound:
        return False

    # 距離をメートルに変換
    distance_m = ''
    if distance_km:
        try:
            distance_m = str(float(distance_km) * 1000)
        except:
            distance_m = distance_km

    # 既存の行データを取得（record_id, split_times_json, created_atを保持するため）
    existing_row = worksheet.row_values(row_index)
    record_id = existing_row[0] if len(existing_row) > 0 else ''
    split_times_json = existing_row[11] if len(existing_row) > 11 else ''
    created_at = existing_row[14] if len(existing_row) > 14 else ''

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # カラム順: record_id, player_id, race_id, date, event, section, distance_m, time, time_sec,
    #          is_pb, is_section_record, split_times_json, rank_in_section, memo, created_at, updated_at,
    #          player_name, race_name, race_type
    worksheet.update(f'A{row_index}:S{row_index}', [[
        record_id, player_id, race_id, date, event, section,
        distance_m, time, time_sec, is_pb, is_section_record,
        split_times_json, rank_in_section, memo, created_at, now,
        player_name, race_name, race_type
    ]])
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
    # カラム順: record_id, player_id, race_id, date, section, distance_km, time, time_sec, is_pb, is_section_record, split_times_json, rank_in_section, memo, created_at, updated_at
    if len(row) >= 7:
        return {
            'record_id': row[0],
            'player_id': row[1],
            'race_id': row[2],
            'date': row[3],
            'event': row[4],  # section → event
            'distance_km': row[5] if len(row) > 5 else '',
            'time': row[6] if len(row) > 6 else '',
            'time_sec': row[7] if len(row) > 7 else '',
            'is_pb': row[8] if len(row) > 8 else '',
            'is_section_record': row[9] if len(row) > 9 else '',
            'memo': row[12] if len(row) > 12 else '',
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

    # 所属別人数
    for player in players:
        affiliation = player.get('affiliation', '未分類')
        stats['groups'][affiliation] = stats['groups'].get(affiliation, 0) + 1

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

# ============ Masters (汎用マスタ) ============

def get_all_masters():
    """全マスタデータを取得（キャッシュ付き）"""
    cached = _get_cache('all_masters')
    if cached is not None:
        return cached

    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Masters')
    except gspread.exceptions.WorksheetNotFound:
        return []

    # 仕様: 1行目=物理名, 2行目=論理名, 3行目以降=データ
    all_values = worksheet.get_all_values()
    if len(all_values) < 3:
        return []

    headers = all_values[0]
    records = []
    for row in all_values[2:]:
        record = dict(zip(headers, row))
        records.append(record)

    _set_cache('all_masters', records)
    return records

def get_masters_by_type(master_type):
    """種別でマスタを取得"""
    masters = get_all_masters()
    filtered = [m for m in masters if m.get('type') == master_type]
    return sorted(filtered, key=lambda x: int(x.get('sort_order', 0) or 0))

def get_master_choices(master_type):
    """マスタの選択肢リストを取得 (code, name)のタプルリスト"""
    masters = get_masters_by_type(master_type)
    return [(m.get('code', ''), m.get('name', '')) for m in masters]

def add_master(master_type, code, name, sort_order=0, memo=''):
    """マスタを追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Masters')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Masters', rows=500, cols=5)
        worksheet.append_row(MASTERS_EXPECTED_HEADERS)
        worksheet.append_row(['マスタ種別', 'コード値', '表示名', '表示順', 'メモ'])

    worksheet.append_row([master_type, code, name, sort_order, memo])
    clear_cache()

def delete_master(master_type, code):
    """マスタを削除"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Masters')
    except gspread.exceptions.WorksheetNotFound:
        return False

    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:  # ヘッダー行をスキップ
            continue
        if row[0] == master_type and row[1] == code:
            worksheet.delete_rows(i + 1)
            clear_cache()
            return True
    return False

# ============ Races (大会マスタ) ============

def get_all_races():
    """全大会を取得（キャッシュ付き）"""
    cached = _get_cache('all_races')
    if cached is not None:
        return cached

    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Races')
    except gspread.exceptions.WorksheetNotFound:
        return []

    all_values = worksheet.get_all_values()
    if len(all_values) < 3:
        return []

    headers = all_values[0]
    records = []
    for i, row in enumerate(all_values[2:]):
        record = dict(zip(headers, row))
        record['row_index'] = i + 3
        records.append(record)

    _set_cache('all_races', records)
    return records

def get_races_from_records():
    """Recordsテーブルから大会別に集計したデータを取得"""
    records = get_all_records()

    # 選手IDから名前を引くための辞書を作成
    players = get_all_players()
    player_dict = {str(p.get('id')): p.get('name', '') for p in players}

    # race_nameでグルーピング
    race_dict = {}
    for record in records:
        race_name = record.get('race_name', '').strip()
        if not race_name:
            continue

        if race_name not in race_dict:
            race_dict[race_name] = {
                'race_name': race_name,
                'race_type': record.get('race_type', ''),
                'date': record.get('date', ''),
                'records': [],
                'player_names': set()
            }

        race_dict[race_name]['records'].append(record)
        # player_nameがなければplayer_idから取得
        player_name = record.get('player_name', '')
        if not player_name:
            player_id = str(record.get('player_id', ''))
            player_name = player_dict.get(player_id, '')
        if player_name:
            race_dict[race_name]['player_names'].add(player_name)

    # リストに変換し、日付でソート（新しい順）
    races = []
    for race_name, data in race_dict.items():
        races.append({
            'race_name': race_name,
            'race_type': data['race_type'],
            'date': data['date'],
            'record_count': len(data['records']),
            'player_count': len(data['player_names']),
            'player_names': list(data['player_names']),
            'records': data['records']
        })

    # 日付で降順ソート
    races.sort(key=lambda x: x['date'], reverse=True)
    return races

def get_race_by_id(race_id):
    """IDで大会を取得"""
    races = get_all_races()
    for race in races:
        if str(race.get('race_id')) == str(race_id):
            return race
    return None

def get_section_results(race_name, section):
    """特定の大会・区間の全結果を取得"""
    records = get_all_records()

    # 選手IDから選手情報を引くための辞書
    players = get_all_players()
    player_dict = {str(p.get('id')): p for p in players}

    # 該当する記録をフィルタリング
    section_records = []
    race_date = ''
    race_type = ''
    distance_m = ''

    for record in records:
        rec_race_name = record.get('race_name', '').strip()
        rec_section = record.get('section', '').strip()

        if rec_race_name == race_name and rec_section == section:
            # 選手情報を追加
            player_id = str(record.get('player_id', ''))
            player = player_dict.get(player_id, {})
            record['player'] = player
            if not record.get('player_name') and player:
                record['player_name'] = player.get('name', '')

            section_records.append(record)

            # 大会情報を取得（最初の1件から）
            if not race_date:
                race_date = record.get('date', '')
            if not race_type:
                race_type = record.get('race_type', '')
            if not distance_m:
                distance_m = record.get('distance_m', '')

    # タイムでソート（区間順位がある場合はそれを優先）
    def sort_key(r):
        rank = r.get('rank_in_section', '')
        if rank and str(rank).isdigit():
            return (0, int(rank), r.get('time', 'ZZZ'))
        return (1, 999, r.get('time', 'ZZZ'))

    section_records.sort(key=sort_key)

    return {
        'race_name': race_name,
        'section': section,
        'date': race_date,
        'race_type': race_type,
        'distance_m': distance_m,
        'records': section_records,
        'record_count': len(section_records)
    }

def add_race(race_name, short_name, date, location='', race_type='', section_count='', importance='', memo=''):
    """大会を追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Races')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Races', rows=500, cols=11)
        worksheet.append_row(RACES_EXPECTED_HEADERS)
        worksheet.append_row(['大会ID', '大会名', '略称', '開催日', '開催地', '大会タイプ', '区間数', '重要度', '備考', '作成日時', '更新日時'])

    all_values = worksheet.get_all_values()
    new_race_id = f"RAC{len(all_values):03d}"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    worksheet.append_row([
        new_race_id, race_name, short_name, date, location,
        race_type, section_count, importance, memo, now, now
    ])
    clear_cache()
    return new_race_id

def update_race(race_id, race_name, short_name, date, location='', race_type='', section_count='', importance='', memo=''):
    """大会を更新"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Races')
    except gspread.exceptions.WorksheetNotFound:
        return False

    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:
            continue
        if str(row[0]) == str(race_id):
            created_at = row[9] if len(row) > 9 else ''
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            worksheet.update(f'A{i+1}:K{i+1}', [[
                race_id, race_name, short_name, date, location,
                race_type, section_count, importance, memo, created_at, now
            ]])
            clear_cache()
            return True
    return False

def delete_race(race_id):
    """大会を削除"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Races')
    except gspread.exceptions.WorksheetNotFound:
        return False

    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:
            continue
        if str(row[0]) == str(race_id):
            worksheet.delete_rows(i + 1)
            clear_cache()
            return True
    return False

# ============ TeamRecords (チーム記録) ============

def get_all_team_records():
    """全チーム記録を取得（キャッシュ付き）"""
    cached = _get_cache('all_team_records')
    if cached is not None:
        return cached

    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('TeamRecords')
    except gspread.exceptions.WorksheetNotFound:
        return []

    all_values = worksheet.get_all_values()
    if len(all_values) < 3:
        return []

    headers = all_values[0]
    records = []
    for i, row in enumerate(all_values[2:]):
        record = dict(zip(headers, row))
        record['row_index'] = i + 3
        records.append(record)

    _set_cache('all_team_records', records)
    return records

def get_team_record_by_id(team_record_id):
    """IDでチーム記録を取得"""
    records = get_all_team_records()
    for record in records:
        if str(record.get('team_record_id')) == str(team_record_id):
            return record
    return None

def add_team_record(race_id, total_time, total_time_sec='', rank='', total_teams='', category='', memo=''):
    """チーム記録を追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('TeamRecords')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='TeamRecords', rows=500, cols=10)
        worksheet.append_row(TEAM_RECORDS_EXPECTED_HEADERS)
        worksheet.append_row(['チーム記録ID', '大会ID', '総合タイム', '総合タイム(秒)', '総合順位', '出場チーム数', '出場カテゴリ', 'メモ', '作成日時', '更新日時'])

    all_values = worksheet.get_all_values()
    new_id = f"TR{len(all_values):03d}"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    worksheet.append_row([
        new_id, race_id, total_time, total_time_sec,
        rank, total_teams, category, memo, now, now
    ])
    clear_cache()
    return new_id

def update_team_record(team_record_id, race_id, total_time, total_time_sec='', rank='', total_teams='', category='', memo=''):
    """チーム記録を更新"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('TeamRecords')
    except gspread.exceptions.WorksheetNotFound:
        return False

    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:
            continue
        if str(row[0]) == str(team_record_id):
            created_at = row[8] if len(row) > 8 else ''
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            worksheet.update(f'A{i+1}:J{i+1}', [[
                team_record_id, race_id, total_time, total_time_sec,
                rank, total_teams, category, memo, created_at, now
            ]])
            clear_cache()
            return True
    return False

def delete_team_record(team_record_id):
    """チーム記録を削除"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('TeamRecords')
    except gspread.exceptions.WorksheetNotFound:
        return False

    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:
            continue
        if str(row[0]) == str(team_record_id):
            worksheet.delete_rows(i + 1)
            clear_cache()
            return True
    return False

# ============ RaceOrders (大会オーダー) ============

def get_race_orders_by_team_record(team_record_id):
    """チーム記録IDで大会オーダーを取得"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('RaceOrders')
    except gspread.exceptions.WorksheetNotFound:
        return []

    all_values = worksheet.get_all_values()
    if len(all_values) < 3:
        return []

    headers = all_values[0]
    records = []
    for i, row in enumerate(all_values[2:]):
        record = dict(zip(headers, row))
        record['row_index'] = i + 3
        if str(record.get('team_record_id')) == str(team_record_id):
            records.append(record)

    return sorted(records, key=lambda x: int(x.get('section_no', 0) or 0))

def add_race_order(team_record_id, section_no, section_name, player_id, record_id='', memo='', distance_m=''):
    """大会オーダーを追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('RaceOrders')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='RaceOrders', rows=500, cols=8)
        worksheet.append_row(RACE_ORDERS_EXPECTED_HEADERS)
        worksheet.append_row(['オーダーID', 'チーム記録ID', '区間番号', '区間名', '選手ID', '記録ID', 'メモ', '距離(m)'])

    all_values = worksheet.get_all_values()
    new_id = f"ORD{len(all_values):03d}"

    worksheet.append_row([
        new_id, team_record_id, section_no, section_name, player_id, record_id, memo, distance_m
    ])
    clear_cache()
    return new_id

def update_race_order(order_id, team_record_id, section_no, section_name, player_id, record_id='', memo=''):
    """大会オーダーを更新"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('RaceOrders')
    except gspread.exceptions.WorksheetNotFound:
        return False

    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:
            continue
        if str(row[0]) == str(order_id):
            worksheet.update(f'A{i+1}:G{i+1}', [[
                order_id, team_record_id, section_no, section_name, player_id, record_id, memo
            ]])
            clear_cache()
            return True
    return False

def delete_race_order(order_id):
    """大会オーダーを削除"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('RaceOrders')
    except gspread.exceptions.WorksheetNotFound:
        return False

    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:
            continue
        if str(row[0]) == str(order_id):
            worksheet.delete_rows(i + 1)
            clear_cache()
            return True
    return False

# ============ Events (カレンダー予定) ============

EVENTS_EXPECTED_HEADERS = [
    'event_id', 'date', 'event_type', 'title', 'start_time', 'end_time',
    'location', 'memo', 'created_at', 'updated_at'
]

def get_all_events():
    """全イベントを取得（キャッシュ付き）"""
    cached = _get_cache('all_events')
    if cached is not None:
        return cached

    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Events')
    except gspread.exceptions.WorksheetNotFound:
        return []

    all_values = worksheet.get_all_values()
    if len(all_values) < 3:
        return []

    headers = all_values[0]
    records = []
    for i, row in enumerate(all_values[2:]):
        record = dict(zip(headers, row))
        record['row_index'] = i + 3
        records.append(record)

    _set_cache('all_events', records)
    return records

def get_events_by_month(year, month):
    """指定月のイベントを取得"""
    events = get_all_events()
    month_prefix = f"{year}-{month:02d}"
    return [e for e in events if e.get('date', '').startswith(month_prefix)]

def get_event_by_id(event_id):
    """IDでイベントを取得"""
    events = get_all_events()
    for event in events:
        if str(event.get('event_id')) == str(event_id):
            return event
    return None

def add_event(date, event_type, title, start_time='', end_time='', location='', memo=''):
    """イベントを追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Events')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Events', rows=500, cols=10)
        worksheet.append_row(EVENTS_EXPECTED_HEADERS)
        worksheet.append_row(['予定ID', '日付', '種別', 'タイトル', '開始時刻', '終了時刻', '場所', 'メモ', '作成日時', '更新日時'])

    all_values = worksheet.get_all_values()
    new_id = f"EVT{len(all_values):03d}"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    worksheet.append_row([
        new_id, date, event_type, title, start_time, end_time,
        location, memo, now, now
    ])
    clear_cache()
    return new_id

def update_event(event_id, date, event_type, title, start_time='', end_time='', location='', memo=''):
    """イベントを更新"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Events')
    except gspread.exceptions.WorksheetNotFound:
        return False

    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:
            continue
        if str(row[0]) == str(event_id):
            created_at = row[8] if len(row) > 8 else ''
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            worksheet.update(f'A{i+1}:J{i+1}', [[
                event_id, date, event_type, title, start_time, end_time,
                location, memo, created_at, now
            ]])
            clear_cache()
            return True
    return False

def delete_event(event_id):
    """イベントを削除"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Events')
    except gspread.exceptions.WorksheetNotFound:
        return False

    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:
            continue
        if str(row[0]) == str(event_id):
            worksheet.delete_rows(i + 1)
            clear_cache()
            return True
    return False

# ============ PracticeLogs (練習日誌) ============

PRACTICE_LOGS_EXPECTED_HEADERS = [
    'log_id', 'date', 'title', 'content', 'weather', 'temperature',
    'participants', 'memo', 'created_at', 'updated_at'
]

def get_all_practice_logs():
    """全練習日誌を取得（キャッシュ付き）"""
    cached = _get_cache('all_practice_logs')
    if cached is not None:
        return cached

    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('PracticeLogs')
    except gspread.exceptions.WorksheetNotFound:
        return []

    all_values = worksheet.get_all_values()
    if len(all_values) < 3:
        return []

    headers = all_values[0]
    records = []
    for i, row in enumerate(all_values[2:]):
        record = dict(zip(headers, row))
        record['row_index'] = i + 3
        records.append(record)

    # 日付の新しい順にソート
    records = sorted(records, key=lambda x: x.get('date', ''), reverse=True)
    _set_cache('all_practice_logs', records)
    return records

def get_practice_log_by_id(log_id):
    """IDで練習日誌を取得"""
    logs = get_all_practice_logs()
    for log in logs:
        if str(log.get('log_id')) == str(log_id):
            return log
    return None

def get_practice_log_by_date(date):
    """日付で練習日誌を取得"""
    logs = get_all_practice_logs()
    for log in logs:
        if log.get('date') == date:
            return log
    return None

def add_practice_log(date, title, content='', weather='', temperature='', participants='', memo=''):
    """練習日誌を追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('PracticeLogs')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='PracticeLogs', rows=500, cols=10)
        worksheet.append_row(PRACTICE_LOGS_EXPECTED_HEADERS)
        worksheet.append_row(['日誌ID', '日付', 'タイトル', '内容', '天候', '気温', '参加人数', 'メモ', '作成日時', '更新日時'])

    all_values = worksheet.get_all_values()
    new_id = f"LOG{len(all_values):03d}"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    worksheet.append_row([
        new_id, date, title, content, weather, temperature,
        participants, memo, now, now
    ])
    clear_cache()
    return new_id

def update_practice_log(log_id, date, title, content='', weather='', temperature='', participants='', memo=''):
    """練習日誌を更新"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('PracticeLogs')
    except gspread.exceptions.WorksheetNotFound:
        return False

    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:
            continue
        if str(row[0]) == str(log_id):
            created_at = row[8] if len(row) > 8 else ''
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            worksheet.update(f'A{i+1}:J{i+1}', [[
                log_id, date, title, content, weather, temperature,
                participants, memo, created_at, now
            ]])
            clear_cache()
            return True
    return False

def delete_practice_log(log_id):
    """練習日誌を削除"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('PracticeLogs')
    except gspread.exceptions.WorksheetNotFound:
        return False

    all_values = worksheet.get_all_values()
    for i, row in enumerate(all_values):
        if i < 2:
            continue
        if str(row[0]) == str(log_id):
            worksheet.delete_rows(i + 1)
            clear_cache()
            return True
    return False

# ============ Attendance (出欠) ============

ATTENDANCE_EXPECTED_HEADERS = [
    'attendance_id', 'date', 'player_id', 'status', 'memo', 'created_at'
]

def get_all_attendance():
    """全出欠データを取得（キャッシュ付き）"""
    cached = _get_cache('all_attendance')
    if cached is not None:
        return cached

    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Attendance')
    except gspread.exceptions.WorksheetNotFound:
        return []

    all_values = worksheet.get_all_values()
    if len(all_values) < 3:
        return []

    headers = all_values[0]
    records = []
    for i, row in enumerate(all_values[2:]):
        record = dict(zip(headers, row))
        record['row_index'] = i + 3
        records.append(record)

    _set_cache('all_attendance', records)
    return records

def get_attendance_by_date(date):
    """日付で出欠を取得"""
    attendance = get_all_attendance()
    return [a for a in attendance if a.get('date') == date]

def get_attendance_by_player(player_id):
    """選手IDで出欠を取得"""
    attendance = get_all_attendance()
    return [a for a in attendance if str(a.get('player_id')) == str(player_id)]

def get_player_attendance_rate(player_id):
    """選手の出席率を計算"""
    attendance = get_attendance_by_player(player_id)
    if not attendance:
        return None
    total = len(attendance)
    present = len([a for a in attendance if a.get('status') == '出席'])
    return round(present / total * 100, 1) if total > 0 else 0

def add_attendance(date, player_id, status, memo=''):
    """出欠を追加"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Attendance')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Attendance', rows=1000, cols=6)
        worksheet.append_row(ATTENDANCE_EXPECTED_HEADERS)
        worksheet.append_row(['出欠ID', '日付', '選手ID', '出欠', '備考', '作成日時'])

    all_values = worksheet.get_all_values()
    new_id = f"ATT{len(all_values):03d}"
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    worksheet.append_row([new_id, date, player_id, status, memo, now])
    clear_cache()
    return new_id

def add_attendance_bulk(date, attendance_list):
    """出欠を一括追加 (attendance_list: [{player_id, status, memo}, ...])"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Attendance')
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title='Attendance', rows=1000, cols=6)
        worksheet.append_row(ATTENDANCE_EXPECTED_HEADERS)
        worksheet.append_row(['出欠ID', '日付', '選手ID', '出欠', '備考', '作成日時'])

    all_values = worksheet.get_all_values()
    base_id = len(all_values)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    rows = []
    for i, att in enumerate(attendance_list):
        new_id = f"ATT{base_id + i:03d}"
        rows.append([new_id, date, att['player_id'], att['status'], att.get('memo', ''), now])

    if rows:
        worksheet.append_rows(rows)
        clear_cache()

def update_attendance_by_date(date, attendance_list):
    """指定日付の出欠を更新（既存データを削除して新規追加）"""
    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('Attendance')
    except gspread.exceptions.WorksheetNotFound:
        add_attendance_bulk(date, attendance_list)
        return

    # 既存の該当日付のデータを削除
    all_values = worksheet.get_all_values()
    rows_to_delete = []
    for i, row in enumerate(all_values):
        if i < 2:
            continue
        if len(row) > 1 and row[1] == date:
            rows_to_delete.append(i + 1)

    # 後ろから削除（インデックスがずれないように）
    for row_num in reversed(rows_to_delete):
        worksheet.delete_rows(row_num)

    clear_cache()
    # 新しいデータを追加
    add_attendance_bulk(date, attendance_list)


# ============ 県縦断駅伝ペース分析 ============

def get_ekiden_legs():
    """区間リストを取得"""
    return [
        '第１区遊佐～酒田',
        '第２区酒田～黒森',
        '第３区黒森～湯野浜',
        '第４区湯野浜～大山',
        '第５区大山～鶴岡',
        '第６区鶴岡～藤島',
        '第７区藤島～狩川',
        '第８区狩川～古口',
        '第９区古口～升形',
        '第１０区升形～鮭川',
        '第１１区鮭川～新庄',
        '第１２区新庄～舟形',
        '第１３区舟形～尾花沢',
        '第１４区尾花沢～村山',
        '第１５区村山～東根',
        '第１６区東根～天童',
        '第１７区天童～寒河江',
        '第１８区寒河江～大江',
        '第１９区大江～朝日',
        '第２０区朝日～白鷹',
        '第２１区白鷹～長井',
        '第２２区長井～川西',
        '第２３区川西～米沢',
        '第２４区米沢～上郷',
        '第２５区上郷～亀岡',
        '第２６区亀岡～高畠',
        '第２７区高畠～南陽',
        '第２８区南陽～上山',
        '第２９区上山～山形',
    ]


def _get_ekiden_individual_data():
    """個人シートからデータを取得（キャッシュ付き）"""
    cached = _get_cache('ekiden_individual')
    if cached is not None:
        return cached

    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('個人')
    except gspread.exceptions.WorksheetNotFound:
        return None, None

    all_values = worksheet.get_all_values()
    if len(all_values) < 2:
        return None, None

    header = all_values[0]
    data = all_values[1:]

    result = (header, data)
    _set_cache('ekiden_individual', result)
    return result


def _get_section_distance_from_records(leg, edition):
    """Recordsテーブルから区間距離を取得（m/km混在対応）"""
    import re
    records = get_all_records()

    # 区間番号を抽出（例: "第１区遊佐～酒田" → "1"）
    # 半角数字を試す
    leg_match = re.search(r'[第]?(\d+)[区]?', str(leg))
    if leg_match:
        leg_num = leg_match.group(1)
    else:
        # 全角数字を試す
        zen_match = re.search(r'[第]?([０-９]+)[区]?', str(leg))
        if zen_match:
            leg_num = zen_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        else:
            return None

    for record in records:
        race_name = record.get('race_name', '')
        section = record.get('section', '')
        distance_m_str = record.get('distance_m', '')

        if not distance_m_str:
            continue

        # 駅伝レースかつ大会回数が一致するか確認
        if '駅伝' not in race_name and '縦断' not in race_name:
            continue
        if str(edition) not in race_name:
            continue

        # 区間番号を抽出（半角・全角両対応）
        section_num = None
        section_match = re.search(r'(\d+)', str(section))
        if section_match:
            section_num = section_match.group(1)
        else:
            # 全角数字を試す
            zen_section_match = re.search(r'([０-９]+)', str(section))
            if zen_section_match:
                section_num = zen_section_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))

        if section_num is None:
            continue
        if section_num != leg_num:
            continue

        try:
            dist_val = float(distance_m_str)
            # m/km混在対応: 100より大きい場合はメートル、それ以下はkm
            if dist_val > 100:
                return dist_val / 1000  # メートル → km
            else:
                return dist_val  # 既にkm
        except (ValueError, TypeError):
            continue

    return None


def _get_ekiden_temperature_data():
    """区間気温シートからデータを取得（キャッシュ付き）"""
    cached = _get_cache('ekiden_temperature')
    if cached is not None:
        return cached

    sh = get_spreadsheet()
    try:
        worksheet = sh.worksheet('区間気温')
    except gspread.exceptions.WorksheetNotFound:
        return None, None

    all_values = worksheet.get_all_values()
    if len(all_values) < 2:
        return None, None

    header = all_values[0]
    data = all_values[1:]

    result = (header, data)
    _set_cache('ekiden_temperature', result)
    return result


def _get_value_for_edition(data, header, leg, edition):
    """指定された大会回数と区間に対応する値を取得"""
    try:
        leg_index = header.index(leg)
    except ValueError:
        return 'N/A'

    for row in data:
        if len(row) > 0 and str(row[0]) == str(edition):
            if leg_index < len(row):
                return row[leg_index]
    return 'N/A'


def _convert_time_to_seconds(time_str):
    """時間（hh:mm:ssまたはmm:ss）を秒に変換"""
    if not time_str:
        return 0

    parts = time_str.split(':')
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
    except (ValueError, TypeError):
        return 0
    return 0


def _calculate_avg_time(time_str, distance):
    """平均ペース（分:秒/km）を計算"""
    total_seconds = _convert_time_to_seconds(time_str)

    try:
        distance_float = float(distance)
        if distance_float <= 0:
            return 'N/A'
    except (ValueError, TypeError):
        return 'N/A'

    avg_time_per_km = total_seconds / distance_float

    avg_minutes = int(avg_time_per_km // 60)
    avg_seconds = avg_time_per_km % 60

    # 秒が60に近い場合、分を繰り上げ
    if avg_seconds >= 59.95:
        avg_minutes += 1
        avg_seconds = 0.0

    # 小数点第1位まで表示
    avg_seconds_str = f"{avg_seconds:.1f}"
    if avg_seconds < 10:
        avg_seconds_str = '0' + avg_seconds_str

    return f"{avg_minutes}:{avg_seconds_str}"


def filter_ekiden_pace_data(leg, position):
    """県縦断駅伝のペースデータをフィルタリングして取得"""
    individual_header, individual_data = _get_ekiden_individual_data()
    if individual_header is None:
        return {'error': '個人シートが見つかりません'}

    temp_header, temp_data = _get_ekiden_temperature_data()
    if temp_header is None:
        temp_header, temp_data = [], []

    # 区間のインデックスを取得
    try:
        leg_index = individual_header.index(leg)
    except ValueError:
        return {'error': f'指定された区間が見つかりません: {leg}'}

    results = []
    for row in individual_data:
        if leg_index >= len(row):
            continue

        cell_value = row[leg_index]
        if not cell_value:
            continue

        # データは「名前_年齢_アルファベット名_所属_順位_タイム」形式
        details = cell_value.split('_')
        if len(details) < 6:
            continue

        rank = details[4]
        if str(rank) != str(position):
            continue

        # チーム名と大会回数を取得
        team = row[0] if len(row) > 0 else ''
        edition = row[1] if len(row) > 1 else ''

        # 距離をRecordsから取得、気温は区間気温シートから取得
        distance = _get_section_distance_from_records(leg, edition)
        if distance is None:
            distance = 'N/A'
        temperature = _get_value_for_edition(temp_data, temp_header, leg, edition)

        # 平均ペースを計算
        time_str = details[5]
        avg_time = _calculate_avg_time(time_str, distance)

        results.append({
            'team': team,
            'edition': edition,
            'name': details[0],
            'year_of_birth': details[1],
            'name_alphabet': details[2],
            'affiliation': details[3],
            'rank': rank,
            'time': time_str,
            'distance': distance,
            'temperature': temperature,
            'avg_time': avg_time
        })

    return results


def get_ekiden_teams():
    """チーム一覧を取得"""
    return [
        '南陽東置賜',
        '北村山',
        '天童東村山',
        '新庄最上',
        '山形',
        '酒田飽海',
        '鶴岡田川',
        '米沢',
        '寒河江西村山',
        '長井西置賜',
        '上山',
    ]


def get_ekiden_editions():
    """大会回数一覧を取得"""
    return list(range(60, 69))  # 60〜68


def get_ekiden_section_results(edition, leg):
    """縦断駅伝の特定大会・区間の全チーム結果を取得"""
    individual_header, individual_data = _get_ekiden_individual_data()
    if individual_header is None:
        return {'error': '個人シートが見つかりません', 'records': []}

    temp_header, temp_data = _get_ekiden_temperature_data()
    if temp_header is None:
        temp_header, temp_data = [], []

    # 区間のインデックスを取得（完全一致または部分一致）
    leg_index = None
    actual_leg = leg

    # まず完全一致を試す
    if leg in individual_header:
        leg_index = individual_header.index(leg)
        actual_leg = leg
    else:
        # 部分一致で検索（例: "1区" → "第１区遊佐～酒田"）
        # 区間番号を抽出して検索
        import re
        match = re.search(r'(\d+)', str(leg))
        if match:
            section_num = match.group(1)
            # 全角数字にも対応
            section_num_zen = section_num.translate(str.maketrans('0123456789', '０１２３４５６７８９'))
            for i, header in enumerate(individual_header):
                if f'第{section_num}区' in header or f'第{section_num_zen}区' in header:
                    leg_index = i
                    actual_leg = header
                    break

    if leg_index is None:
        return {'error': f'指定された区間が見つかりません: {leg}', 'records': []}

    # 距離をRecordsテーブルから取得、気温は区間気温シートから取得
    distance = _get_section_distance_from_records(actual_leg, edition)
    if distance is None:
        distance = 'N/A'
    temperature = _get_value_for_edition(temp_data, temp_header, actual_leg, edition)

    results = []
    for row in individual_data:
        if len(row) < 2:
            continue

        # 大会回数でフィルタリング
        if str(row[1]) != str(edition):
            continue

        if leg_index >= len(row):
            continue

        cell_value = row[leg_index]
        if not cell_value:
            continue

        # データは「名前_生年_アルファベット名_所属_順位_タイム」形式
        details = cell_value.split('_')
        if len(details) < 6:
            continue

        team = row[0] if len(row) > 0 else ''
        time_str = details[5]
        avg_time = _calculate_avg_time(time_str, distance)

        results.append({
            'team': team,
            'name': details[0],
            'year_of_birth': details[1],
            'name_alphabet': details[2],
            'affiliation': details[3],
            'rank': details[4],
            'rank_int': int(details[4]) if details[4].isdigit() else 999,
            'time': time_str,
            'avg_time': avg_time
        })

    # 順位でソート
    results.sort(key=lambda x: x['rank_int'])

    return {
        'edition': edition,
        'leg': actual_leg,
        'distance': distance,
        'temperature': temperature,
        'records': results,
        'record_count': len(results)
    }


def get_team_edition_sections(team_name, edition):
    """チーム大会別区間一覧を取得"""
    individual_header, individual_data = _get_ekiden_individual_data()
    if individual_header is None:
        return {'error': '個人シートが見つかりません'}

    results = []

    # 該当チーム・回数の行を検索
    for row in individual_data:
        if len(row) < 2:
            continue

        if row[0] == team_name and str(row[1]) == str(edition):
            # 3列目以降の各区間データを処理
            for j in range(2, len(row)):
                cell = row[j]
                if not cell:
                    continue

                parts = cell.split('_')
                if len(parts) < 6:
                    continue

                results.append({
                    'section': individual_header[j] if j < len(individual_header) else '',
                    'name': parts[0],
                    'year_of_birth': parts[1],
                    'name_alphabet': parts[2],
                    'affiliation': parts[3],
                    'rank': parts[4],
                    'time': parts[5]
                })
            break

    return results


def get_team_section_all_editions(team_name, leg):
    """チーム区間全大会一覧を取得（距離・気温・平均タイム付き）"""
    individual_header, individual_data = _get_ekiden_individual_data()
    if individual_header is None:
        return {'error': '個人シートが見つかりません'}

    temp_header, temp_data = _get_ekiden_temperature_data()
    if temp_header is None:
        temp_header, temp_data = [], []

    # 区間のインデックスを取得
    try:
        leg_index = individual_header.index(leg)
    except ValueError:
        return {'error': f'区間が見つかりません: {leg}'}

    results = []

    for row in individual_data:
        if len(row) < 2:
            continue

        # チーム名でフィルタリング
        if row[0] != team_name:
            continue

        cell = row[leg_index] if leg_index < len(row) else ''
        if not cell:
            continue

        parts = cell.split('_')
        if len(parts) < 6:
            continue

        edition = row[1]

        # 距離をRecordsから取得、気温は区間気温シートから取得
        distance = _get_section_distance_from_records(leg, edition)
        if distance is None:
            distance = 'N/A'
        temperature = _get_value_for_edition(temp_data, temp_header, leg, edition)

        # 平均タイムを計算
        time_str = parts[5]
        avg_time = _calculate_avg_time(time_str, distance) if distance != 'N/A' else 'N/A'

        results.append({
            'edition': edition,
            'section': leg,
            'name': parts[0],
            'year_of_birth': parts[1],
            'affiliation': parts[3],
            'rank': parts[4],
            'time': time_str,
            'distance': distance,
            'temperature': temperature,
            'avg_time': avg_time
        })

    if not results:
        return {'error': '該当データがありません'}

    return results
