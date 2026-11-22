"""Fan platform for Xiaomi Air Purifier."""

from __future__ import annotations

from typing import Any

from miio import DeviceException

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from . import XiaomiAirPurifierConfigEntry
from .const import FAVORITE_SPEEDS, MODE_FAVORITE, PRESET_MODE_AUTO
from .entity import XiaomiAirPurifierEntity

ORDERED_FAVORITE_SPEEDS = list(FAVORITE_SPEEDS)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XiaomiAirPurifierConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the air purifier fan entity."""
    coordinator = entry.runtime_data
    async_add_entities([XiaomiAirPurifierFan(coordinator)])


class XiaomiAirPurifierFan(XiaomiAirPurifierEntity, FanEntity):
    """Representation of the air purifier as a fan."""

    _attr_name = None
    _attr_translation_key = "air_purifier"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = [PRESET_MODE_AUTO]
    _attr_speed_count = len(ORDERED_FAVORITE_SPEEDS)

    def __init__(self, coordinator) -> None:
        """Initialize the fan entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._unique_base}_fan"

    @property
    def is_on(self) -> bool | None:
        """Return true if the purifier is on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.is_on

    @property
    def percentage(self) -> int | None:
        """Return the manual speed as a percentage."""
        status = self.coordinator.data
        if status is None or status.is_on is None:
            return None
        if not status.is_on:
            return 0
        if status.mode != MODE_FAVORITE or status.favorite_speed not in FAVORITE_SPEEDS:
            return None
        return ordered_list_item_to_percentage(
            ORDERED_FAVORITE_SPEEDS, status.favorite_speed
        )

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.preset_mode

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the purifier on, optionally setting speed or preset."""
        if percentage == 0 and preset_mode is None:
            await self.async_turn_off()
            return
        try:
            if preset_mode is not None and preset_mode != PRESET_MODE_AUTO:
                raise ValueError(f"Unknown preset mode: {preset_mode}")
            if preset_mode is None and percentage is not None:
                self._validate_percentage(percentage)
            await self.hass.async_add_executor_job(self._device.set_power, True)
            if preset_mode is not None:
                await self.hass.async_add_executor_job(
                    self._device.set_preset_mode, preset_mode
                )
            elif percentage is not None:
                await self._async_set_percentage(percentage)
        except (DeviceException, ValueError) as err:
            raise HomeAssistantError(f"Failed to turn on air purifier: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the purifier off."""
        try:
            await self.hass.async_add_executor_job(self._device.set_power, False)
        except DeviceException as err:
            raise HomeAssistantError(f"Failed to turn off air purifier: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the manual fan speed percentage."""
        if percentage == 0:
            await self.async_turn_off()
            return
        try:
            self._validate_percentage(percentage)
            await self._async_ensure_on()
            await self._async_set_percentage(percentage)
        except (DeviceException, ValueError) as err:
            raise HomeAssistantError(f"Failed to set fan speed: {err}") from err
        await self.coordinator.async_request_refresh()

    async def _async_set_percentage(self, percentage: int) -> None:
        """Map percentage to a favorite speed and send it to the device."""
        speed = percentage_to_ordered_list_item(
            ORDERED_FAVORITE_SPEEDS, percentage
        )
        await self.hass.async_add_executor_job(self._device.set_favorite_speed, speed)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the operation mode preset."""
        try:
            if preset_mode != PRESET_MODE_AUTO:
                raise ValueError(f"Unknown preset mode: {preset_mode}")
            await self._async_ensure_on()
            await self.hass.async_add_executor_job(
                self._device.set_preset_mode, preset_mode
            )
        except (DeviceException, ValueError) as err:
            raise HomeAssistantError(f"Failed to set preset mode: {err}") from err
        await self.coordinator.async_request_refresh()

    @staticmethod
    def _validate_percentage(percentage: int) -> None:
        """Reject percentages outside the manual speed range."""
        if not 1 <= percentage <= 100:
            raise ValueError(f"Invalid fan percentage: {percentage}")

    async def _async_ensure_on(self) -> None:
        """Power on the purifier if necessary."""
        status = self.coordinator.data
        if status is None or status.is_on is not True:
            await self.hass.async_add_executor_job(self._device.set_power, True)
