import requests
import json
import logging
import time

logger = logging.getLogger("YandexLLM")

SYSTEM_PROMPT = """Ты — суровый AI-ассистент отдела B2B продаж. Твоя задача — извлечь BANT+ из транскрипта.

ПРАВИЛА (СТРОГО):
1. Не придумывай данные! Если инфы нет — пиши null, "unknown" или [].
2. need: если need=false, то need_description=null.
3. budget_estimated: строго формат "min-max" только цифрами (например "100000-500000", "до 50000" -> "0-50000") или "unknown".
4. decision_maker: "yes", "no", "unknown".
5. timeline: "ASAP", "30d", "90d", "unknown".
6. intent_score: "high" ставится ТОЛЬКО если совпадает минимум 2 из 3 критериев (есть боль, назван бюджет, понятны сроки). Иначе "med" (просит КП/думает) или "low" (нет интереса/отказ).
7. competitors и objections: заполняй ТОЛЬКО если клиент явно их назвал, иначе возвращай пустые массивы [].

Верни СТРОГО валидный JSON без markdown-разметки по этому шаблону:
{
 "need": true,
 "need_description": "Описание боли клиента (до 150 симв.)",
 "budget_estimated": "150000-200000",
 "decision_maker": "unknown",
 "timeline": "30d",
 "intent_score": "med",
 "competitors": ["AmoCRM", "Salesforce"],
 "objections": ["дорого", "нет времени"]
}"""

def extract_bant_data(transcript: str, config) -> dict | None:
    if not transcript:
        return None

    # Защита лимитов контекста: обрезаем транскрипт до безопасных ~15000 символов
    safe_transcript = transcript[:15000]

    headers = {
        "Authorization": f"Api-Key {config.YANDEX_API_KEY}",
        "x-folder-id": config.YANDEX_FOLDER_ID,
        "Content-Type": "application/json"
    }

    payload = {
        "modelUri": config.MODEL_URI,
        "completionOptions": {
            "stream": False,
            "temperature": 0.1,  # Исключаем креативность и галлюцинации
            "maxTokens": "1500"
        },
        "messages": [
            {"role": "system", "text": SYSTEM_PROMPT},
            {"role": "user", "text": f"Транскрипция:\n{safe_transcript}"}
        ]
    }

    for attempt in range(3):
        try:
            response = requests.post(config.YANDEX_GPT_URL, headers=headers, json=payload, timeout=20)
            if response.status_code == 429:
                time.sleep(2 ** attempt)
                continue

            response.raise_for_status()
            raw_text = response.json()['result']['alternatives'][0]['message']['text']

            # Очистка от маркдауна (если модель вернет ```json ... ```)
            clean_text = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(clean_text)

        except (json.JSONDecodeError, requests.RequestException) as e:
            logger.error(f"Ошибка LLM (попытка {attempt + 1}): {e}")
            if attempt == 2:
                return None
    return None