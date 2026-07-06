from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .zapcap_client import ZapCapApiClient, ZapCapApiError


@dataclass(frozen=True)
class ZapCapTemplateOption:
    id: str
    name: str


def list_zapcap_template_options(settings: Settings) -> list[ZapCapTemplateOption]:
    if not settings.zapcap_api_key:
        return []
    client = ZapCapApiClient(
        api_key=settings.zapcap_api_key,
        base_url=settings.zapcap_api_base_url,
        timeout_seconds=settings.zapcap_request_timeout_seconds,
    )
    try:
        templates = client.list_templates()
    except ZapCapApiError as exc:
        raise RuntimeError(str(exc)) from exc
    return [ZapCapTemplateOption(id=item.id, name=item.name) for item in templates]
