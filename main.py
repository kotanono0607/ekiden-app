import os
import gspread
import google.auth
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    try:
        # 1. Googleの認証情報を取得
        credentials, project = google.auth.default(scopes=['https://www.googleapis.com/auth/spreadsheets'])
        gc = gspread.authorize(credentials)

        # 2. あなたのスプレッドシートを開く
        SPREADSHEET_ID = '1emj5sW_saJpydDTva7mH5pi00YA2QIloCi_rKx_cbdU'
        sh = gc.open_by_key(SPREADSHEET_ID)
        
        # 3. 1枚目のシートのデータを全部持ってくる
        worksheet = sh.sheet1
        data = worksheet.get_all_values()

        # 4. データをHTMLの表にして表示する
        rows_html = ""
        for row in data:
            rows_html += "<tr>" + "".join([f"<td style='border: 1px solid #ccc; padding: 8px;'>{cell}</td>" for cell in row]) + "</tr>"

        return f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>駅伝アプリ</title>
                <style>
                    body {{ font-family: sans-serif; padding: 20px; text-align: center; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                    th, td {{ border: 1px solid #ccc; padding: 8px; }}
                    h2 {{ color: #4285F4; }}
                </style>
            </head>
            <body>
                <h2>🏃‍♂️ 選手名簿</h2>
                <p>スプレッドシート連携成功！</p>
                <table>
                    {rows_html}
                </table>
            </body>
        </html>
        """
    except Exception as e:
        return f"<h3>エラーが発生しました</h3><p>{str(e)}</p><p>スプレッドシートの共有設定を確認してください。</p>"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
