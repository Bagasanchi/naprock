/*
  BandFlow — ESP32-S3 wristband BLE firmware (step 1: no display yet)

  What this does:
  - Advertises itself over BLE as "BandFlow-Wristband"
  - Creates ONE service with TWO characteristics:
      TASK_CHAR   — the Raspberry Pi WRITES to this. This is how the Pi
                    sends the current subtask text to the band.
      STATUS_CHAR — the band WRITES to this (Pi reads/subscribes). This is
                    how the band reports things back, e.g. "DONE" when the
                    user taps a button.
  - For now, instead of a touchscreen button, it fakes a "DONE" report
    every 15 seconds so you can test the round-trip without any display
    wiring yet. Swap that timer for a real touch event once the screen
    is wired in.

  Setup required in Arduino IDE before flashing:
  1. File > Preferences > Additional Board URLs, add:
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-storage/package_esp32_index.json
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
  2. Tools > Board > Boards Manager > search "esp32" > install "esp32 by Espressif Systems"
  3. Tools > Board > select your specific ESP32-S3 board
  4. Sketch > Include Library > Manage Libraries > search "NimBLE-Arduino" > install
  5. Select the correct Port (USB) before uploading

  How to test after flashing (no Pi needed yet):
  - Install "nRF Connect" (free) on your phone
  - Scan for BLE devices, find "BandFlow-Wristband", connect
  - You should see one service with two characteristics
  - Try writing text to TASK_CHAR from the app — watch Serial Monitor
    on your laptop print what it received
  - Watch STATUS_CHAR update every 15 seconds with "DONE"
*/

#include <NimBLEDevice.h>

// These are just random unique IDs (UUIDs) that identify our service
// and characteristics. They must match EXACTLY on the Raspberry Pi side
// later, so don't change them once the Pi code is written against them.
#define SERVICE_UUID        "12345678-1234-1234-1234-1234567890ab"
#define TASK_CHAR_UUID       "12345678-1234-1234-1234-1234567890ac"
#define STATUS_CHAR_UUID     "12345678-1234-1234-1234-1234567890ad"

NimBLECharacteristic *taskCharacteristic;
NimBLECharacteristic *statusCharacteristic;

unsigned long lastFakeStatusUpdate = 0;
const unsigned long FAKE_STATUS_INTERVAL_MS = 15000; // every 15 seconds

// Called automatically whenever the Pi writes to TASK_CHAR
class TaskCallback : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic *characteristic) {
    std::string value = characteristic->getValue();
    Serial.print("Received subtask from Pi: ");
    Serial.println(value.c_str());
    // Later: this is where you'll update the actual screen with `value`
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println("Starting BandFlow wristband BLE...");

  NimBLEDevice::init("BandFlow-Wristband");

  NimBLEServer *server = NimBLEDevice::createServer();
  NimBLEService *service = server->createService(SERVICE_UUID);

  // Pi -> band: Pi writes subtask text here
  taskCharacteristic = service->createCharacteristic(
    TASK_CHAR_UUID,
    NIMBLE_PROPERTY::WRITE
  );
  taskCharacteristic->setCallbacks(new TaskCallback());

  // Band -> Pi: band writes status updates here, Pi reads/subscribes
  statusCharacteristic = service->createCharacteristic(
    STATUS_CHAR_UUID,
    NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
  );
  statusCharacteristic->setValue("READY");

  service->start();

  // Make the device discoverable
  NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  advertising->start();

  Serial.println("BLE advertising started. Look for 'BandFlow-Wristband' in nRF Connect.");
}

void loop() {
  // Fake a "user tapped done" event every 15 seconds, just so you have
  // something to test the Pi <-> band round trip with before the real
  // touchscreen button exists.
  unsigned long now = millis();
  if (now - lastFakeStatusUpdate > FAKE_STATUS_INTERVAL_MS) {
    lastFakeStatusUpdate = now;
    statusCharacteristic->setValue("SERGEI GOMO");
    statusCharacteristic->notify();
    Serial.println("Sent fake status update: SERGEI GOMO");
  }
}
