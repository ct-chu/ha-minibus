"""Sensor platform for custom_components/ha-minibus."""

from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
import homeassistant.util.dt as dt_util

from .const import DOMAIN, API_BASE_URL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""
    stop_id = entry.data["stop_id"]
    route_id = entry.data["route_id"]
    route_seq = entry.data["route_seq"]

    session = async_get_clientsession(hass)

    async def async_update_data():
        url = f"{API_BASE_URL}/eta/stop/{stop_id}"
        async with session.get(url) as resp:
            res = await resp.json()
            eta_data = []

            data_node = res.get("data", [])
            if isinstance(data_node, dict):
                data_node = data_node.get("eta", [])

            if isinstance(data_node, list):
                for item in data_node:
                    if isinstance(item, dict):
                        if (
                            item.get("route_id") == route_id
                            and item.get("route_seq") == route_seq
                        ):
                            eta_data = item.get("eta", [])
                            break

            # Return both the ETA payload and the current localized timestamp
            return {"eta": eta_data, "last_updated": dt_util.now()}

    # Poll the endpoint every 60 seconds automatically
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"gmb_eta_stop_{stop_id}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=60),
    )

    await coordinator.async_config_entry_first_refresh()

    entities = [
        GmbDirectionSensor(entry),
        GmbLastUpdatedSensor(coordinator, entry),
        GmbEtaSensor(coordinator, entry, 0),
        GmbEtaSensor(coordinator, entry, 1),
        GmbEtaSensor(coordinator, entry, 2),
    ]

    async_add_entities(entities)


class GmbDirectionSensor(SensorEntity):
    """Sensor to display the static route direction."""

    def __init__(self, entry):
        self._entry = entry

        self._attr_unique_id = f"gmb_dir_{entry.data['stop_id']}_{entry.data['route_id']}_{entry.data['route_seq']}"
        self._attr_has_entity_name = True
        self._attr_icon = "mdi:sign-direction"

        lang = entry.data["language"]
        dest = entry.data["dest_name"]

        if lang == "tc":
            self._attr_name = "方向"
            self._state = f"往{dest}"
        elif lang == "sc":
            self._attr_name = "方向"
            self._state = f"往{dest}"
        else:
            self._attr_name = "Direction"
            self._state = f"To {dest}"

    @property
    def native_value(self):
        return self._state

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._entry.data["stop_id"]))},
            name=self._entry.data["stop_name"],
            manufacturer="Hong Kong GMB",
            model=f"Route {self._entry.data['route_code']}",
            entry_type=DeviceEntryType.SERVICE,
        )


class GmbLastUpdatedSensor(CoordinatorEntity, SensorEntity):
    """Sensor to display the timestamp of the last API response update."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

        self._attr_unique_id = f"gmb_updated_{entry.data['stop_id']}_{entry.data['route_id']}_{entry.data['route_seq']}"
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

        lang = entry.data["language"]
        if lang in ["tc", "sc"]:
            self._attr_name = "最後更新"
        else:
            self._attr_name = "Last Updated"

    @property
    def native_value(self):
        """Return the precise timestamp of the last successful fetch."""
        if self.coordinator.data and "last_updated" in self.coordinator.data:
            return self.coordinator.data["last_updated"]
        return None

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._entry.data["stop_id"]))},
            name=self._entry.data["stop_name"],
            manufacturer="Hong Kong GMB",
            model=f"Route {self._entry.data['route_code']}",
            entry_type=DeviceEntryType.SERVICE,
        )


class GmbEtaSensor(CoordinatorEntity, SensorEntity):
    """Sensor to display the ETA values."""

    def __init__(self, coordinator, entry, index):
        super().__init__(coordinator)
        self._entry = entry
        self._index = index

        self._attr_unique_id = f"gmb_eta_{entry.data['stop_id']}_{entry.data['route_id']}_{entry.data['route_seq']}_{index + 1}"
        self._attr_has_entity_name = True
        self._attr_name = f"ETA {index + 1}"
        self._attr_icon = "mdi:bus-clock"

    @property
    def native_value(self):
        if not self.coordinator.data or "eta" not in self.coordinator.data:
            return "N/A"

        etas = self.coordinator.data["eta"]
        if isinstance(etas, list) and len(etas) > self._index:
            eta_entry = etas[self._index]
            if isinstance(eta_entry, dict):
                diff = eta_entry.get("diff")
                if diff is not None:
                    return f"{diff} min"
                return eta_entry.get("eta", "Unknown")
        return "N/A"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._entry.data["stop_id"]))},
            name=self._entry.data["stop_name"],
            manufacturer="Hong Kong GMB",
            model=f"Route {self._entry.data['route_code']}",
            entry_type=DeviceEntryType.SERVICE,
        )
