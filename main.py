import os
import io
import csv
import json
import calendar
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from services import sheet_api

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ekiden-app-secret-key')

# ============ カスタムJinja2フィルター ============

import re

@app.template_filter('parse_distance_km')
def parse_distance_km(value):
    """距離文字列をkm単位の数値に変換するフィルター

    対応形式:
    - "5.8km" → 5.8
    - "5800m" → 5.8
    - "5800" (数値のみ、メートル想定) → 5.8
    - 5800 (数値) → 5.8
    """
    if value is None or value == '':
        return None

    value_str = str(value).strip().lower()

    # 数値部分を抽出
    match = re.match(r'^([\d.]+)\s*(km|m)?$', value_str)
    if not match:
        return None

    try:
        num = float(match.group(1))
        unit = match.group(2)

        if unit == 'km':
            return round(num, 2)
        elif unit == 'm':
            return round(num / 1000, 2)
        else:
            # 単位なしの場合、100より大きければメートル、それ以下ならkm
            if num > 100:
                return round(num / 1000, 2)
            else:
                return round(num, 2)
    except (ValueError, TypeError):
        return None


@app.template_filter('calc_pace')
def calc_pace(time_str, distance_m):
    """タイムと距離から1km平均ペースを計算するフィルター

    Args:
        time_str: タイム文字列 (mm:ss または hh:mm:ss)
        distance_m: 距離（単位付き文字列対応: "5.8km", "5800m", "5800"）

    Returns:
        平均ペース文字列 (例: "3:45") または None
    """
    if not time_str or not distance_m:
        return None

    # 距離をkmに変換
    distance_km = parse_distance_km(distance_m)
    if not distance_km or distance_km <= 0:
        return None

    # タイムを秒に変換
    try:
        parts = time_str.split(':')
        if len(parts) == 3:
            total_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            total_seconds = int(parts[0]) * 60 + float(parts[1])
        else:
            return None
    except (ValueError, TypeError):
        return None

    if total_seconds <= 0:
        return None

    # 1kmあたりの秒数を計算
    pace_seconds = total_seconds / distance_km

    # mm:ss形式に変換
    pace_minutes = int(pace_seconds // 60)
    pace_secs = int(pace_seconds % 60)

    return f"{pace_minutes}:{pace_secs:02d}"


# ============ 選手一覧 (ホーム) ============

@app.route("/")
def index():
    """選手一覧画面"""
    try:
        all_players = sheet_api.get_all_players()

        # 現役選手と非現役選手を分離
        active_players = [p for p in all_players if p.get('status', '現役') == '現役' or not p.get('status')]
        inactive_players = [p for p in all_players if p.get('status') and p.get('status') != '現役']

        # カテゴリ一覧（現役選手のみから取得）
        categories = list(set(p.get('category', '') for p in active_players if p.get('category')))

        # ソートパラメータ
        sort_by = request.args.get('sort', 'name')
        if sort_by == 'name':
            active_players = sorted(active_players, key=lambda x: x.get('name', ''))
            inactive_players = sorted(inactive_players, key=lambda x: x.get('name', ''))
        elif sort_by == 'category':
            active_players = sorted(active_players, key=lambda x: x.get('category', ''))
            inactive_players = sorted(inactive_players, key=lambda x: x.get('category', ''))
        elif sort_by == 'pb_5000m':
            active_players = sorted(active_players, key=lambda x: x.get('pb_5000m', '') or 'ZZZ')
            inactive_players = sorted(inactive_players, key=lambda x: x.get('pb_5000m', '') or 'ZZZ')

        # 表示モード
        view_mode = request.args.get('view', 'card')

        return render_template('index.html',
                               players=active_players,
                               inactive_players=inactive_players,
                               categories=sorted(categories),
                               sort_by=sort_by,
                               view_mode=view_mode)
    except Exception as e:
        flash(f'データの取得に失敗しました: {str(e)}', 'danger')
        return render_template('index.html', players=[], inactive_players=[], categories=[], sort_by='name', view_mode='card')

# ============ 選手詳細 ============

@app.route("/player/<player_id>")
def player_detail(player_id):
    """選手詳細画面"""
    try:
        player = sheet_api.get_player_by_id(player_id)
        if not player:
            flash('選手が見つかりません', 'warning')
            return redirect(url_for('index'))

        records = sheet_api.get_records_by_player(player_id)
        records_json = json.dumps(records, ensure_ascii=False)
        personal_bests = sheet_api.get_personal_bests(player_id)

        return render_template('detail.html',
                               player=player,
                               records=records,
                               records_json=records_json,
                               personal_bests=personal_bests)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('index'))

# ============ 選手追加 ============

@app.route("/player/add", methods=['GET', 'POST'])
def player_add():
    """選手追加画面"""
    if request.method == 'POST':
        try:
            name_sei = request.form.get('name_sei')
            name_mei = request.form.get('name_mei')
            registration_number = request.form.get('registration_number', '')
            affiliation = request.form.get('affiliation', '')
            category = request.form.get('category', '')
            status = request.form.get('status', '現役')
            role = request.form.get('role', '')
            grade = request.form.get('grade', '')
            birth_date = request.form.get('birth_date', '')
            pb_1500m = request.form.get('pb_1500m', '')
            pb_3000m = request.form.get('pb_3000m', '')
            pb_5000m = request.form.get('pb_5000m', '')
            pb_10000m = request.form.get('pb_10000m', '')
            pb_half = request.form.get('pb_half', '')
            pb_full = request.form.get('pb_full', '')
            comment = request.form.get('comment', '')

            sheet_api.add_player(name_sei, name_mei, affiliation, category, status, role, grade, birth_date,
                                pb_1500m, pb_3000m, pb_5000m, pb_10000m, pb_half, pb_full, comment, registration_number)
            flash(f'{name_sei} {name_mei}さんを登録しました', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'登録に失敗しました: {str(e)}', 'danger')

    category_list = sheet_api.get_master_choices('category_list')
    status_list = sheet_api.get_master_choices('status_list')
    grade_list = sheet_api.get_master_choices('grade_list')
    affiliation_list = sheet_api.get_master_choices('affiliation_list')
    role_list = sheet_api.get_master_choices('role_list')
    return render_template('player_add.html',
                           category_list=category_list,
                           status_list=status_list,
                           grade_list=grade_list,
                           affiliation_list=affiliation_list,
                           role_list=role_list)

# ============ 選手編集 ============

@app.route("/player/<player_id>/edit", methods=['GET', 'POST'])
def player_edit(player_id):
    """選手編集画面"""
    player = sheet_api.get_player_by_id(player_id)
    if not player:
        flash('選手が見つかりません', 'warning')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            name_sei = request.form.get('name_sei')
            name_mei = request.form.get('name_mei')
            registration_number = request.form.get('registration_number', '')
            affiliation = request.form.get('affiliation', '')
            category = request.form.get('category', '')
            status = request.form.get('status', '現役')
            role = request.form.get('role', '')
            grade = request.form.get('grade', '')
            birth_date = request.form.get('birth_date', '')
            pb_1500m = request.form.get('pb_1500m', '')
            pb_3000m = request.form.get('pb_3000m', '')
            pb_5000m = request.form.get('pb_5000m', '')
            pb_10000m = request.form.get('pb_10000m', '')
            pb_half = request.form.get('pb_half', '')
            pb_full = request.form.get('pb_full', '')
            comment = request.form.get('comment', '')
            photo_url = request.form.get('photo_url', '').strip()
            is_deleted = '1' if request.form.get('is_deleted') else ''

            sheet_api.update_player(player_id, name_sei, name_mei, affiliation, category, status, role, grade, birth_date,
                                   pb_1500m, pb_3000m, pb_5000m, pb_10000m, pb_half, pb_full, comment, registration_number, photo_url, is_deleted)
            flash(f'{name_sei} {name_mei}さんの情報を更新しました', 'success')
            return redirect(url_for('player_detail', player_id=player_id))
        except Exception as e:
            flash(f'更新に失敗しました: {str(e)}', 'danger')

    category_list = sheet_api.get_master_choices('category_list')
    status_list = sheet_api.get_master_choices('status_list')
    grade_list = sheet_api.get_master_choices('grade_list')
    affiliation_list = sheet_api.get_master_choices('affiliation_list')
    role_list = sheet_api.get_master_choices('role_list')
    return render_template('player_edit.html',
                           player=player,
                           category_list=category_list,
                           status_list=status_list,
                           grade_list=grade_list,
                           affiliation_list=affiliation_list,
                           role_list=role_list)


# ============ 記録登録 ============

@app.route("/record/add", methods=['GET', 'POST'])
def record_add():
    """記録登録画面"""
    if request.method == 'POST':
        try:
            player_id = request.form.get('player_id')
            date = request.form.get('date')
            event = request.form.get('event')
            time = request.form.get('time')
            memo = request.form.get('memo', '')
            race_id = request.form.get('race_id', '')
            distance_km = request.form.get('distance_km', '')
            race_type = request.form.get('race_type', '')
            race_name = request.form.get('race_name', '')
            section = request.form.get('section', '')
            rank_in_section = request.form.get('rank_in_section', '')

            # 選手名を取得
            player = sheet_api.get_player_by_id(player_id)
            player_name = player.get('name', '') if player else ''

            sheet_api.add_record(
                player_id=player_id,
                event=event,
                time=time,
                memo=memo,
                date=date,
                race_id=race_id,
                distance_km=distance_km,
                section=section,
                rank_in_section=rank_in_section,
                player_name=player_name,
                race_name=race_name,
                race_type=race_type
            )
            flash('記録を登録しました', 'success')
            return redirect(url_for('player_detail', player_id=player_id))
        except Exception as e:
            flash(f'登録に失敗しました: {str(e)}', 'danger')

    players = sheet_api.get_all_players()
    selected_player_id = request.args.get('player_id', '')
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('record_add.html',
                           players=players,
                           selected_player_id=selected_player_id,
                           today=today)

# ============ 記録編集 ============

@app.route("/record/<int:row_index>/edit", methods=['GET', 'POST'])
def record_edit(row_index):
    """記録編集画面"""
    record = sheet_api.get_record_by_row(row_index)
    if not record:
        flash('記録が見つかりません', 'warning')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            date = request.form.get('date')
            player_id = request.form.get('player_id')
            event = request.form.get('event')
            time = request.form.get('time')
            memo = request.form.get('memo', '')
            race_id = request.form.get('race_id', '')
            distance_km = request.form.get('distance_km', '')
            race_type = request.form.get('race_type', '')
            race_name = request.form.get('race_name', '')
            section = request.form.get('section', '')
            rank_in_section = request.form.get('rank_in_section', '')

            # 選手名を取得
            player = sheet_api.get_player_by_id(player_id)
            player_name = player.get('name', '') if player else ''

            sheet_api.update_record(
                row_index=row_index,
                date=date,
                player_id=player_id,
                event=event,
                time=time,
                memo=memo,
                race_id=race_id,
                distance_km=distance_km,
                section=section,
                rank_in_section=rank_in_section,
                player_name=player_name,
                race_name=race_name,
                race_type=race_type
            )
            flash('記録を更新しました', 'success')
            return redirect(url_for('player_detail', player_id=player_id))
        except Exception as e:
            flash(f'更新に失敗しました: {str(e)}', 'danger')

    players = sheet_api.get_all_players()
    # 日付フォーマットを変換（YYYY/MM/DD → YYYY-MM-DD）
    if record.get('date'):
        record['date'] = record['date'].replace('/', '-')
    # 距離をkmに変換して表示
    if record.get('distance_m'):
        try:
            record['distance_km'] = str(float(record['distance_m']) / 1000)
        except:
            record['distance_km'] = ''
    return render_template('record_edit.html', record=record, players=players)

# ============ 記録削除 ============

@app.route("/record/<int:row_index>/delete", methods=['POST'])
def record_delete(row_index):
    """記録を削除"""
    try:
        record = sheet_api.get_record_by_row(row_index)
        player_id = record.get('player_id') if record else None

        sheet_api.delete_record(row_index)
        flash('記録を削除しました', 'success')

        if player_id:
            return redirect(url_for('player_detail', player_id=player_id))
    except Exception as e:
        flash(f'削除に失敗しました: {str(e)}', 'danger')

    return redirect(url_for('index'))

# ============ シミュレーション ============

@app.route("/simulation")
def simulation():
    """シミュレーション画面"""
    try:
        players = sheet_api.get_all_players()
        simulations = sheet_api.get_all_simulations()
        return render_template('simulation.html',
                               players=players,
                               simulations=simulations)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return render_template('simulation.html', players=[], simulations=[])

@app.route("/simulation/save", methods=['POST'])
def simulation_save():
    """シミュレーションを保存"""
    try:
        data = request.get_json()
        title = data.get('title')
        order_data = data.get('order_data', {})

        sheet_api.save_simulation(title, order_data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ チーム統計 ============

@app.route("/statistics")
def statistics():
    """チーム統計画面"""
    try:
        stats = sheet_api.get_team_statistics()
        players = sheet_api.get_all_players()

        # 選手名をIDから取得するための辞書
        player_names = {str(p.get('id')): p.get('name') for p in players}

        return render_template('statistics.html', stats=stats, player_names=player_names)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return render_template('statistics.html', stats={}, player_names={})

# ============ CSVエクスポート ============

@app.route("/export/players")
def export_players():
    """選手一覧をCSVエクスポート"""
    try:
        players = sheet_api.get_all_players_including_inactive()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', '登録番号', '姓', '名', '氏名', '生年月日', '学年', '所属', 'カテゴリ', 'ステータス',
                        '1500m PB', '3000m PB', '5000m PB', '10000m PB', 'ハーフPB', 'フルPB', 'コメント'])

        for p in players:
            writer.writerow([
                p.get('id', ''),
                p.get('registration_number', ''),
                p.get('name_sei', ''),
                p.get('name_mei', ''),
                p.get('name', ''),
                p.get('birth_date', ''),
                p.get('grade', ''),
                p.get('affiliation', ''),
                p.get('category', ''),
                p.get('status', ''),
                p.get('pb_1500m', ''),
                p.get('pb_3000m', ''),
                p.get('pb_5000m', ''),
                p.get('pb_10000m', ''),
                p.get('pb_half', ''),
                p.get('pb_full', ''),
                p.get('comment', '')
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=players.csv'}
        )
    except Exception as e:
        flash(f'エクスポートに失敗しました: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route("/export/records")
def export_records():
    """記録一覧をCSVエクスポート"""
    try:
        records = sheet_api.get_all_records()
        players = sheet_api.get_all_players()
        player_names = {str(p.get('id')): p.get('name') for p in players}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['日付', '選手ID', '選手名', '種目', 'タイム', 'メモ'])

        for r in records:
            player_id = str(r.get('player_id', ''))
            writer.writerow([
                r.get('date', ''),
                player_id,
                player_names.get(player_id, ''),
                r.get('event', ''),
                r.get('time', ''),
                r.get('memo', '')
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=records.csv'}
        )
    except Exception as e:
        flash(f'エクスポートに失敗しました: {str(e)}', 'danger')
        return redirect(url_for('index'))

# ============ 大会管理 ============

@app.route("/races")
def races():
    """大会一覧画面（Recordsから集計）"""
    try:
        race_list = sheet_api.get_races_from_records()
        return render_template('races.html', races=race_list)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return render_template('races.html', races=[])

@app.route("/race/detail/<path:race_name>")
def race_detail(race_name):
    """大会詳細画面（Recordsから取得）"""
    try:
        race_list = sheet_api.get_races_from_records()
        race = None
        for r in race_list:
            if r['race_name'] == race_name:
                race = r
                break

        if not race:
            flash('大会が見つかりません', 'warning')
            return redirect(url_for('races'))

        # 選手情報を取得
        players = sheet_api.get_all_players()
        player_dict = {str(p.get('id')): p for p in players}

        return render_template('race_detail.html', race=race, player_dict=player_dict)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('races'))

@app.route("/race/section/<path:race_name>/<section>")
def section_result(race_name, section):
    """区間別結果画面（Recordsテーブルから）"""
    try:
        result = sheet_api.get_section_results(race_name, section)

        if not result['records']:
            flash('該当する記録が見つかりません', 'warning')
            return redirect(url_for('races'))

        return render_template('section_result.html', result=result)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('races'))

@app.route("/ekiden/section/<int:edition>/<path:leg>")
def ekiden_section_result(edition, leg):
    """縦断駅伝区間別結果画面（全チーム表示）"""
    try:
        result = sheet_api.get_ekiden_section_results(edition, leg)

        if 'error' in result and result.get('error'):
            flash(result['error'], 'warning')
            return redirect(url_for('analysis_menu'))

        if not result['records']:
            flash('該当する記録が見つかりません', 'warning')
            return redirect(url_for('analysis_menu'))

        return render_template('ekiden_section_result.html', result=result)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('analysis_menu'))

@app.route("/race/add", methods=['GET', 'POST'])
def race_add():
    """大会追加画面"""
    if request.method == 'POST':
        try:
            race_name = request.form.get('race_name')
            short_name = request.form.get('short_name', '')
            location = request.form.get('location', '')
            race_type = request.form.get('type', '')
            section_count = request.form.get('section_count', '')
            importance = request.form.get('importance', '')
            memo = request.form.get('memo', '')

            sheet_api.add_race(race_name, short_name, location, race_type, section_count, importance, memo)
            flash(f'{race_name}を登録しました', 'success')
            return redirect(url_for('races'))
        except Exception as e:
            flash(f'登録に失敗しました: {str(e)}', 'danger')

    race_types = sheet_api.get_master_choices('race_type_list')
    importance_list = sheet_api.get_master_choices('importance_list')
    return render_template('race_add.html', race_types=race_types, importance_list=importance_list)

@app.route("/race/<race_id>/edit", methods=['GET', 'POST'])
def race_edit(race_id):
    """大会編集画面"""
    race = sheet_api.get_race_by_id(race_id)
    if not race:
        flash('大会が見つかりません', 'warning')
        return redirect(url_for('races'))

    if request.method == 'POST':
        try:
            race_name = request.form.get('race_name')
            short_name = request.form.get('short_name', '')
            location = request.form.get('location', '')
            race_type = request.form.get('type', '')
            section_count = request.form.get('section_count', '')
            importance = request.form.get('importance', '')
            memo = request.form.get('memo', '')

            sheet_api.update_race(race_id, race_name, short_name, location, race_type, section_count, importance, memo)
            flash('大会情報を更新しました', 'success')
            return redirect(url_for('races'))
        except Exception as e:
            flash(f'更新に失敗しました: {str(e)}', 'danger')

    race_types = sheet_api.get_master_choices('race_type_list')
    importance_list = sheet_api.get_master_choices('importance_list')
    return render_template('race_edit.html', race=race, race_types=race_types, importance_list=importance_list)

@app.route("/race/<race_id>/delete", methods=['POST'])
def race_delete(race_id):
    """大会を削除"""
    try:
        sheet_api.delete_race(race_id)
        flash('大会を削除しました', 'success')
    except Exception as e:
        flash(f'削除に失敗しました: {str(e)}', 'danger')
    return redirect(url_for('races'))

# ============ 駅伝メニュー ============

# 山形県縦断駅伝の親race_name（１日目〜３日目をまとめる）
KENJUDAN_PARENT = '山形県縦断駅伝競走大会'

@app.route("/ekiden")
def ekiden_menu():
    """駅伝メニュー画面"""
    try:
        all_races = sheet_api.get_all_races()
        # 駅伝大会のみフィルタリング（race_nameに「駅伝」を含むもの）
        ekiden_races = [r for r in all_races if '駅伝' in r.get('race_name', '')]
        # 山形県縦断駅伝の「X日目」は除外（親の「山形県縦断駅伝競走大会」のみ表示）
        ekiden_races = [r for r in ekiden_races
                        if not (KENJUDAN_PARENT in r.get('race_name', '')
                               and r.get('race_name', '') != KENJUDAN_PARENT)]
        return render_template('ekiden_menu.html', ekiden_races=ekiden_races)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return render_template('ekiden_menu.html', ekiden_races=[])

@app.route("/ekiden/<race_id>")
def ekiden_race_detail(race_id):
    """駅伝大会別の記録一覧"""
    try:
        race = sheet_api.get_race_by_id(race_id)
        if not race:
            flash('大会が見つかりません', 'warning')
            return redirect(url_for('ekiden_menu'))

        all_records = sheet_api.get_all_team_records()

        # 山形県縦断駅伝の場合、１日目〜３日目も含めて取得
        if race.get('race_name') == KENJUDAN_PARENT:
            all_races = sheet_api.get_all_races()
            # 「山形県縦断駅伝競走大会」を含む全てのrace_idを取得
            related_race_ids = [r.get('race_id') for r in all_races
                               if KENJUDAN_PARENT in r.get('race_name', '')]
            records = [r for r in all_records if r.get('race_id') in related_race_ids]
        else:
            records = [r for r in all_records if r.get('race_id') == race_id]

        # 日付の新しい順にソート
        records = sorted(records, key=lambda x: x.get('date', ''), reverse=True)

        return render_template('ekiden_race_detail.html', race=race, records=records)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('ekiden_menu'))

# ============ チーム記録管理 ============

@app.route("/team_records")
def team_records():
    """チーム記録一覧画面"""
    try:
        records = sheet_api.get_all_team_records()
        race_list = sheet_api.get_all_races()
        race_dict = {r.get('race_id'): r for r in race_list}
        return render_template('team_records.html', records=records, race_dict=race_dict)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return render_template('team_records.html', records=[], race_dict={})

@app.route("/team_record/add", methods=['GET', 'POST'])
def team_record_add():
    """チーム記録追加画面"""
    if request.method == 'POST':
        try:
            race_id = request.form.get('race_id')
            edition = request.form.get('edition', '')
            date = request.form.get('date', '')
            total_time = request.form.get('total_time')
            total_time_sec = request.form.get('total_time_sec', '')
            rank = request.form.get('rank', '')
            total_teams = request.form.get('total_teams', '')
            category = request.form.get('category', '')
            team_name = request.form.get('team_name', '')
            memo = request.form.get('memo', '')

            team_record_id = sheet_api.add_team_record(race_id, edition, date, total_time, total_time_sec, rank, total_teams, category, team_name, memo)
            flash('チーム記録を登録しました', 'success')
            return redirect(url_for('team_record_detail', team_record_id=team_record_id))
        except Exception as e:
            flash(f'登録に失敗しました: {str(e)}', 'danger')

    races = sheet_api.get_all_races()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('team_record_add.html', races=races, today=today)

@app.route("/team_record/<team_record_id>")
def team_record_detail(team_record_id):
    """チーム記録詳細画面"""
    try:
        record = sheet_api.get_team_record_by_id(team_record_id)
        if not record:
            flash('チーム記録が見つかりません', 'warning')
            return redirect(url_for('team_records'))

        race = sheet_api.get_race_by_id(record.get('race_id'))
        # Recordsテーブルから区間記録を取得（section順でソート済み）
        section_records = sheet_api.get_records_by_team_record(team_record_id)
        players = sheet_api.get_all_players()
        player_dict = {str(p.get('id')): p for p in players}

        return render_template('team_record_detail.html',
                               record=record,
                               race=race,
                               section_records=section_records,
                               player_dict=player_dict,
                               players=players)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('team_records'))

@app.route("/team_record/<team_record_id>/delete", methods=['POST'])
def team_record_delete(team_record_id):
    """チーム記録を削除"""
    try:
        sheet_api.delete_team_record(team_record_id)
        flash('チーム記録を削除しました', 'success')
    except Exception as e:
        flash(f'削除に失敗しました: {str(e)}', 'danger')
    return redirect(url_for('team_records'))

# ============ チーム記録の区間管理 ============

@app.route("/team_record/<team_record_id>/section/add", methods=['POST'])
def team_record_section_add(team_record_id):
    """チーム記録に区間記録を追加（Recordsテーブルに登録）"""
    try:
        # TeamRecordから情報を取得
        team_record = sheet_api.get_team_record_by_id(team_record_id)
        if not team_record:
            flash('チーム記録が見つかりません', 'warning')
            return redirect(url_for('team_records'))

        # フォームデータ取得
        section = request.form.get('section')
        player_id = request.form.get('player_id')
        time = request.form.get('time', '')
        rank_in_section = request.form.get('rank_in_section', '')
        distance_km = request.form.get('distance_km', '')
        memo = request.form.get('memo', '')

        # 選手情報を取得
        player = sheet_api.get_player_by_id(player_id)
        player_name = player.get('name', '') if player else ''

        # 大会情報を取得
        race = sheet_api.get_race_by_id(team_record.get('race_id'))
        race_name = race.get('race_name', '') if race else ''
        race_type = race.get('type', '') if race else ''

        # Recordsテーブルに追加
        sheet_api.add_record(
            player_id=player_id,
            event='',
            time=time,
            memo=memo,
            date=team_record.get('date'),
            race_id=team_record.get('race_id'),
            distance_km=distance_km,
            section=section,
            rank_in_section=rank_in_section,
            player_name=player_name,
            race_name=race_name,
            race_type=race_type,
            team_record_id=team_record_id
        )
        flash('区間記録を追加しました', 'success')
    except Exception as e:
        flash(f'追加に失敗しました: {str(e)}', 'danger')
    return redirect(url_for('team_record_detail', team_record_id=team_record_id))

# ============ マスタ管理 ============

@app.route("/masters")
def masters():
    """マスタ管理画面"""
    try:
        all_masters = sheet_api.get_all_masters()
        # タイプ別にグループ化
        grouped = {}
        for m in all_masters:
            t = m.get('type', '未分類')
            if t not in grouped:
                grouped[t] = []
            grouped[t].append(m)
        return render_template('masters.html', grouped_masters=grouped)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return render_template('masters.html', grouped_masters={})

@app.route("/master/add", methods=['POST'])
def master_add():
    """マスタを追加"""
    try:
        master_type = request.form.get('type')
        code = request.form.get('code')
        name = request.form.get('name')
        sort_order = request.form.get('sort_order', 0)
        memo = request.form.get('memo', '')

        sheet_api.add_master(master_type, code, name, sort_order, memo)
        flash('マスタを追加しました', 'success')
    except Exception as e:
        flash(f'追加に失敗しました: {str(e)}', 'danger')
    return redirect(url_for('masters'))

@app.route("/master/delete", methods=['POST'])
def master_delete():
    """マスタを削除"""
    try:
        master_type = request.form.get('type')
        code = request.form.get('code')
        sheet_api.delete_master(master_type, code)
        flash('マスタを削除しました', 'success')
    except Exception as e:
        flash(f'削除に失敗しました: {str(e)}', 'danger')
    return redirect(url_for('masters'))

# ============ カレンダー ============

@app.route("/calendar")
def calendar_view():
    """カレンダー画面"""
    try:
        # 年月パラメータ取得（デフォルトは今月）
        today = datetime.now()
        year = int(request.args.get('year', today.year))
        month = int(request.args.get('month', today.month))

        # カレンダーデータ作成
        cal = calendar.Calendar(firstweekday=6)  # 日曜始まり
        month_days = cal.monthdayscalendar(year, month)

        # イベント取得
        events = sheet_api.get_events_by_month(year, month)
        # 練習日誌取得
        practice_logs = sheet_api.get_all_practice_logs()
        logs_by_date = {log.get('date'): log for log in practice_logs}

        # 日付ごとのイベントをマップ
        events_by_date = {}
        for event in events:
            date = event.get('date', '')
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)

        # 前月・次月
        prev_month = month - 1
        prev_year = year
        if prev_month < 1:
            prev_month = 12
            prev_year -= 1

        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1

        event_types = sheet_api.get_master_choices('event_type_list')

        return render_template('calendar.html',
                               year=year,
                               month=month,
                               month_days=month_days,
                               events_by_date=events_by_date,
                               logs_by_date=logs_by_date,
                               prev_year=prev_year,
                               prev_month=prev_month,
                               next_year=next_year,
                               next_month=next_month,
                               today=today.strftime('%Y-%m-%d'),
                               event_types=event_types)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return render_template('calendar.html',
                               year=datetime.now().year,
                               month=datetime.now().month,
                               month_days=[],
                               events_by_date={},
                               logs_by_date={},
                               prev_year=datetime.now().year,
                               prev_month=datetime.now().month,
                               next_year=datetime.now().year,
                               next_month=datetime.now().month,
                               today=datetime.now().strftime('%Y-%m-%d'),
                               event_types=[])

@app.route("/event/add", methods=['GET', 'POST'])
def event_add():
    """イベント追加画面"""
    if request.method == 'POST':
        try:
            date = request.form.get('date')
            event_type = request.form.get('event_type')
            title = request.form.get('title')
            start_time = request.form.get('start_time', '')
            end_time = request.form.get('end_time', '')
            location = request.form.get('location', '')
            memo = request.form.get('memo', '')

            sheet_api.add_event(date, event_type, title, start_time, end_time, location, memo)
            flash('予定を追加しました', 'success')
            return redirect(url_for('calendar_view'))
        except Exception as e:
            flash(f'登録に失敗しました: {str(e)}', 'danger')

    event_types = sheet_api.get_master_choices('event_type_list')
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    return render_template('event_add.html', event_types=event_types, date=date)

@app.route("/event/<event_id>/edit", methods=['GET', 'POST'])
def event_edit(event_id):
    """イベント編集画面"""
    event = sheet_api.get_event_by_id(event_id)
    if not event:
        flash('予定が見つかりません', 'warning')
        return redirect(url_for('calendar_view'))

    if request.method == 'POST':
        try:
            date = request.form.get('date')
            event_type = request.form.get('event_type')
            title = request.form.get('title')
            start_time = request.form.get('start_time', '')
            end_time = request.form.get('end_time', '')
            location = request.form.get('location', '')
            memo = request.form.get('memo', '')

            sheet_api.update_event(event_id, date, event_type, title, start_time, end_time, location, memo)
            flash('予定を更新しました', 'success')
            return redirect(url_for('calendar_view'))
        except Exception as e:
            flash(f'更新に失敗しました: {str(e)}', 'danger')

    event_types = sheet_api.get_master_choices('event_type_list')
    return render_template('event_edit.html', event=event, event_types=event_types)

@app.route("/event/<event_id>/delete", methods=['POST'])
def event_delete(event_id):
    """イベントを削除"""
    try:
        sheet_api.delete_event(event_id)
        flash('予定を削除しました', 'success')
    except Exception as e:
        flash(f'削除に失敗しました: {str(e)}', 'danger')
    return redirect(url_for('calendar_view'))

# ============ 練習日誌 ============

@app.route("/practice_logs")
def practice_logs():
    """練習日誌一覧画面"""
    try:
        logs = sheet_api.get_all_practice_logs()
        return render_template('practice_logs.html', logs=logs)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return render_template('practice_logs.html', logs=[])

@app.route("/practice_log/add", methods=['GET', 'POST'])
def practice_log_add():
    """練習日誌追加画面"""
    if request.method == 'POST':
        try:
            date = request.form.get('date')
            title = request.form.get('title')
            content = request.form.get('content', '')
            weather = request.form.get('weather', '')
            temperature = request.form.get('temperature', '')
            participants = request.form.get('participants', '')
            memo = request.form.get('memo', '')

            log_id = sheet_api.add_practice_log(date, title, content, weather, temperature, participants, memo)
            flash('練習日誌を追加しました', 'success')
            return redirect(url_for('practice_log_detail', log_id=log_id))
        except Exception as e:
            flash(f'登録に失敗しました: {str(e)}', 'danger')

    weather_list = sheet_api.get_master_choices('weather_list')
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    return render_template('practice_log_add.html', weather_list=weather_list, date=date)

@app.route("/practice_log/<log_id>")
def practice_log_detail(log_id):
    """練習日誌詳細画面"""
    try:
        log = sheet_api.get_practice_log_by_id(log_id)
        if not log:
            flash('練習日誌が見つかりません', 'warning')
            return redirect(url_for('practice_logs'))

        # その日の出欠データ取得
        attendance = sheet_api.get_attendance_by_date(log.get('date', ''))
        players = sheet_api.get_all_players()
        player_dict = {str(p.get('id')): p for p in players}

        return render_template('practice_log_detail.html',
                               log=log,
                               attendance=attendance,
                               player_dict=player_dict)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('practice_logs'))

@app.route("/practice_log/<log_id>/edit", methods=['GET', 'POST'])
def practice_log_edit(log_id):
    """練習日誌編集画面"""
    log = sheet_api.get_practice_log_by_id(log_id)
    if not log:
        flash('練習日誌が見つかりません', 'warning')
        return redirect(url_for('practice_logs'))

    if request.method == 'POST':
        try:
            date = request.form.get('date')
            title = request.form.get('title')
            content = request.form.get('content', '')
            weather = request.form.get('weather', '')
            temperature = request.form.get('temperature', '')
            participants = request.form.get('participants', '')
            memo = request.form.get('memo', '')

            sheet_api.update_practice_log(log_id, date, title, content, weather, temperature, participants, memo)
            flash('練習日誌を更新しました', 'success')
            return redirect(url_for('practice_log_detail', log_id=log_id))
        except Exception as e:
            flash(f'更新に失敗しました: {str(e)}', 'danger')

    weather_list = sheet_api.get_master_choices('weather_list')
    return render_template('practice_log_edit.html', log=log, weather_list=weather_list)

@app.route("/practice_log/<log_id>/delete", methods=['POST'])
def practice_log_delete(log_id):
    """練習日誌を削除"""
    try:
        sheet_api.delete_practice_log(log_id)
        flash('練習日誌を削除しました', 'success')
    except Exception as e:
        flash(f'削除に失敗しました: {str(e)}', 'danger')
    return redirect(url_for('practice_logs'))

# ============ 出欠管理 ============

@app.route("/attendance")
def attendance():
    """出欠管理画面"""
    try:
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        players = sheet_api.get_all_players()
        attendance_data = sheet_api.get_attendance_by_date(date)

        # 選手ごとの出欠をマップ
        attendance_by_player = {str(a.get('player_id')): a for a in attendance_data}

        # 出欠ステータス選択肢
        status_list = sheet_api.get_master_choices('attendance_status_list')
        if not status_list:
            status_list = [('出席', '出席'), ('欠席', '欠席'), ('遅刻', '遅刻'), ('早退', '早退')]

        return render_template('attendance.html',
                               date=date,
                               players=players,
                               attendance_by_player=attendance_by_player,
                               status_list=status_list)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return render_template('attendance.html',
                               date=datetime.now().strftime('%Y-%m-%d'),
                               players=[],
                               attendance_by_player={},
                               status_list=[])

@app.route("/attendance/save", methods=['POST'])
def attendance_save():
    """出欠を保存"""
    try:
        date = request.form.get('date')
        players = sheet_api.get_all_players()

        attendance_list = []
        for player in players:
            player_id = str(player.get('id'))
            status = request.form.get(f'status_{player_id}', '')
            memo = request.form.get(f'memo_{player_id}', '')

            if status:  # ステータスが設定されている場合のみ追加
                attendance_list.append({
                    'player_id': player_id,
                    'status': status,
                    'memo': memo
                })

        sheet_api.update_attendance_by_date(date, attendance_list)
        flash('出欠を保存しました', 'success')
    except Exception as e:
        flash(f'保存に失敗しました: {str(e)}', 'danger')

    return redirect(url_for('attendance', date=request.form.get('date')))

@app.route("/attendance/player/<player_id>")
def attendance_player(player_id):
    """選手別出欠履歴"""
    try:
        player = sheet_api.get_player_by_id(player_id)
        if not player:
            flash('選手が見つかりません', 'warning')
            return redirect(url_for('index'))

        attendance_data = sheet_api.get_attendance_by_player(player_id)
        attendance_rate = sheet_api.get_player_attendance_rate(player_id)

        return render_template('attendance_player.html',
                               player=player,
                               attendance=attendance_data,
                               attendance_rate=attendance_rate)
    except Exception as e:
        flash(f'エラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('index'))

# ============ ペース分析 ============

@app.route("/analysis")
def analysis_menu():
    """分析メニュー画面"""
    return render_template('analysis_menu.html')

@app.route("/pace_analysis")
def pace_analysis():
    """県縦断駅伝ペース分析画面"""
    legs = sheet_api.get_ekiden_legs()
    positions = list(range(1, 12))  # 1〜11位
    teams = sheet_api.get_ekiden_teams()
    editions = sheet_api.get_ekiden_editions()
    return render_template('pace_analysis.html',
                           legs=legs,
                           positions=positions,
                           teams=teams,
                           editions=editions)


@app.route("/api/pace_analysis")
def api_pace_analysis():
    """ペース分析APIエンドポイント"""
    leg = request.args.get('leg', '第１区遊佐～酒田')
    position = request.args.get('position', '1')

    try:
        data = sheet_api.filter_ekiden_pace_data(leg, position)
        if isinstance(data, dict) and 'error' in data:
            return jsonify({'error': data['error']}), 400
        return jsonify({'data': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/team_sections")
def api_team_sections():
    """チーム大会別区間一覧APIエンドポイント"""
    team = request.args.get('team', '南陽東置賜')
    edition = request.args.get('edition', '60')

    try:
        data = sheet_api.get_team_edition_sections(team, edition)
        if isinstance(data, dict) and 'error' in data:
            return jsonify({'error': data['error']}), 400
        return jsonify({'data': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/team_section_all_editions")
def api_team_section_all_editions():
    """チーム区間全大会一覧APIエンドポイント"""
    team = request.args.get('team', '南陽東置賜')
    leg = request.args.get('leg', '第１区遊佐～酒田')

    try:
        data = sheet_api.get_team_section_all_editions(team, leg)
        if isinstance(data, dict) and 'error' in data:
            return jsonify({'error': data['error']}), 400
        return jsonify({'data': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ メイン ============

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
