"""Config flow for custom_components/ha-minibus"""

import logging
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, API_BASE_URL, REGIONS, LANGUAGES

_LOGGER = logging.getLogger(__name__)


class GMBConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HK GMB ETA."""

    VERSION = 1

    def __init__(self):
        self.region = None
        self.route_code = None
        self.language = None

        self.route_data = []
        self.directions_map = {}

        self.route_id = None
        self.route_seq = None
        self.dest_name = None
        self.stops_map = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Get Region, Route Code, and Language."""
        errors = {}
        if user_input is not None:
            self.region = user_input["region"]
            self.route_code = user_input["route_code"]
            self.language = user_input["language"]

            session = async_get_clientsession(self.hass)
            url = f"{API_BASE_URL}/route/{self.region}/{self.route_code}"

            try:
                async with session.get(url) as resp:
                    res = await resp.json()
                    if "data" in res and res["data"]:
                        self.route_data = res["data"]
                        return await self.async_step_direction()
                    else:
                        errors["base"] = "route_not_found"
            except Exception:
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required("region", default="NT"): vol.In(REGIONS),
                vol.Required("route_code"): str,
                vol.Required("language", default="en"): vol.In(LANGUAGES),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_direction(self, user_input=None):
        """Step 2: Select Direction based on previously fetched Route Data."""
        if user_input is not None:
            selected = user_input["direction"]
            info = self.directions_map[selected]
            self.route_id = info["route_id"]
            self.route_seq = info["route_seq"]
            self.dest_name = info["dest_name"]

            session = async_get_clientsession(self.hass)
            url = f"{API_BASE_URL}/route-stop/{self.route_id}/{self.route_seq}"
            async with session.get(url) as resp:
                res = await resp.json()
                self.stops_map = {}
                for stop in res.get("data", []):
                    stop_id = stop["stop_id"]
                    # Fallback to English if the chosen language is unexpectedly missing
                    stop_name = stop.get(
                        f"name_{self.language}", stop.get("name_en", f"Stop {stop_id}")
                    )
                    self.stops_map[str(stop_id)] = stop_name
                return await self.async_step_stop()

        self.directions_map = {}
        for route in self.route_data:
            r_id = route["route_id"]
            for d in route.get("directions", []):
                r_seq = d["route_seq"]
                dest = d.get(f"dest_{self.language}", d.get("dest_en"))
                label = f"Route {r_id} (Seq {r_seq}) -> {dest}"
                self.directions_map[label] = {
                    "route_id": r_id,
                    "route_seq": r_seq,
                    "dest_name": dest,
                }

        schema = vol.Schema(
            {vol.Required("direction"): vol.In(list(self.directions_map.keys()))}
        )
        return self.async_show_form(step_id="direction", data_schema=schema)

    async def async_step_stop(self, user_input=None):
        """Step 3: Select the Specific Stop."""
        if user_input is not None:
            stop_id = user_input["stop_id"]
            stop_name = self.stops_map[stop_id]
            title = f"{self.route_code} - {stop_name}"

            return self.async_create_entry(
                title=title,
                data={
                    "stop_id": stop_id,
                    "stop_name": stop_name,
                    "route_id": self.route_id,
                    "route_seq": self.route_seq,
                    "dest_name": self.dest_name,
                    "language": self.language,
                    "route_code": self.route_code,
                },
            )

        schema = vol.Schema({vol.Required("stop_id"): vol.In(self.stops_map)})
        return self.async_show_form(step_id="stop", data_schema=schema)
