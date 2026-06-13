from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '<h1>Dawn House</h1><p>Сайт работает!</p>'

@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
