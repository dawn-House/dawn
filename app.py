from flask import Flask, request, jsonify
import hashlib
import uuid
import json
import os

app = Flask(__name__)

# Данные для YooMoney (замени на свои!)
YOOMONEY_WALLET = ""  # Номер кошелька, например "410011234567890"
YOOMONEY_SECRET = ""  # Секретное слово из настроек уведомлений

# Хранилище платежей (в реальном проекте используй базу данных)
pending_payments = {}

# Простая главная страница
@app.route('/')
def home():
    return '''
    <h1>🌅 Dawn House</h1>
    <p>Сервер работает! Для покупок используйте Telegram-бота.</p>
    <a href="/health">Проверка статуса</a>
    '''

# Проверка здоровья для Railway
@app.route('/health')
def health():
    return 'OK', 200

# Эндпоинт для уведомлений от YooMoney
@app.route('/yoomoney', methods=['POST'])
def yoomoney_notification():
    """Принимает уведомления от YooMoney об оплате"""
    data = request.form.to_dict()
    print(f"📥 Получено уведомление: {data}")
    
    # Проверяем подпись
    if not verify_signature(data):
        print("❌ Неверная подпись!")
        return "Invalid signature", 400
    
    label = data.get('label')
    status = data.get('status', '')
    
    if status == 'success' and label in pending_payments:
        payment = pending_payments.pop(label)
        print(f"✅ Платёж подтверждён! Товар: {payment['item']}, Пользователь: {payment['user_id']}")
        
        # Здесь можно:
        # 1. Сохранить в базу данных
        # 2. Отправить уведомление в Telegram бот
        # 3. Активировать привилегию на сервере
        
        save_payment(label, payment)
        
    return "OK", 200

def verify_signature(data):
    """Проверяет, что уведомление пришло от YooMoney"""
    if not YOOMONEY_SECRET:
        return True  # Если секрет не задан, пропускаем проверку
    
    # Формируем строку для проверки
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
    """Сохраняет информацию об успешном платеже"""
    filename = 'payments.json'
    payments = []
    
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            payments = json.load(f)
    
    payments.append({
        'label': label,
        'user_id': payment['user_id'],
        'item': payment['item'],
        'amount': payment['amount'],
        'status': 'paid'
    })
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(payments, f, ensure_ascii=False, indent=2)

# Функция для создания ссылки на оплату
def create_payment_link(amount, label, description):
    """Создаёт ссылку для оплаты через YooMoney"""
    if not YOOMONEY_WALLET:
        return None
    
    return f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YOOMONEY_WALLET}&quickpay-form=donate&targets={description}&sum={amount}&label={label}"

# API для бота (чтобы бот мог создавать ссылки на оплату)
@app.route('/api/create-payment', methods=['POST'])
def api_create_payment():
    """Создаёт платёж и возвращает ссылку для оплаты"""
    data = request.get_json()
    
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
    
    payment_link = create_payment_link(amount, label, f"Dawn House: {item}")
    
    return jsonify({
        'link': payment_link,
        'label': label
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
