from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

YOOMONEY_WALLET = "4100119350010213"
pending_payments = {}

@app.route('/')
def home():
    return 'Dawn House works!'

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/yoomoney', methods=['POST'])
def yoomoney_notification():
    data = request.form.to_dict()
    print(f"Уведомление: {data}")
    
    label = data.get('label')
    if data.get('status') == 'success' and label in pending_payments:
        payment = pending_payments.pop(label)
        print(f"✅ Оплачено! {payment['item']} для {payment.get('nick')}")
    
    return "OK", 200

@app.route('/api/create-payment', methods=['POST'])
def create_payment():
    data = request.get_json()
    label = str(uuid.uuid4())[:8]
    pending_payments[label] = data
    
    link = f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YOOMONEY_WALLET}&quickpay-form=donate&targets={data['item']}&sum={data['amount']}&label={label}"
    
    return jsonify({'link': link, 'label': label})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
