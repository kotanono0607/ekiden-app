import os
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return """
    <div style="text-align: center; margin-top: 50px; font-family: sans-serif;">
        <h1 style="color: #4285F4;">Hello World!</h1>
        <p>スマホからこの画面が見えていますか？</p>
        <p>GitHub連携とCloud Runのテスト成功です！</p>
    </div>
    """

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
