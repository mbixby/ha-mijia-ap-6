"""Tests for manual speed and Auto controls."""

import unittest
from unittest.mock import AsyncMock, MagicMock, call, patch

from homeassistant.exceptions import HomeAssistantError
from miio import DeviceException

from custom_components.xiaomi_air_purifier.const import MODE_AUTO, MODE_FAVORITE
from custom_components.xiaomi_air_purifier.device import AirPurifierStatus, XiaomiAirPurifier
from custom_components.xiaomi_air_purifier.fan import XiaomiAirPurifierFan


class DeviceTests(unittest.TestCase):
    """Test MIoT properties used by the manual control."""

    def setUp(self):
        patcher = patch("custom_components.xiaomi_air_purifier.device.MiotDevice")
        self.addCleanup(patcher.stop)
        self.miot_factory = patcher.start()
        self.miot = self.miot_factory.return_value
        self.miot.set_property.return_value = [{"code": 0}]
        self.device = XiaomiAirPurifier("192.0.2.1", "0" * 32)

    def test_manual_speed_uses_favorite_mode_and_property(self):
        self.device.set_favorite_speed(11)
        self.assertEqual(
            self.miot.set_property.call_args_list,
            [call("mode", MODE_FAVORITE), call("favorite_speed", 11)],
        )
        self.assertEqual(
            self.miot_factory.call_args.kwargs["mapping"]["favorite_speed"],
            {"siid": 9, "piid": 1},
        )

    def test_status_reads_favorite_speed(self):
        self.miot.get_properties_for_mapping.return_value = [
            {"did": "power", "code": 0, "value": True},
            {"did": "mode", "code": 0, "value": MODE_FAVORITE},
            {"did": "favorite_speed", "code": 0, "value": 7},
        ]
        status = self.device.status()
        self.assertEqual(status.favorite_speed, 7)
        self.assertIsNone(status.preset_mode)

    def test_rejected_write_stops_following_commands(self):
        self.miot.set_property.return_value = [{"code": -4004}]
        with self.assertRaises(DeviceException):
            self.device.set_favorite_speed(5)
        self.miot.set_property.assert_called_once_with("mode", MODE_FAVORITE)


class MiotProtocolTests(unittest.TestCase):
    """Test the actual python-miio property requests."""

    def test_manual_speed_requests(self):
        with patch(
            "miio.miot_device.MiotDevice.send", return_value=[{"code": 0}]
        ) as send:
            device = XiaomiAirPurifier("192.0.2.1", "0" * 32)
            device.set_favorite_speed(11)
        self.assertEqual(
            send.call_args_list,
            [
                call(
                    "set_properties",
                    [{"did": "mode", "siid": 2, "piid": 4, "value": 5}],
                ),
                call(
                    "set_properties",
                    [{"did": "favorite_speed", "siid": 9, "piid": 1, "value": 11}],
                ),
            ],
        )


class FanTests(unittest.IsolatedAsyncioTestCase):
    """Test Home Assistant fan behavior."""

    def setUp(self):
        self.device = MagicMock()
        self.device.get_device_info.return_value = MagicMock(
            model="xiaomi.airp.mb5",
            firmware_version="1",
            hardware_version="1",
            mac_address=None,
        )
        self.coordinator = MagicMock()
        self.coordinator.device = self.device
        self.coordinator.entry.unique_id = "device"
        self.coordinator.entry.title = "Purifier"
        self.coordinator.data = AirPurifierStatus(power=True, mode=MODE_FAVORITE)
        self.coordinator.async_request_refresh = AsyncMock()
        self.fan = XiaomiAirPurifierFan(self.coordinator)
        self.fan.hass = MagicMock()
        self.fan.hass.async_add_executor_job = AsyncMock(
            side_effect=lambda func, *args: func(*args)
        )

    async def test_manual_values_round_trip_and_leave_auto(self):
        self.coordinator.data.mode = MODE_AUTO
        self.assertEqual(self.fan.preset_mode, "Auto")
        self.assertIsNone(self.fan.percentage)
        for speed in range(12):
            self.coordinator.data.mode = MODE_FAVORITE
            self.coordinator.data.favorite_speed = speed
            percentage = self.fan.percentage
            self.assertIsNotNone(percentage)
            await self.fan.async_set_percentage(percentage)
            self.device.set_favorite_speed.assert_called_with(speed)
            self.assertIsNone(self.fan.preset_mode)
        self.assertEqual(self.fan.preset_modes, ["Auto"])

    async def test_speed_and_auto_turn_on_when_off(self):
        self.coordinator.data.power = False
        self.assertEqual(self.fan.percentage, 0)
        await self.fan.async_set_percentage(100)
        self.device.set_power.assert_called_once_with(True)
        self.device.set_favorite_speed.assert_called_once_with(11)
        self.device.reset_mock()
        await self.fan.async_set_preset_mode("Auto")
        self.device.set_power.assert_called_once_with(True)
        self.device.set_preset_mode.assert_called_once_with("Auto")

    async def test_zero_turns_off_and_invalid_values_do_not_power_on(self):
        await self.fan.async_turn_on(percentage=0)
        self.device.set_power.assert_called_once_with(False)
        self.device.reset_mock()
        with self.assertRaises(HomeAssistantError):
            await self.fan.async_turn_on(percentage=101)
        self.device.set_power.assert_not_called()
        with self.assertRaises(HomeAssistantError):
            await self.fan.async_set_preset_mode("Sleep")
        self.device.set_power.assert_not_called()

    async def test_unknown_or_other_mode_does_not_report_manual_speed(self):
        self.coordinator.data = AirPurifierStatus(power=None, mode=MODE_FAVORITE)
        self.assertIsNone(self.fan.is_on)
        self.assertIsNone(self.fan.percentage)
        self.coordinator.data = AirPurifierStatus(
            power=True, mode=3, favorite_speed=4
        )
        self.assertIsNone(self.fan.percentage)
        self.assertIsNone(self.fan.preset_mode)

    async def test_device_error_is_reported(self):
        self.device.set_favorite_speed.side_effect = DeviceException("rejected")
        with self.assertRaises(HomeAssistantError):
            await self.fan.async_set_percentage(50)
        self.coordinator.async_request_refresh.assert_not_awaited()
