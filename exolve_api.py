import requests
import logging
import time

logger = logging.getLogger("ExolveAPI")

def get_call_transcription(call_id: str, config) -> str | None:
    """Забирает транскрипцию из API Exolve и форматирует в диалог."""

    url = f"https://api.exolve.ru/voice/v1/calls/{call_id}/transcription"
    headers = {"Authorization": f"Bearer {config.EXOLVE_API_KEY}"}

    # Транскрипция сводится не мгновенно. Делаем поллинг (до 5 попыток)
    for attempt in range(5):
        try:
            logger.info(f"Запрос транскрипции звонка {call_id} (попытка {attempt + 1})...")
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code in (404, 422):
                logger.info("Транскрипция еще сводится, ждем 10 секунд...")
                time.sleep(10)
                continue

            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            if not messages:
                time.sleep(5)
                continue

            # Форматируем сырой JSON в читаемый диалог для LLM
            formatted_dialog = []
            for msg in messages:
                role = msg.get("role", "")
                text = msg.get("text", "").strip()

                if not text:
                    continue

                # Условно считаем OUTBOUND - Менеджер, INBOUND - Клиент
                speaker = "Менеджер" if role == "OUTBOUND" else "Клиент"
                formatted_dialog.append(f"{speaker}: {text}")

            final_text = "\n".join(formatted_dialog)
            logger.info(f"Транскрипция успешно собрана: {len(final_text)} символов.")
            return final_text

        except requests.RequestException as e:
            logger.error(f"Сбой при запросе к API Exolve: {e}")
            time.sleep(5)

    logger.error(f"Не удалось получить транскрипцию для {call_id} за отведенное время.")
    return None