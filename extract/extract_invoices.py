import os
import json
import requests
from datetime import datetime, timedelta
from infra.config import config
from infra.authenticator import authenticate_user
from infra.logger import get_logger

logger = get_logger(__name__)

FMT = "%d/%m/%Y"


def _fmt(dt: datetime) -> str:
    return dt.strftime(FMT)


def get_invoice_statuses(user_token) -> list:
    url = f"{config.API_BASE_URL}/listar/situacao-boleto/todos"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return [s["codigo_situacaoboleto"] for s in response.json()]


def _fetch_by_status(status_code, user_token, date_filters: dict) -> list:
    url = f"{config.API_BASE_URL}/listar/boleto"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    payload = {
        "codigo_situacao": int(status_code),
        "quantidade_por_pagina": 1000,
        "inicio_paginacao": 0,
        **date_filters,
    }

    all_boletos = []
    total_boletos = None

    while True:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            boletos = data
            if total_boletos is None:
                total_boletos = len(data)
        else:
            if total_boletos is None:
                total_boletos = data.get("total_boletos", 0)
            boletos = data.get("boletos", [])

        if not boletos:
            break

        for boleto in boletos:
            boleto["codigo_situacao"] = status_code

        all_boletos.extend(boletos)

        logger.info(f"Status {status_code} | Page {payload['inicio_paginacao']}: {len(boletos)} invoices extracted.")

        payload["inicio_paginacao"] += 1

        if len(boletos) < 1000 or len(all_boletos) >= total_boletos:
            break

    return all_boletos


def _extract_for_all_statuses(user_token, status_list, date_filters: dict, label: str) -> list:
    all_records = []
    for status in status_list:
        try:
            records = _fetch_by_status(status, user_token, date_filters)
            logger.info(f"[{label}] Status {status}: {len(records)} invoices extracted total.")
            all_records.extend(records)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 406:
                logger.info(f"[{label}] Status {status} not supported by /boleto (406) — skipping.")
            else:
                logger.warning(f"[{label}] HTTP error extracting status {status}: {e}")
        except Exception as e:
            logger.warning(f"[{label}] Error extracting status {status}: {e}")
    return all_records


def extract_new_invoices(user_token, status_list) -> list:
    today = datetime.now()
    filters = {
        "data_emissao_inicial": _fmt(today - timedelta(days=7)),
        "data_emissao_final": _fmt(today - timedelta(days=1)),
    }
    logger.info(f"[NEW] Extracting by emissao: {filters['data_emissao_inicial']} to {filters['data_emissao_final']}")
    return _extract_for_all_statuses(user_token, status_list, filters, "NEW")


def extract_paid_invoices(user_token, status_list) -> list:
    today = datetime.now()
    filters = {
        "data_pagamento_inicial": _fmt(today - timedelta(days=30)),
        "data_pagamento_final": _fmt(today),
    }
    logger.info(f"[PAID] Extracting by pagamento: {filters['data_pagamento_inicial']} to {filters['data_pagamento_final']}")
    return _extract_for_all_statuses(user_token, status_list, filters, "PAID")


def extract_due_date_changes(user_token, status_list) -> list:
    today = datetime.now()
    filters = {
        "data_vencimento_inicial": _fmt(today - timedelta(days=30)),
        "data_vencimento_final": _fmt(today + timedelta(days=30)),
    }
    logger.info(f"[DUE] Extracting by vencimento: {filters['data_vencimento_inicial']} to {filters['data_vencimento_final']}")
    return _extract_for_all_statuses(user_token, status_list, filters, "DUE")


def run_invoice_extraction():
    logger.info("Starting invoice daily extraction pipeline...")

    try:
        user_token = authenticate_user()
        status_list = get_invoice_statuses(user_token)
        logger.info(f"Statuses found: {status_list}")

        new_records = extract_new_invoices(user_token, status_list)
        paid_records = extract_paid_invoices(user_token, status_list)
        due_records = extract_due_date_changes(user_token, status_list)

        merged = {}
        for record in new_records + paid_records + due_records:
            key = record.get("codigo_boleto")
            merged[key] = record

        all_records = list(merged.values())

        logger.info(
            f"Extraction summary: {len(new_records)} new | {len(paid_records)} paid | "
            f"{len(due_records)} due-date | {len(all_records)} unique after dedup"
        )

        current_date = datetime.now().strftime("%Y-%m-%d")
        output_path = os.path.join("data", "raw", f"invoices_{current_date}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_records, f, ensure_ascii=False, indent=2)

        logger.info(f"File successfully saved to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Critical failure in the invoice daily extraction pipeline: {e}")
        raise


if __name__ == "__main__":
    run_invoice_extraction()
