import logging
import threading
import json
from flask import Flask, request, jsonify, render_template

from config import Config
from database import init_db, create_call_record, update_call_state, get_db_connection
from exolve_api import get_call_transcription
from yandex_llm import extract_bant_data
from bitrix24_crm import update_crm_deal

# Базовая настройка логирования для вывода в консоль
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("App")

app = Flask(__name__)
app.config.from_object(Config)

with app.app_context():
    init_db()

def process_call_async(call_id, client_phone, audio_url):
    logger.info(f"[{call_id}] Старт фонового пайплайна")

    # 1. Получение транскрипции из Exolve
    transcript = get_call_transcription(call_id, app.config)
    if not transcript:
        update_call_state(call_id, 'ERROR')
        return
    update_call_state(call_id, 'STT_OK', transcript=transcript)

    # 2. Нейроанализ
    bant_result = extract_bant_data(transcript, app.config)
    if not bant_result:
        update_call_state(call_id, 'ERROR')
        return
    bant_json_str = json.dumps(bant_result, ensure_ascii=False)
    update_call_state(call_id, 'LLM_OK', bant_result=bant_json_str)

    # 3. Выгрузка в CRM
    if update_crm_deal(client_phone, bant_result, app.config):
        update_call_state(call_id, 'CRM_OK')
    else:
        update_call_state(call_id, 'ERROR')

@app.route('/webhook/exolve', methods=['POST'])
def handle_exolve_webhook():
    if request.args.get('token') != app.config['WEBHOOK_SECRET']:
        return "Forbidden", 403

    data = request.json or {}

    # Строгий парсинг по документации Voice API МТС Exolve
    if data.get('event_type') != 'call.completed':
        # Игнорируем промежуточные события (started, answered и т.д.)
        return jsonify({"status": "ignored"}), 200

    payload = data.get('payload', {})
    call_id = payload.get('call_id')
    audio_url = payload.get('recording_url')

    # Определяем номер клиента в зависимости от направления звонка
    direction = payload.get('direction')
    client_phone = payload.get('from') if direction == 'inbound' else payload.get('to')

    if not call_id or not audio_url or not client_phone:
        return "Bad Request: Missing payload data", 400

    # Создаем запись. Если дубль - игнорируем
    if create_call_record(call_id, client_phone, audio_url):
        # Асинхронный запуск
        thread = threading.Thread(target=process_call_async, args=(call_id, client_phone, audio_url))
        thread.start()
        # Мгновенно отпускаем сервер МТС Exolve
        return jsonify({"status": "accepted"}), 202

    return jsonify({"status": "already_processed"}), 200

@app.route('/', methods=['GET'])
def dashboard():
    conn = get_db_connection()
    calls = conn.execute('SELECT * FROM calls ORDER BY created_at DESC LIMIT 20').fetchall()
    conn.close()

    parsed_calls = []
    for c in calls:
        call_dict = dict(c)
        call_dict['bant_data'] = json.loads(c['bant_result']) if c['bant_result'] else None
        parsed_calls.append(call_dict)

    return render_template('index.html', calls=parsed_calls)

if __name__ == '__main__':
    app.run(debug=True, port=5000)