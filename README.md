# Xiaomi Air Purifier 6 for Home Assistant

Local integration for the Xiaomi Air Purifier 6, model `xiaomi.airp.mb5`.
It uses the miIO/MIoT protocol and does not require a cloud connection at runtime.

## Installation

Requires Home Assistant 2024.11 or newer, a device on the local network, its IP
address, and its 32-character hexadecimal miIO token.

### Home Assistant Marketplace

1. Publish these files to a public GitHub repository.
2. In Home Assistant, open **Settings > Marketplace > Add from link**.
3. Add `https://github.com/praktronics/Xiaomi-HA`, selecting **Integration**
   if prompted. Connect GitHub when requested.
4. Open the repository and select **Install**. Restart Home Assistant if prompted.
5. Under **Settings > Devices & services**, select **Add integration**, search
   for **Xiaomi Air Purifier**, and enter the IP address and token.

For older Home Assistant versions with HACS, add the same URL under **HACS >
Custom repositories** as an integration, install it, and restart Home Assistant.

### Manual installation

Copy `custom_components/xiaomi_air_purifier` to
`/config/custom_components/xiaomi_air_purifier`, restart Home Assistant, and
add the integration through **Settings > Devices & services**.

Each purifier can be added separately. The token can be obtained with a
community tool such as
[Xiaomi-cloud-tokens-extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor).

## Controls

The fan entity has an on/off control, a manual speed slider, and an **Auto**
preset. The slider uses the device's favorite-mode setting, which exposes 12
values. Percentages are rounded to those values, and 0% turns the device off.
Selecting a speed switches out of Auto. The current slider value is unknown
while the device is in Auto or another mode selected outside Home Assistant.

Switches control the screen, anion, and UV lamp. Sensors report temperature,
humidity, PM1, PM2.5, PM10, air quality, motor speed, and filter life.
The device is polled every 30 seconds.

## Troubleshooting

- Check the IP address, network reachability, and token if setup fails.
- Check that `custom_components/xiaomi_air_purifier/manifest.json` exists and
  restart Home Assistant if the integration is missing.
- If the device changes IP address, remove and re-add the integration.

The device properties are documented in the
[Xiaomi MIoT specification](https://home.miot-spec.com/spec/xiaomi.airp.mb5).
