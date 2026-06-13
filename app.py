from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

# Вставь свои данные YooMoney сюда
YOOMONEY_WALLET = "4100119350010213"  # Номер кошелька, например "410011234567890"

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
    data = request.form.to_dict()
    print(f"Данные: {data}")
    
    # Проверяем статус платежа
    if data.get('status') == 'success':
        label = data.get('label')
        if label and label in pending_payments:
            print(f"✅ ОПЛАТА ПОДТВЕРЖДЕНА!")
            print(f"   Пользователь: {pending_payments[label].get('user_id')}")
            print(f"   Товар: {pending_payments[label].get('item')}")
            print(f"   Сумма: {pending_payments[label].get('amount')} руб.")
    
    return "OK", 200

@app.route('/api/create-payment', methods=['POST'])
def create_payment():
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
    
    # Создаём реальную ссылку на оплату
    if YOOMONEY_WALLET:
        link = f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YOOMONEY_WALLET}&quickpay-form=donate&targets={item}&sum={amount}&label={label}"
    else:
        link = f"https://yoomoney.ru/"
    
    return jsonify({
        'success': True,
        'link': link,
        'label': label
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
