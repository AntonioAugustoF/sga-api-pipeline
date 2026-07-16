from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from infra.config import config
from infra.logger import get_logger

logger = get_logger(__name__)

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")

# Discord user id mentioned on failure so the alert triggers a mobile push
# regardless of the channel's notification setting.
ALERT_MENTION_USER_ID = "1325197672772272168"


def _format_local(ts) -> tuple[str, str]:
    """Converts a UTC timestamp to local time, returning (date, time) strings."""
    if ts is None:
        return "-", "-"
    if not isinstance(ts, datetime):
        ts = datetime.fromisoformat(str(ts))
    local = ts.astimezone(LOCAL_TZ)
    return local.strftime("%d/%m/%Y"), local.strftime("%H:%M:%S")


def send_failure_alert(flow, flow_run, state) -> None:
    """Prefect on_failure hook: posts a formatted failure message to Discord.

    Reads the webhook URL from config; if it is not set the alert is skipped
    silently so local/dev runs don't fail. Any error while sending is logged
    but never propagated — alerting must not break the pipeline itself.
    """
    webhook_url = config.DISCORD_WEBHOOK_URL
    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL not set; skipping failure alert.")
        return

    data, hora = _format_local(getattr(state, "timestamp", None))
    message = getattr(state, "message", None) or "Sem detalhes."

    content = (
        f"<@{ALERT_MENTION_USER_ID}>\n"
        "**❌ O pipeline diário falhou**\n\n"
        f"**Execução:** {flow_run.name}\n"
        f"**Data:** {data}\n"
        f"**Hora:** {hora}\n"
        f"**Motivo:** {message}"
    )

    payload = {
        "content": content,
        "allowed_mentions": {"users": [ALERT_MENTION_USER_ID]},
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()
        logger.info("Failure alert sent to Discord.")
    except Exception as e:
        logger.error(f"Could not send failure alert to Discord: {e}")
