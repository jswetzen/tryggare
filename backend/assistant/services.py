from django.core.exceptions import ValidationError
from django.views.decorators.debug import sensitive_variables

from .models import LLMProvider, validate_base_url
from .providers import list_models


@sensitive_variables("api_key")
def fetch_models(
    provider: LLMProvider, base_url: str = "", api_key: str = ""
) -> list[str]:
    """Models at ``base_url`` (default: the saved one), so an admin can pick
    before saving. A blank key falls back to the saved key for the saved URL
    only. Raises ValidationError for a bad URL, ProviderError for the call."""
    base_url = (base_url or provider.base_url).strip()
    if not base_url:
        raise ValidationError(
            {
                "base_url": LLMProvider._meta.get_field("base_url").error_messages[
                    "blank"
                ]
            }
        )
    validate_base_url(base_url)
    return list_models(base_url, api_key or provider.key_for(base_url))
