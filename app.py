from flask import Flask, request, jsonify
import uuid
import os

app = Flask(__name__)

# ============================================
# НАСТРОЙКИ - ЗАМЕНИ НА СВОИ ДАННЫЕ
# ============================================
YOOMONEY_WALLET = "4100119350010213"  # Твой номер кошелька, например "410011234567890"

# ============================================
# ХРАНИЛИЩЕ ОЖИДАЮЩИХ ПЛАТЕЖЕЙ
# ============================================
pending_payments = {}

# ============================================
# ОСНОВНЫЕ МАРШРУТЫ
# ============================================
@app.route('/')
def home():
    return 'Dawn House Payment System works!'

@app.route('/health')
def health():
    return 'OK', 200

# ============================================
# ОБРАБОТКА УВЕДОМЛЕНИЙ ОТ YOOMONEY
# ============================================
@app.route('/yoomoney', methods=['POST'])
def yoomoney_notification():
    """Принимает уведомления от YooMoney об оплате"""
    data = request.form.to_dict()
    print(f"Получено уведомление: {data}")
    
    status = data.get('status')
    label = data.get('label')
    amount = data.get('amount')
    
    if status == 'success' and label and label in pending_payments:
        payment = pending_payments.pop(label)
        print(f"✅ ОПЛАЧЕНО! Товар: {payment['item']}, Сумма: {amount} руб.")
        # Здесь можно вызвать RCON команду для выдачи привилегии
    
    return "OK", 200

# ============================================
# API ДЛЯ БОТА (СОЗДАНИЕ ПЛАТЕЖА)
# ============================================
@app.route('/api/create-payment', methods=['POST'])
def create_payment():
    """Создаёт платёж и возвращает ссылку для оплаты (вызывается ботом)"""
    data = request.get_json()
    
    user_id = data.get('user_id')
    item = data.get('item')
    amount = data.get('amount')
    nick = data.get('nick', '')
    
    if not all([user_id, item, amount]):
        return jsonify({'error': 'Missing fields'}), 400
    
    label = str(uuid.uuid4())[:8]
    
    pending_payments[label] = {
        'user_id': user_id,
        'item': item,
        'amount': amount,
        'nick': nick
    }
    
    # Создаём ссылку на оплату
    if YOOMONEY_WALLET:
        link = f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YOOMONEY_WALLET}&quickpay-form=donate&targets={item}&sum={amount}&label={label}"
    else:
        link = "https://yoomoney.ru/"
        print("⚠️ YOOMONEY_WALLET не настроен!")
    
    print(f"Создан платёж: {label} - {item} - {amount} руб.")
    
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
