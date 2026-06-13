from flask import Flask, request, jsonify
import os
import hashlib
import uuid
import json
from datetime import datetime

app = Flask(__name__)

# ============================================
# КОНФИГУРАЦИЯ (ЗАМЕНИ НА СВОИ ДАННЫЕ)
# ============================================
YOOMONEY_WALLET = "4100119350010213"  # Вставь номер кошелька, например "410011234567890"
YOOMONEY_SECRET = "tUJj4wjTMYdDexqAn5WG61N4"  # Вставь секретное слово из настроек уведомлений

# Временное хранилище платежей (для теста)
pending_payments = {}

# Файл для сохранения истории платежей
PAYMENTS_FILE = "payments.json"

# ============================================
# ОСНОВНЫЕ МАРШРУТЫ
# ============================================

@app.route('/')
def home():
    """Главная страница"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dawn House</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #0a0a2a; color: white; }
            h1 { color: #ffaa00; }
            .status { color: #00ff00; margin-top: 20px; }
            a { color: #ffaa00; }
        </style>
    </head>
    <body>
        <h1>🌅 Dawn House</h1>
        <p>Добро пожаловать на сайт!</p>
        <p class="status">✅ Сервер работает</p>
        <p>Для покупок используйте Telegram-бота</p>
        <hr>
        <small><a href="/health">Проверка статуса</a></small>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    """Проверка здоровья для Railway"""
    return 'OK', 200

# ============================================
# ОБРАБОТКА ПЛАТЕЖЕЙ YOOMONEY
# ============================================

@app.route('/yoomoney', methods=['POST'])
def yoomoney_notification():
    """
    Принимает уведомления от YooMoney об оплате
    """
    print("=" * 50)
    print(f"[{datetime.now()}] Получено уведомление от YooMoney")
    
    data = request.form.to_dict()
    print(f"Данные: {data}")
    
    # Проверяем подпись (если задан секрет)
    if YOOMONEY_SECRET and not verify_signature(data):
        print("❌ Ошибка: неверная подпись!")
        return "Invalid signature", 400
    
    label = data.get('label')
    status = data.get('status')
    amount = data.get('amount')
    
    print(f"Label: {label}, Status: {status}, Amount: {amount}")
    
    # Если оплата успешна
    if status == 'success' and label:
        if label in pending_payments:
            payment = pending_payments.pop(label)
            print(f"✅ ПЛАТЁЖ ПОДТВЕРЖДЁН!")
            print(f"   Товар: {payment.get('item')}")
            print(f"   Пользователь: {payment.get('user_id')}")
            print(f"   Сумма: {payment.get('amount')} руб.")
            
            # Сохраняем в историю
            save_payment_to_history(label, payment)
        else:
            print(f"⚠️ Платёж с label {label} не найден в pending_payments")
    
    return "OK", 200

def verify_signature(data):
    """
    Проверяет, что уведомление пришло от YooMoney
    """
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
    expected_hash = data.get('sha1_hash', '')
    
    return sha1_hash == expected_hash

def save_payment_to_history(label, payment):
    """
    Сохраняет информацию об успешном платеже в JSON файл
    """
    history = []
    if os.path.exists(PAYMENTS_FILE):
        try:
            with open(PAYMENTS_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
    
    history.append({
        'label': label,
        'user_id': payment.get('user_id'),
        'item': payment.get('item'),
        'amount': payment.get('amount'),
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'paid'
    })
    
    with open(PAYMENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print(f"💰 Платёж сохранён в историю. Всего платежей: {len(history)}")

# ============================================
# API ДЛЯ БОТА
# ============================================

@app.route('/api/create-payment', methods=['POST'])
def api_create_payment():
    """
    Создаёт платёж и возвращает ссылку для оплаты
    Используется Telegram-ботом
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data'}), 400
        
        user_id = data.get('user_id')
        item = data.get('item')
        amount = data.get('amount')
        description = data.get('description', f"Покупка {item}")
        
        if not all([user_id, item, amount]):
            return jsonify({'error': 'Missing required fields: user_id, item, amount'}), 400
        
        # Генерируем уникальный label для платежа
        label = str(uuid.uuid4())[:8]
        
        # Сохраняем информацию о платеже
        pending_payments[label] = {
            'user_id': user_id,
            'item': item,
            'amount': amount,
            'time': datetime.now().isoformat()
        }
        
        # Создаём ссылку на оплату
        payment_link = create_payment_link(amount, label, description)
        
        print(f"📝 Создан платёж: label={label}, user={user_id}, item={item}, amount={amount}")
        
        return jsonify({
            'success': True,
            'link': payment_link,
            'label': label
        })
        
    except Exception as e:
        print(f"❌ Ошибка в api_create_payment: {e}")
        return jsonify({'error': str(e)}), 500

def create_payment_link(amount, label, description):
    """
    Создаёт ссылку для оплаты через YooMoney
    """
    if not YOOMONEY_WALLET:
        # Если кошелёк не настроен, возвращаем тестовую ссылку
        print("⚠️ YOOMONEY_WALLET не настроен!")
        return f"https://yoomoney.ru/quickpay/confirm.xml?receiver=&quickpay-form=donate&targets={description}&sum={amount}&label={label}"
    
    return f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YOOMONEY_WALLET}&quickpay-form=donate&targets={description}&sum={amount}&label={label}"

# ============================================
# ДОПОЛНИТЕЛЬНЫЕ МАРШРУТЫ ДЛЯ ОТЛАДКИ
# ============================================

@app.route('/api/pending-payments', methods=['GET'])
def get_pending_payments():
    """Возвращает список ожидающих платежей (только для отладки)"""
    return jsonify(pending_payments)

@app.route('/api/payments-history', methods=['GET'])
def get_payments_history():
    """Возвращает историю платежей (только для отладки)"""
    history = []
    if os.path.exists(PAYMENTS_FILE):
        try:
            with open(PAYMENTS_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            pass
    return jsonify(history)

# ============================================
# ЗАПУСК
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Запуск Dawn House на порту {port}")
    print(f"📝 Главная страница: http://0.0.0.0:{port}/")
    print(f"🔍 Health check: http://0.0.0.0:{port}/health")
    app.run(host='0.0.0.0', port=port)
