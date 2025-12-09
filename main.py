import os
import io
import csv
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from services import sheet_api

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ekiden-app-secret-key')

# ============ 選手一覧 (ホーム) ============

@app.route("/")
def index():
    """選手一覧画面"""
    try:
        players = sheet_api.get_all_players()
        groups = list(set(p.get('group', '') for p in players if p.get('group')))

        # ソートパラメータ
        sort_by = request.args.get('sort', 'name')
        if sort_by == 'name':
            players = sorted(players, key=lambda x: x.get('name', ''))
        elif sort_by == 'group':
            players = sorted(players, key=lambda x: x.get('group', ''))
        elif sort_by == 'best_5000m':
            players = sorted(players, key=lambda x: x.get('best_5000m', '') or 'ZZZ')

        # 表示モード
        view_mode = request.args.get('view', 'card')

        return render_template('index.html',
                               players=players,
                               groups=sorted(groups),
                               sort_by=sort_by,
                               view_mode=view_mode)
    except Exception as e:
        flash(f'データの取得に失敗しました: {str(e)}', 'danger')
        return render_template('index.html', players=[], groups=[], sort_by='name', view_mode='card')

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
            name = request.form.get('name')
            group = request.form.get('group')
            best_5000m = request.form.get('best_5000m', '')
            target_time = request.form.get('target_time', '')
            grade = request.form.get('grade', '')
            school = request.form.get('school', '')
            height = request.form.get('height', '')
            weight = request.form.get('weight', '')
            message = request.form.get('message', '')
            photo_url = request.form.get('photo_url', '')

            sheet_api.add_player(name, group, best_5000m, target_time, grade, school, height, weight, message, photo_url)
            flash(f'{name}さんを登録しました', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'登録に失敗しました: {str(e)}', 'danger')

    return render_template('player_add.html')

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
            name = request.form.get('name')
            group = request.form.get('group')
            best_5000m = request.form.get('best_5000m', '')
            target_time = request.form.get('target_time', '')
            active = request.form.get('active', 'TRUE')
            grade = request.form.get('grade', '')
            school = request.form.get('school', '')
            height = request.form.get('height', '')
            weight = request.form.get('weight', '')
            message = request.form.get('message', '')
            photo_url = request.form.get('photo_url', '')

            sheet_api.update_player(player_id, name, group, best_5000m, target_time, active, grade, school, height, weight, message, photo_url)
            flash(f'{name}さんの情報を更新しました', 'success')
            return redirect(url_for('player_detail', player_id=player_id))
        except Exception as e:
            flash(f'更新に失敗しました: {str(e)}', 'danger')

    return render_template('player_edit.html', player=player)

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

            sheet_api.add_record(player_id, event, time, memo, date, race_id, distance_km)
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

            sheet_api.update_record(row_index, date, player_id, event, time, memo, race_id, distance_km)
            flash('記録を更新しました', 'success')
            return redirect(url_for('player_detail', player_id=player_id))
        except Exception as e:
            flash(f'更新に失敗しました: {str(e)}', 'danger')

    players = sheet_api.get_all_players()
    # 日付フォーマットを変換（YYYY/MM/DD → YYYY-MM-DD）
    record['date'] = record['date'].replace('/', '-')
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
        writer.writerow(['ID', '氏名', '所属', '5000m PB', '目標タイム', 'アクティブ', '学年', '出身校', '身長', '体重', '意気込み'])

        for p in players:
            writer.writerow([
                p.get('id', ''),
                p.get('name', ''),
                p.get('group', ''),
                p.get('best_5000m', ''),
                p.get('target_time', ''),
                p.get('active', ''),
                p.get('grade', ''),
                p.get('school', ''),
                p.get('height', ''),
                p.get('weight', ''),
                p.get('message', '')
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

# ============ メイン ============

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
