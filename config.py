import os

class Config:
    # Безопасность: токен для авторизации нашего вебхука и токен для API МТС Exolve
    WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'bant-super-secret-token')
    EXOLVE_API_KEY = os.environ.get('EXOLVE_API_KEY', 'your_exolve_api_key')

    # База данных
    DB_NAME = 'bant_analytics.db'

    # Yandex Cloud (IAM токен или API-ключ сервисного аккаунта)
    YANDEX_API_KEY = os.environ.get('YANDEX_API_KEY', 'your_yandex_api_key')
    YANDEX_FOLDER_ID = os.environ.get('YANDEX_FOLDER_ID', 'your_folder_id')

    YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    MODEL_URI = f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite/latest"

    # Bitrix24 CRM (URL входящего вебхука с правами на CRM)
    BITRIX24_WEBHOOK_URL = os.environ.get('BITRIX24_WEBHOOK_URL', 'https://domain.bitrix24.ru/rest/1/token/')