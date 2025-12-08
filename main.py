import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
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
        return render_template('index.html', players=players, groups=sorted(groups))
    except Exception as e:
        flash(f'データの取得に失敗しました: {str(e)}', 'danger')
        return render_template('index.html', players=[], groups=[])

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

        return render_template('detail.html',
                               player=player,
                               records=records,
                               records_json=records_json)
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

            sheet_api.add_player(name, group, best_5000m, target_time)
            flash(f'{name}さんを登録しました', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'登録に失敗しました: {str(e)}', 'danger')

    return render_template('player_add.html')

# ============ 記録登録 ============

@app.route("/record/add", methods=['GET', 'POST'])
def record_add():
    """記録登録画面"""
    if request.method == 'POST':
        try:
            player_id = request.form.get('player_id')
            event = request.form.get('event')
            time = request.form.get('time')
            memo = request.form.get('memo', '')

            sheet_api.add_record(player_id, event, time, memo)
            flash('記録を登録しました', 'success')
            return redirect(url_for('player_detail', player_id=player_id))
        except Exception as e:
            flash(f'登録に失敗しました: {str(e)}', 'danger')

    players = sheet_api.get_all_players()
    selected_player_id = request.args.get('player_id', '')
    return render_template('record_add.html',
                           players=players,
                           selected_player_id=selected_player_id)

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

# ============ メイン ============

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
