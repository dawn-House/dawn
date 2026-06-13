from flask import Flask, request, jsonify
import uuid
import socket
import struct

app = Flask(__name__)

# ============================================
# НАСТРОЙКИ
# ============================================
YOOMONEY_WALLET = "4100119350010213"  # Твой номер кошелька

# RCON НАСТРОЙКИ ДЛЯ ВЫДАЧИ ПРИВИЛЕГИЙ
RCON_HOST = "77.42.49.6"
RCON_PORT = 25923
RCON_PASSWORD = "rMIJOBLqFq"

# Временное хранилище платежей
pending_payments = {}

# ============================================
# ФУНКЦИЯ RCON ДЛЯ ВЫДАЧИ ПРИВИЛЕГИИ
# ============================================
def rcon_command(command: str) -> str:
    """Выполнить команду через RCON на сервере Minecraft"""
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

        # Авторизация
        send_packet(1, 3, RCON_PASSWORD)
        rid, _, _ = recv_packet()
        if rid == -1:
            sock.close()
            return "❌ Неверный пароль RCON"

        # Отправка команды
        send_packet(2, 2, command)
        _, _, response = recv_packet()
        sock.close()
        return response.strip() if response else "✅ Команда выполнена"

    except socket.timeout:
        return "❌ Таймаут — сервер не ответил"
    except ConnectionRefusedError:
        return "❌ RCON порт закрыт"
    except Exception as e:
        return f"❌ Ошибка RCON: {e}"

def give_privilege(nick: str, privilege_name: str) -> str:
    """Выдаёт привилегию игроку на сервере"""
    # Команда для LuckPerms (замени на свою систему прав)
    command = f"lp user {nick} parent add {privilege_name}"
    return rcon_command(command)

# ============================================
# ОСНОВНЫЕ МАРШРУТЫ
# ============================================
@app.route('/')
def home():
    return 'Dawn House works!'

@app.route('/health')
def health():
    return 'OK'

# ============================================
# ОБРАБОТКА УВЕДОМЛЕНИЙ ОТ YOOMONEY
# ============================================
@app.route('/yoomoney', methods=['POST'])
def yoomoney_notification():
    data = request.form.to_dict()
    print(f"📥 Получено уведомление: {data}")
    
    status = data.get('status')
    label = data.get('label')
    amount = data.get('amount')
    
    if status == 'success' and label and label in pending_payments:
        payment = pending_payments.pop(label)
        
        print(f"💰 ПЛАТЁЖ ПОДТВЕРЖДЁН!")
        print(f"   Товар: {payment['item']}")
        print(f"   Сумма: {amount} руб.")
        print(f"   Пользователь ID: {payment['user_id']}")
        print(f"   Minecraft ник: {payment.get('nick', 'не указан')}")
        
        # ВЫДАЁМ ПРИВИЛЕГИЮ НА СЕРВЕРЕ
        if payment.get('nick'):
            result = give_privilege(payment['nick'], payment['item'])
            print(f"📡 Результат выдачи привилегии: {result}")
        else:
            print("⚠️ Ник не указан — привилегия не выдана")
    
    return "OK", 200

# ============================================
# API ДЛЯ БОТА
# ============================================
@app.route('/api/create-payment', methods=['POST'])
def create_payment():
    data = request.get_json()
    
    user_id = data.get('user_id')
    item = data.get('item')
    amount = data.get('amount')
    nick = data.get('nick', '')
    
    if not all([user_id, item, amount]):
        return jsonify({'error': 'Missing fields'}), 400
    
    label = str(uuid.uuid4())[:8]
    
    # Сохраняем информацию о платеже
    pending_payments[label] = {
        'user_id': user_id,
        'item': item,
        'amount': amount,
        'nick': nick
    }
    
    # РЕАЛЬНАЯ ССЫЛКА НА ОПЛАТУ
    if YOOMONEY_WALLET:
        link = f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YOOMONEY_WALLET}&quickpay-form=donate&targets={item}&sum={amount}&label={label}&successURL=https://t.me/dawnhouse_bot"
    else:
        link = "https://yoomoney.ru/"
        print("⚠️ YOOMONEY_WALLET не настроен!")
    
    print(f"📝 Создан платёж: label={label}, user={user_id}, item={item}, amount={amount}, nick={nick}")
    
    return jsonify({
        'success': True,
        'link': link,
        'label': label
    })

# ============================================
# ЗАПУСК
# ============================================
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Запуск на порту {port}")
    app.run(host='0.0.0.0', port=port)
