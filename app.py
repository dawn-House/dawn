from flask import Flask, request

app = Flask(__name__)

@app.route('/')
def home():
    return 'Dawn House works!'

@app.route('/health')
def health():
    return 'OK'

@app.route('/yoomoney', methods=['POST'])
def yoomoney_notification():
    print("Получен запрос на /yoomoney")
    print(request.form.to_dict())
    return "OK", 200
