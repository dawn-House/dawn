from flask import Flask, request, jsonify
import os
import hashlib
import uuid
import json
from datetime import datetime

app = Flask(__name__)

# ============================================
# КОНФИГУРАЦИЯ - ЗАМЕНИ НА СВОИ ДАННЫЕ!
# ============================================
YOOMONEY_WALLET = ""  # Вставь номер кошелька, например "410011234567890"
YOOMONEY_SECRET = ""  # Вставь секретное слово из настроек уведомлений

# Временное хранилище платежей
pending_payments = {}
PAYMENTS_FILE = "payments.json"

# ============================================
# ОСНОВНЫЕ МАРШРУТЫ
# ============================================

@app.route('/')
def home():
    return '''
    <h1>🌅 Dawn House</h1>
    <p>Сервер работает! Для покупок используйте Telegram-бота.</p>
    <p><a href="/health">Проверка статуса</a></p>
    '''

@app.route('/health')
def health():
    return 'OK', 200

# ============================================
# ОБРАБОТКА ПЛАТЕЖЕЙ
# ============================================

@app.route('/yoomoney', methods=['POST'])
def yoomoney_notification():
    """Принимает уведомления от YooMoney об оплате"""
    print(f"[{datetime.now()}] Получено уведомление")
    
    data = request.form.to_dict()
    print(f"Данные: {data}")
    
    # Проверяем подпись
    if YOOMONEY_SECRET and not verify_signature(data):
        print("❌ Неверная подпись!")
        return "Invalid signature", 400
    
    label = data.get('label')
    status = data.get('status')
    
    if status == 'success' and label and label in pending_payments:
        payment = pending_payments.pop(label)
        print(f"✅ ОПЛАТА ПОДТВЕРЖДЕНА!")
        print(f"   Товар: {payment.get('item')}")
        print(f"   Пользователь: {payment.get('user_id')}")
        print(f"   Сумма: {payment.get('amount')} руб.")
        
        # Сохраняем в историю
        save_payment(label, payment)
    
    return "OK", 200

def verify_signature(data):
    """Проверяет подпись уведомления от YooMoney"""
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

def save_payment(label, payment):
    """Сохраняет платёж в историю"""
    history = []
    if os.path.exists(PAYMENTS_FILE):
        with open(PAYMENTS_FILE, 'r') as f:
            history = json.load(f)
    
    history.append({
        'label': label,
        'user_id': payment['user_id'],
        'item': payment['item'],
        'amount': payment['amount'],
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    with open(PAYMENTS_FILE, 'w') as f:
        json.dump(history, f, indent=2)

# ============================================
# API ДЛЯ ТЕЛЕГРАМ БОТА
# ============================================

@app.route('/api/create-payment', methods=['POST'])
def create_payment():
    """Создаёт платёж и возвращает ссылку для оплаты"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data'}), 400
    
    user_id = data.get('user_id')
    item = data.get('item')
    amount = data.get('amount')
    
    if not all([user_id, item, amount]):
        return jsonify({'error': 'Missing fields'}), 400
    
    label = str(uuid.uuid4())[:8]
    
    pending_payments[label] = {
        'user_id': user_id,
        'item': item,
        'amount': amount
    }
    
    # Создаём ссылку на оплату
    if YOOMONEY_WALLET:
        link = f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YOOMONEY_WALLET}&quickpay-form=donate&targets={item}&sum={amount}&label={label}"
    else:
        link = f"https://yoomoney.ru/"
    
    return jsonify({
        'success': True,
        'link': link,
        'label': label
    })

# ============================================
# ЗАПУСК
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
