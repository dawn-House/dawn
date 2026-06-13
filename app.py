from flask import Flask, request, jsonify

# ... твой существующий код бота и приложения ...

@app.route('/yoomoney', methods=['POST'])
def handle_yoomoney_notification():
    """
    Обрабатывает HTTP-уведомления от YooMoney.
    """
    data = request.form.to_dict() # Уведомления приходят в формате form-data
    print(f"Получено уведомление: {data}") # Отлично подходит для отладки

    # Здесь будет логика проверки подписи и активации покупки
    # label = data.get('label')
    # if verify_signature(data):
    #     activate_purchase(label)

    return "OK", 200
