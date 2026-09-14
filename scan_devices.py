"""
BandFlow — BLE diagnostic scanner

Unlike ble_test.py, this does NOT filter by name — it lists every BLE
device the Pi's Bluetooth radio can see, along with signal strength.
This tells us whether the ESP32-S3 is visible at all, and if so,
exactly what name/address bleak sees it under.

Run with your venv active:
    python3 scan_devices.py

Make sure:
- The ESP32-S3 is powered on and running bandflow_esp32.ino
- Nothing else (like your phone) is currently connected to it,
  since a connected peripheral usually stops advertising
"""

import asyncio
from bleak import BleakScanner


async def main():
    print("Scanning for 15 seconds... (make sure nothing else is connected to the ESP32)")
    devices = await BleakScanner.discover(timeout=15.0, return_adv=True, scanning_mode="active")

    if not devices:
        print("\nNo BLE devices found at all.")
        print("This points to a Pi Bluetooth/driver issue rather than the ESP32.")
        return

    print(f"\nFound {len(devices)} device(s):\n")
    for address, (device, adv_data) in devices.items():
        # Some adapters expose the local name only through advertisement data.
        name = adv_data.local_name or device.name or "(no name)"
        is_bandflow = name.casefold() == "bandflow-wristband".casefold()
        marker = "  <-- BAND FLOW FOUND" if is_bandflow else ""
        print(f"Name: {name}{marker}")
        print(f"  Address: {address}")
        print(f"  RSSI: {adv_data.rssi} dBm")
        print(f"  Advertised service UUIDs: {adv_data.service_uuids}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
