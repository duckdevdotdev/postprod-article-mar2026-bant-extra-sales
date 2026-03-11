import requests

# Замените на ваш URL из ngrok или localhost (если тестируете без ngrok)
NGROK_URL = "http://127.0.0.1:5000/webhook/exolve?token=bant-super-secret-token"

mock_payload = {
    "event_type": "call.completed",
    "payload": {
        "call_id": "test_local_001",
        "direction": "inbound",
        "from": "+79991234567",
        "to": "+74950000000",
        "recording_url": "https://api.exolve.ru/v1/recordings/test.mp3"
    }
}

print(f"Отправляем тестовый звонок на {NGROK_URL} ...")
try:
    response = requests.post(NGROK_URL, json=mock_payload)
    print("Статус:", response.status_code) # Ожидаем 202
    print("Ответ:", response.text)
except requests.exceptions.ConnectionError:
    print("Ошибка соединения. Убедитесь, что сервер Flask (app.py) запущен.")