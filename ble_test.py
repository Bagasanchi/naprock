"""Connect to the BandFlow wristband and test the BLE round trip."""

import asyncio

from bleak import BleakClient, BleakScanner

SERVICE_UUID = "12345678-1234-1234-1234-1234567890ab"
TASK_CHAR_UUID = "12345678-1234-1234-1234-1234567890ac"
STATUS_CHAR_UUID = "12345678-1234-1234-1234-1234567890ad"
TARGET_NAME = "bandflow-wristband"


async def find_band():
    print("Scanning for BandFlow (15 seconds)...")
    devices = await BleakScanner.discover(
        timeout=15.0,
        return_adv=True,
        scanning_mode="active",
    )

    for address, (device, advertisement) in devices.items():
        advertised_name = advertisement.local_name or device.name or ""
        service_uuids = [uuid.casefold() for uuid in advertisement.service_uuids]
        if (
            SERVICE_UUID.casefold() in service_uuids
            or advertised_name.casefold() == TARGET_NAME
        ):
            print(f"Found BandFlow: {advertised_name or '(name hidden)'} at {address}")
            return device

    print("BandFlow was not found.")
    print("Power on the ESP32, keep it disconnected from your phone, and try again.")
    return None


async def main():
    device = await find_band()
    if device is None:
        return

    async with BleakClient(device) as client:
        print(f"Connected: {client.is_connected}")

        def on_status(_, data):
            print(f"Status from band: {data.decode(errors='replace')}")

        await client.start_notify(STATUS_CHAR_UUID, on_status)
        await client.write_gatt_char(
            TASK_CHAR_UUID,
            b"Test subtask from Raspberry Pi",
            response=True,
        )
        print("Test subtask sent. Waiting 20 seconds for a status notification...")
        await asyncio.sleep(20)
        await client.stop_notify(STATUS_CHAR_UUID)


if __name__ == "__main__":
    asyncio.run(main())
