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


def _send_to_discord(content: str, description: str) -> None:
    """Posts content to the configured Discord webhook.

    Reads the webhook URL from config; if it is not set the alert is skipped
    silently so local/dev runs don't fail. Any error while sending is logged
    but never propagated — alerting must not break the pipeline itself.
    """
    webhook_url = config.DISCORD_WEBHOOK_URL
    if not webhook_url:
        logger.warning(f"DISCORD_WEBHOOK_URL not set; skipping {description}.")
        return

    payload = {
        "content": content,
        "allowed_mentions": {"users": [ALERT_MENTION_USER_ID]},
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"{description.capitalize()} sent to Discord.")
    except Exception as e:
        logger.error(f"Could not send {description} to Discord: {e}")


def send_failure_alert(flow, flow_run, state) -> None:
    """Prefect on_failure hook: posts a formatted failure message to Discord."""
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

    _send_to_discord(content, "failure alert")


def send_status_coverage_alert(
    table_name: str,
    added: dict[str, str],
    removed: dict[str, str],
) -> None:
    """Warns that the set of statuses returned by the source has changed.

    The status lists are filtered by the API user's permissions, so a code can be
    absent for months without any error — entities in that status are silently
    never extracted. Both directions matter: a new code means coverage just
    widened and needs validating, while a disappeared code means entities in it
    stopped being extracted and will quietly go stale in the dimensions.
    """
    if not added and not removed:
        return

    sections = []
    if added:
        listed = "\n".join(f"- `{code}` — {desc}" for code, desc in sorted(added.items()))
        sections.append(f"**Códigos novos:**\n{listed}")
    if removed:
        listed = "\n".join(f"- `{code}` — {desc}" for code, desc in sorted(removed.items()))
        sections.append(f"**Códigos que sumiram da origem:**\n{listed}")

    body = "\n\n".join(sections)
    content = (
        f"<@{ALERT_MENTION_USER_ID}>\n"
        "**⚠️ A lista de situações da origem mudou**\n\n"
        f"**Tabela:** {table_name}\n"
        f"{body}\n\n"
        "A cobertura da extração mudou. Como essa lista é filtrada por permissão "
        "do usuário da API, verifique se alguma entidade deixou de ser extraída."
    )

    _send_to_discord(content, "status coverage alert")
