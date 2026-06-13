from flask import Flask, request
import os
import hashlib
import json

app = Flask(__name__)

# Данные из личного кабинета YooMoney (замени на свои!)
YOOMONEY_WALLET = "410011234567890"  # Номер вашего кошелька
YOOMONEY_SECRET = "tUJj4wjTMYdDexqAn5WG61N4"  # Из настроек уведомлений

# Хранилище ожидающих платежей (временно)
pending_payments = {}

@app.route('/')
def home():
    return 'Dawn House работает!'

@app.route('/health')
def health():
    return 'OK', 200

# Эндпоинт для уведомлений от YooMoney
@app.route('/yoomoney', methods=['POST'])
def yoomoney_notification():
    data = request.form.to_dict()
    print(f"Получено уведомление: {data}")
    
    # Проверяем подпись
    if not verify_signature(data):
        return "Invalid signature", 400
    
    label = data.get('label')
    status = data.get('status')
    
    if status == 'success' and label in pending_payments:
        payment = pending_payments.pop(label)
        print(f"✅ Оплачено! Товар: {payment['item']}")
        # Здесь можно активировать привилегию на сервере
        # или отправить уведомление в Telegram
    
    return "OK", 200

def verify_signature(data):
    if not YOOMONEY_SECRET:
        return True
    params = [
        data.get('notification_type', ''),
        data.get('operation_id', ''),
        data.get('amount', ''),
        data.get('currency', ''),
        data.get('datetime', ''),
        data.get('sender', ''),
        data.get('codepro', ''),
        YOOMONEY_SECRET,
        data.get('label', '')
    ]
    check_string = '&'.join(params)
    sha1_hash = hashlib.sha1(check_string.encode()).hexdigest()
    return sha1_hash == data.get('sha1_hash', '')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
