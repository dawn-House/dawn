from flask import Flask

# ЭТА СТРОКА ОБЯЗАТЕЛЬНА - создаём экземпляр приложения
app = Flask(__name__)

@app.route('/')
def home():
    return 'Dawn House работает!'

@app.route('/health')
def health():
    return 'OK', 200

# Только для локального запуска (на Railway эту часть не используют)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
