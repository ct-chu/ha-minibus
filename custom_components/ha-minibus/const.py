"""Constants for custom_components/ha-minibus."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "ha-minibus"
API_BASE_URL = "https://data.etagmb.gov.hk"

REGIONS = {
    "NT": "New Territories",
    "KLN": "Kowloon",
    "HKI": "Hong Kong Island",
}

LANGUAGES = {
    "tc": "Traditional Chinese",
    "sc": "Simplified Chinese",
    "en": "English",
}
