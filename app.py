from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'Dawn House works!'

@app.route('/health')
def health():
    return 'OK'
