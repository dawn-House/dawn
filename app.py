from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

# Временное хранилище
pending_payments = {}

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

@app.route('/api/create-payment', methods=['POST'])
def create_payment():
    data = request.get_json()
    label = str(uuid.uuid4())[:8]
    pending_payments[label] = data
    return jsonify({'link': 'https://yoomoney.ru', 'label': label})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
