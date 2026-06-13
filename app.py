# ============================================================
#   DAWN HOUSE — Railway сервер (app.py)
#   Зависимости: Flask
# ============================================================
 
from flask import Flask, request, jsonify
import uuid
import socket
import struct
import hashlib
import json
import os
 
app = Flask(__name__)
 
# ─────────────────────────────────────────────
#  КОНФИГУРАЦИЯ
# ─────────────────────────────────────────────
YOOMONEY_WALLET  = "4100119350010213"
YOOMONEY_SECRET  = "tUJj4wjTMYdDexqAn5WG61N4"
 
RCON_HOST        = "77.42.49.6"
RCON_PORT        = 25923
RCON_PASSWORD    = "rMIJOBLqFq"
 
# Telegram (для уведомлений об автооплате)
BOT_TOKEN        = "7945405277:AAEbywt7eFG41SVvx4rSIfQsug3MDE5KSn0"
ADMIN_IDS        = [7186618502]
 
# Файл хранения платежей (Railway сбрасывает память при рестарте)
PAYMENTS_FILE    = "pending_payments.json"
 
# ─────────────────────────────────────────────
#  МАППИНГ: название товара → команды RCON
# ─────────────────────────────────────────────
 
# Привилегии: отображение русского названия → группа LuckPerms
PRIVILEGE_MAP = {
    "Привилегия Рассвет":  "dawn",
    "Привилегия Фантом":   "phantom",
    "Привилегия Варден":   "warden",
    "Привилегия Титан":    "titan",
    "Привилегия Эклипс":   "eclipse",
    "Привилегия Мифик":    "mythic",
    "Привилегия Лорд":     "overlord",
    "Привилегия Dawn":     "dawnmaster",
}
 
 
def get_rcon_commands(item: str, nick: str, extra: dict) -> list:
    """
    Возвращает список RCON-команд для выдачи товара.
    extra — доп. данные из платежа (количество и т.д.)
    """
    commands = []
 
    # ── Привилегии ──────────────────────────────
    if item in PRIVILEGE_MAP:
        group = PRIVILEGE_MAP[item]
        commands.append(f"lp user {nick} parent set {group}")
        commands.append(f"whitelist add {nick}")
        return commands
 
    # ── Фениксы ─────────────────────────────────
    if "фениксов" in item or "феникс" in item.lower():
        amount = extra.get("amount_items", 0)
        if amount:
            commands.append(f"p give {nick} {amount}")
        return commands
 
    # ── Монеты ──────────────────────────────────
    if "монет" in item.lower():
        amount = extra.get("amount_items", 0)
        if amount:
            commands.append(f"eco give {nick} {amount}")
        return commands
 
    # ── Кейсы с привилегиями ────────────────────
    if "Кейс привилегий" in item:
        count = extra.get("amount_items", 1)
        commands.append(f"hc givekey {nick} donate {count}")
        return commands
 
    # ── Кейсы с монетами ────────────────────────
    if "Кейс монет" in item:
        count = extra.get("amount_items", 1)
        commands.append(f"hc givekey {nick} money {count}")
        return commands
 
    # ── Кейсы с фениксами ───────────────────────
    if "Кейс фениксов" in item:
        count = extra.get("amount_items", 1)
        commands.append(f"hc givekey {nick} fenix {count}")
        return commands
 
    return commands
 
 
# ─────────────────────────────────────────────
#  RCON
# ─────────────────────────────────────────────
 
def rcon_command(command: str) -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((RCON_HOST, RCON_PORT))
 
        def send_packet(req_id, ptype, payload):
            data   = payload.encode("utf-8") + b"\x00\x00"
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
            raw    = b""
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
        return response.strip() if response else "✅ Выполнено"
 
    except socket.timeout:
        return "❌ Таймаут RCON"
    except ConnectionRefusedError:
        return "❌ RCON порт закрыт"
    except Exception as e:
        return f"❌ Ошибка RCON: {e}"
 
 
def execute_purchase(nick: str, item: str, extra: dict) -> list:
    """Выполнить все RCON-команды для покупки, вернуть список результатов."""
    commands = get_rcon_commands(item, nick, extra)
    results  = []
    for cmd in commands:
        res = rcon_command(cmd)
        results.append(f"/{cmd} → {res}")
        print(f"[RCON] {cmd} → {res}")
    return results
 
 
# ─────────────────────────────────────────────
#  TELEGRAM УВЕДОМЛЕНИЕ
# ─────────────────────────────────────────────
 
def tg_notify(chat_id: int, text: str):
    """Отправить сообщение в Telegram (без зависимостей, через requests)."""
    try:
        import urllib.request
        import urllib.parse
        url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id":    chat_id,
            "text":       text,
            "parse_mode": "HTML",
        }).encode()
        urllib.request.urlopen(url, data, timeout=5)
    except Exception as e:
        print(f"[TG] Ошибка отправки: {e}")
 
 
# ─────────────────────────────────────────────
#  ХРАНИЛИЩЕ ПЛАТЕЖЕЙ (JSON-файл)
#  Railway сбрасывает память при рестарте,
#  поэтому сохраняем на диск.
# ─────────────────────────────────────────────
 
def load_payments() -> dict:
    if os.path.exists(PAYMENTS_FILE):
        try:
            with open(PAYMENTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}
 
def save_payments(payments: dict):
    try:
        with open(PAYMENTS_FILE, "w") as f:
            json.dump(payments, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[SAVE] Ошибка: {e}")
 
 
# ─────────────────────────────────────────────
#  YOOMONEY — проверка подписи
# ─────────────────────────────────────────────
 
def verify_yoomoney(data: dict) -> bool:
    if not YOOMONEY_SECRET:
        return True   # если секрет не задан — пропускаем (для отладки)
    keys = ["notification_type", "operation_id", "amount", "currency",
            "datetime", "sender", "codepro", YOOMONEY_SECRET, "label"]
    check_str = "&".join(str(data.get(k, "")) for k in keys)
    expected  = hashlib.sha1(check_str.encode()).hexdigest()
    received  = data.get("sha1_hash", "")
    ok        = expected == received
    if not ok:
        print(f"[YM] Подпись не совпала. Ожидалось: {expected}, получено: {received}")
    return ok
 
 
# ─────────────────────────────────────────────
#  МАРШРУТЫ
# ─────────────────────────────────────────────
 
@app.route("/")
def home():
    return "Dawn House Payment System — OK ✅"
 
@app.route("/health")
def health():
    return "OK", 200
 
 
@app.route("/api/create-payment", methods=["POST"])
def create_payment():
    """
    Бот вызывает этот эндпоинт для создания платежа.
    Тело JSON: { nick, item, amount, user_id, amount_items? }
    """
    data     = request.get_json(force=True, silent=True) or {}
    label    = str(uuid.uuid4())[:16]
    payments = load_payments()
    payments[label] = {
        "nick":         data.get("nick", ""),
        "item":         data.get("item", ""),
        "amount":       data.get("amount", 0),
        "user_id":      data.get("user_id", 0),
        "amount_items": data.get("amount_items", 0),
    }
    save_payments(payments)
 
    comment = f"Dawn House: {data.get('item')} для {data.get('nick')}"
    link    = (
        f"https://yoomoney.ru/quickpay/confirm.xml"
        f"?receiver={YOOMONEY_WALLET}"
        f"&quickpay-form=donate"
        f"&targets={comment}"
        f"&sum={data.get('amount', 0)}"
        f"&label={label}"
        f"&need-fio=false&need-email=false&need-phone=false"
    )
 
    print(f"[PAY] Создан платёж {label}: {data.get('item')} для {data.get('nick')} — {data.get('amount')} руб.")
    return jsonify({"link": link, "label": label})
 
 
@app.route("/api/confirm-payment", methods=["POST"])
def confirm_payment():
    """
    Бот вызывает этот эндпоинт при ручном подтверждении оплаты администратором.
    Тело JSON: { label }
    """
    data     = request.get_json(force=True, silent=True) or {}
    label    = data.get("label", "")
    payments = load_payments()
 
    if label not in payments:
        return jsonify({"ok": False, "error": "Платёж не найден"}), 404
 
    payment  = payments.pop(label)
    save_payments(payments)
 
    nick  = payment.get("nick", "")
    item  = payment.get("item", "")
    extra = {"amount_items": payment.get("amount_items", 0)}
 
    results = execute_purchase(nick, item, extra)
 
    # Уведомить игрока в Telegram
    uid = payment.get("user_id")
    if uid:
        tg_notify(
            uid,
            f"✅ <b>Оплата подтверждена!</b>\n\n"
            f"📦 Товар: <b>{item}</b>\n"
            f"🎮 Ник: <b>{nick}</b>\n\n"
            "Зайди на сервер — всё уже активировано! 🎮"
        )
 
    print(f"[CONFIRM] {label} подтверждён вручную. Результаты: {results}")
    return jsonify({"ok": True, "results": results})
 
 
@app.route("/yoomoney", methods=["POST"])
def yoomoney_notification():
    """
    YooMoney автоматически присылает POST сюда после оплаты.
    Настрой URL в кабинете YooMoney:
    https://ТВО_ДОМЕН.railway.app/yoomoney
    """
    data  = request.form.to_dict()
    print(f"[YM] Входящее уведомление: {data}")
 
    # Проверяем подпись
    if not verify_yoomoney(data):
        print("[YM] ❌ Подпись не прошла проверку")
        return "Bad signature", 400
 
    label    = data.get("label", "")
    status   = data.get("notification_type", "")
    amount   = data.get("amount", "?")
    payments = load_payments()
 
    if label not in payments:
        print(f"[YM] ⚠️ Label {label} не найден в pending_payments")
        return "OK", 200   # всё равно возвращаем 200 чтобы YooMoney не повторял
 
    payment  = payments.pop(label)
    save_payments(payments)
 
    nick  = payment.get("nick", "")
    item  = payment.get("item", "")
    extra = {"amount_items": payment.get("amount_items", 0)}
 
    print(f"[YM] ✅ Оплата {label}: {item} для {nick} — {amount} руб.")
 
    # Выполняем команды на сервере
    results = execute_purchase(nick, item, extra)
 
    # Уведомляем игрока
    uid = payment.get("user_id")
    if uid:
        tg_notify(
            int(uid),
            f"✅ <b>Оплата получена автоматически!</b>\n\n"
            f"📦 Товар: <b>{item}</b>\n"
            f"🎮 Ник: <b>{nick}</b>\n"
            f"💰 Сумма: <b>{amount} ₽</b>\n\n"
            "Всё активировано! Заходи на сервер 🎮"
        )
 
    # Уведомляем администраторов
    for admin in ADMIN_IDS:
        tg_notify(
            admin,
            f"💰 <b>АВТООПЛАТА ПОЛУЧЕНА</b>\n\n"
            f"🎮 Ник: <b>{nick}</b>\n"
            f"📦 Товар: <b>{item}</b>\n"
            f"💵 Сумма: <b>{amount} ₽</b>\n\n"
            f"🖥 RCON: {chr(10).join(results)}"
        )
 
    return "OK", 200
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
