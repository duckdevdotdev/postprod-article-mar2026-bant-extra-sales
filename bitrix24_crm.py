import requests
import logging
import re

logger = logging.getLogger("Bitrix24")

def normalize_phone(phone: str) -> str:
    """Очищает телефон от скобок/пробелов для строгого поиска в CRM."""
    if not phone: return ""
    digits = re.sub(r'\D', '', phone)
    # Приводим 8 к 7 для стандарта
    if digits.startswith('8') and len(digits) == 11:
        digits = '7' + digits[1:]
    return digits

def update_crm_deal(client_phone: str, bant_data: dict, config) -> bool:
    if not client_phone or not bant_data:
        return False

    clean_phone = normalize_phone(client_phone)
    url = f"{config.BITRIX24_WEBHOOK_URL}crm.deal.list.json"

    # 1. Ищем открытую сделку по очищенному номеру
    try:
        search_resp = requests.post(url, json={"filter": {"=CONTACT.PHONE": clean_phone}}, timeout=10)
        search_resp.raise_for_status()
        deals = search_resp.json().get("result", [])
        if not deals:
            logger.warning(f"Сделка для номера {clean_phone} не найдена.")
            return False

        deal_id = deals[0]["ID"]
    except requests.RequestException as e:
        logger.error(f"Ошибка поиска сделки: {e}")
        return False

    update_url = f"{config.BITRIX24_WEBHOOK_URL}crm.deal.update.json"

    # 2. Маппим BANT в кастомные поля (UF_CRM_...)
    payload = {
        "ID": deal_id,
        "FIELDS": {
            "UF_CRM_BANT_NEED": bant_data.get("need_description") or "",
            "UF_CRM_BANT_BUDGET": bant_data.get("budget_estimated") or "",
            "UF_CRM_BANT_DM": bant_data.get("decision_maker") or "unknown",
            "UF_CRM_BANT_TIMELINE": bant_data.get("timeline") or "",
            "UF_CRM_INTENT": bant_data.get("intent_score", "low").upper(),
            "UF_CRM_COMPETITORS": ", ".join(bant_data.get("competitors", [])),
            "UF_CRM_OBJECTIONS": ", ".join(bant_data.get("objections", []))
        }
    }

    try:
        response = requests.post(update_url, json=payload, timeout=10)
        response.raise_for_status()
        if "error" in response.json():
            logger.error(f"Ошибка API Битрикса: {response.json()['error_description']}")
            return False
        return True
    except requests.RequestException as e:
        logger.error(f"Сбой сети при отправке в CRM: {e}")
        return False