from flask import Flask, request, jsonify
import uuid
import socket
import struct

app = Flask(__name__)

# ============================================
# НАСТРОЙКИ
# ============================================
YOOMONEY_WALLET = "4100119350010213"

# RCON НАСТРОЙКИ ТВОЕГО СЕРВЕРА
RCON_HOST = "77.42.49.6"
RCON_PORT = 25923
RCON_PASSWORD = "rMIJOBLqFq"

pending_payments = {}

# ============================================
# RCON ФУНКЦИЯ (РАБОТАЕТ)
# ============================================
def rcon_command(command: str) -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((RCON_HOST, RCON_PORT))

        def send_packet(req_id, ptype, payload):
            data = payload.encode("utf-8") + b"\x00\x00"
            header = struct.pack("<iii", len(data) + 8, req_id, ptype)
            sock.sendall(header + data)

        def recv_packet():
            raw_len = b""
            while len(raw_len) < 4:
                chunk = sock.recv(4 - len(raw_len))
                if not chunk:
                    return None, None, ""
                raw_len += chunk
            length = struct.unpack("<i", raw_len)[0]
            raw = b""
            while len(raw) < length:
                chunk = sock.recv(length - len(raw))
                if not chunk:
                    return None, None, ""
                raw += chunk
            req_id, ptype = struct.unpack("<ii", raw[:8])
            payload = raw[8:-2].decode("utf-8", errors="replace")
            return req_id, ptype, payload

        send_packet(1, 3, RCON_PASSWORD)
        rid, _, _ = recv_packet()
        if rid == -1:
            sock.close()
            return "❌ Неверный пароль RCON"

        send_packet(2, 2, command)
        _, _, response = recv_packet()
        sock.close()
        return response.strip() if response else "✅ Команда выполнена"
    except Exception as e:
        return f"❌ Ошибка RCON: {e}"

# ============================================
# МАРШРУТЫ
# ============================================
@app.route('/')
def home():
    return 'Dawn House Payment System Works!'

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/yoomoney', methods=['POST'])
def yoomoney_notification():
    data = request.form.to_dict()
    print(f"📥 Уведомление: {data}")
    
    if data.get('status') == 'success':
        label = data.get('label')
        if label and label in pending_payments:
            payment = pending_payments.pop(label)
            nick = payment.get('nick')
            item = payment.get('item')
            
            print(f"💰 ОПЛАЧЕНО! {item} для {nick}")
            
            # ВЫДАЁМ ПРИВИЛЕГИЮ НА СЕРВЕРЕ
            if nick:
                result = rcon_command(f"lp user {nick} parent add {item}")
                print(f"📡 Результат: {result}")
                
                # ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ В TELEGRAM
                import requests
                TOKEN = "7945405277:AAEbywt7eFG41SVvx4rSIfQsug3MDE5KSn0"
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={
                        'chat_id': payment['user_id'],
                        'text': f"✅ Привилегия {item} выдана нику {nick}!",
                        'parse_mode': 'HTML'
                    }
                )
    
    return "OK", 200

@app.route('/api/create-payment', methods=['POST'])
def create_payment():
    data = request.get_json()
    label = str(uuid.uuid4())[:8]
    pending_payments[label] = data
    
    link = f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YOOMONEY_WALLET}&quickpay-form=donate&targets={data['item']}&sum={data['amount']}&label={label}"
    
    print(f"📝 Создан платёж: {data['item']} для {data.get('nick')} на {data['amount']} руб.")
    
    return jsonify({'link': link, 'label': label})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
