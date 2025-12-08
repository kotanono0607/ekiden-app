import os
import gspread
import google.auth
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    try:
        # 認証とスプレッドシートを開く
        credentials, project = google.auth.default(scopes=['https://www.googleapis.com/auth/spreadsheets'])
        gc = gspread.authorize(credentials)
        
        # あなたのID (設定済み)
        SPREADSHEET_ID = '1emj5sW_saJpydDTva7mH5pi00YA2QIloCi_rKx_cbdU'
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.sheet1
        data = worksheet.get_all_values()

        # データを表にする
        rows_html = ""
        for row in data:
            rows_html += "<tr>" + "".join([f"<td style='border: 1px solid #ccc; padding: 8px;'>{cell}</td>" for cell in row]) + "</tr>"

        return f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>駅伝アプリ</title>
                <style>body {{ font-family: sans-serif; padding: 20px; text-align: center; }} table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}</style>
            </head>
            <body>
                <h2 style="color:#4285F4;">🏃‍♂️ 選手名簿</h2>
                <p>連携成功！データ表示中</p>
                <table border="1">
                    {rows_html}
                </table>
            </body>
        </html>
        """
    except Exception as e:
        return f"<h3>エラー</h3><p>{str(e)}</p>"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))