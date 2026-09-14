"""BandFlow Flask API and background BLE connection manager."""

import asyncio
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError

from bleak import BleakClient, BleakScanner
from flask import Flask, jsonify, request

SERVICE_UUID = "12345678-1234-1234-1234-1234567890ab"
TASK_CHAR_UUID = "12345678-1234-1234-1234-1234567890ac"
STATUS_CHAR_UUID = "12345678-1234-1234-1234-1234567890ad"
TARGET_NAME = "bandflow-wristband"

SCAN_SECONDS = 15.0
RECONNECT_DELAY_SECONDS = 5.0
TASK_WRITE_TIMEOUT_SECONDS = 10.0

app = Flask(__name__)

_status_lock = threading.Lock()
_latest_status = None


class BandFlowBle:
    def __init__(self):
        self.loop = None
        self.client = None
        self._connected = None
        self.thread = threading.Thread(
            target=self._run,
            name="bandflow-ble",
            daemon=True,
        )

    def start(self):
        self.thread.start()

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connection_loop())
        self.loop.close()

    async def _find_band(self):
        print("Scanning for BandFlow...")
        devices = await BleakScanner.discover(
            timeout=SCAN_SECONDS,
            return_adv=True,
            scanning_mode="active",
        )

        for address, (device, advertisement) in devices.items():
            advertised_name = advertisement.local_name or device.name or ""
            service_uuids = [
                uuid.casefold() for uuid in advertisement.service_uuids
            ]
            if (
                SERVICE_UUID.casefold() in service_uuids
                or advertised_name.casefold() == TARGET_NAME
            ):
                print(
                    f"Found BandFlow: {advertised_name or '(name hidden)'} "
                    f"at {address}"
                )
                return device

        print("BandFlow not found; retrying...")
        return None

    async def _connection_loop(self):
        global _latest_status

        while True:
            device = await self._find_band()
            if device is None:
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                continue

            disconnected = asyncio.Event()

            def on_disconnect(_):
                print("BandFlow disconnected; scanning again...")
                self.loop.call_soon_threadsafe(disconnected.set)

            try:
                async with BleakClient(device, disconnected_callback=on_disconnect) as client:
                    self.client = client
                    self._connected = asyncio.Event()
                    self._connected.set()

                    def on_status(_, data):
                        global _latest_status
                        status = data.decode(errors="replace")
                        with _status_lock:
                            _latest_status = status
                        print(f"Status from band: {status}")

                    await client.start_notify(STATUS_CHAR_UUID, on_status)
                    print("Connected!")
                    await disconnected.wait()
                    await client.stop_notify(STATUS_CHAR_UUID)
            except Exception as error:
                print(f"BLE connection error: {error}; retrying...")
            finally:
                self.client = None
                self._connected = None

            await asyncio.sleep(RECONNECT_DELAY_SECONDS)

    async def send_task(self, text):
        if self._connected is None:
            raise RuntimeError("BandFlow is not connected")

        await asyncio.wait_for(
            self._connected.wait(),
            timeout=TASK_WRITE_TIMEOUT_SECONDS,
        )
        if self.client is None or not self.client.is_connected:
            raise RuntimeError("BandFlow is not connected")

        await self.client.write_gatt_char(
            TASK_CHAR_UUID,
            text.encode("utf-8"),
            response=True,
        )


ble_manager = BandFlowBle()
_start_lock = threading.Lock()
_started = False


def start_ble_once():
    global _started
    with _start_lock:
        if not _started:
            ble_manager.start()
            _started = True


@app.get("/ping")
def ping():
    return jsonify(status="ok")


@app.get("/status")
def status():
    with _status_lock:
        current_status = _latest_status
    return jsonify(status=current_status)


@app.post("/task")
def task():
    body = request.get_json(silent=True) or {}
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        return jsonify(error="JSON body must contain a non-empty string 'text'"), 400

    if ble_manager.loop is None or not ble_manager.thread.is_alive():
        return jsonify(error="BLE connection thread is not running"), 503

    future = asyncio.run_coroutine_threadsafe(
        ble_manager.send_task(text),
        ble_manager.loop,
    )
    try:
        future.result(timeout=TASK_WRITE_TIMEOUT_SECONDS + 2)
    except FutureTimeoutError:
        future.cancel()
        return jsonify(error="Timed out sending task to BandFlow"), 504
    except RuntimeError as error:
        return jsonify(error=str(error)), 503
    except Exception as error:
        return jsonify(error=f"Could not send task: {error}"), 503

    return jsonify(status="sent")


start_ble_once()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
