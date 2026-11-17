// kukucs: one-button camera. Always in deep sleep.
//   short press            -> photo (+ tiny thumbnail), back to sleep
//   long press (2 s)       -> Wi-Fi hotspot "kukucs" with a gallery (opens by itself on the phone)
//   plugged into a PC + short press -> the SD card shows up as a USB drive
// Photos go to the microSD card when one is in (FAT32), else to internal flash (~30 small photos).
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Preferences.h>
#include <sys/time.h>
#include "esp_camera.h"
#include "driver/rtc_io.h"
#include "esp_rom_crc.h"
#include "exif.h"
#include "page.h"
#include "zipstream.h"

#include <SD.h>
#include <LittleFS.h>

bool onSD = false;  // checked on every wake
#define store (onSD ? (fs::FS &)SD : (fs::FS &)LittleFS)
uint64_t freeBytes() { return onSD ? SD.totalBytes() - SD.usedBytes() : LittleFS.totalBytes() - LittleFS.usedBytes(); }

#if !ARDUINO_USB_MODE  // USB drive needs TinyUSB (set in platformio.ini)
#define USB_DRIVE 1
#include "USB.h"
#include "USBMSC.h"
#include "esp32-hal-tinyusb.h"
USBMSC msc;  // global, so its interface is registered before USB starts at boot
#endif

#define AP_SSID "kukucs"
#define AP_PASS "kukucs123"  // min 8 chars
const gpio_num_t BTN = GPIO_NUM_2;  // D1, button to GND
const int LED = 21;  // orange user LED, on when LOW. Also the SD card's chip-select: only flash it while the card is idle
const uint32_t LONG_MS = 2000;
const uint32_t IDLE_MS = 5 * 60 * 1000;      // hotspot: no page loads for this long -> sleep
const uint32_t NOBODY_MS = 2 * 60 * 1000;    // hotspot: no phone connected for this long -> sleep (forgotten)
const uint32_t USB_WAIT_MS = 900;   // how long a PC gets to set up the USB device after wake
const char *THUMBS = "/.thumbs";
// How the pictures must be turned depends on how the board sits. Measured with test photos: held like it sits in the
// case v5 (USB-C pointing down, lens away from you) the picture is already upright and landscape: no turn needed.
// If your pictures come out turned: EXIF_ORIENTATION 3 = half turn, 6 = quarter turn clockwise, 8 = counter-clockwise;
// SENSOR_ROTATE_180 does a half turn in the sensor itself (free, no tag).
const bool SENSOR_ROTATE_180 = false;
const uint8_t EXIF_ORIENTATION = 1;
RTC_DATA_ATTR int32_t tzMin = 0;    // phone's UTC offset; survives deep sleep, like the clock itself

WebServer srv(80);
DNSServer dns;
uint32_t lastReq, lastPhone;
enum Mode { SLEEPING, HOTSPOT, USBDRIVE } mode = SLEEPING;

#ifdef FAKE_BTN
// test build: serial 's'/'l' act as short/long press ('d' = USB drive). No restarts: they drop USB.
uint32_t fakeUntil = 0;  // fake button "held" until this millis()
bool fakeDrive = false;
#endif

bool pressed() {
#ifdef FAKE_BTN
  if (millis() < fakeUntil) return true;
#endif
  return digitalRead(BTN) == LOW;
}

void ledFlash(uint32_t ms) {
  digitalWrite(LED, LOW);
  delay(ms);
  digitalWrite(LED, HIGH);
}

// The camera module has no power switch: put the sensor in standby, or it keeps drawing mA in deep sleep.
void cameraOff() {
  sensor_t *s = esp_camera_sensor_get();
  if (!s) return;
  if (s->id.PID == OV2640_PID) s->set_reg(s, 0x109, 0x10, 0x10);  // bank 1 (sensor), COM2 bit 4: standby
  else s->set_reg(s, 0x3008, 0x40, 0x40);                         // OV3660/OV5640 SYSTEM_CTRL0: power down
  esp_camera_deinit();
}

void sleepNow() {
  Serial.println("sleep");
  while (pressed()) delay(10);  // else we wake right away
  delay(50);                    // debounce release
  cameraOff();
  dns.stop();
  srv.stop();
  WiFi.mode(WIFI_OFF);
#ifdef USB_DRIVE
  if (mode == USBDRIVE) {  // the PC may have changed files: drop our cached view of the card
    msc.mediaPresent(false);
    SD.end();
    SD.begin(LED);
  }
#endif
  mode = SLEEPING;
#ifdef FAKE_BTN
  Serial.println("fake sleep: send s = short press, l = long press, d = USB drive");
  return;  // stay awake; loop() waits for the next fake press
#endif
  Serial.flush();
  rtc_gpio_pullup_en(BTN);
  rtc_gpio_pulldown_dis(BTN);
  esp_sleep_enable_ext0_wakeup(BTN, 0);
  esp_deep_sleep_start();
}

bool initCamera() {
  camera_config_t c = {};
  c.pin_pwdn = -1;  c.pin_reset = -1;  c.pin_xclk = 10;
  c.pin_sccb_sda = 40;  c.pin_sccb_scl = 39;
  c.pin_d7 = 48;  c.pin_d6 = 11;  c.pin_d5 = 12;  c.pin_d4 = 14;
  c.pin_d3 = 16;  c.pin_d2 = 18;  c.pin_d1 = 17;  c.pin_d0 = 15;
  c.pin_vsync = 38;  c.pin_href = 47;  c.pin_pclk = 13;
  c.xclk_freq_hz = 20000000;
  c.ledc_timer = LEDC_TIMER_0;  c.ledc_channel = LEDC_CHANNEL_0;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = onSD ? FRAMESIZE_UXGA : FRAMESIZE_SVGA;  // 1600x1200 on the card; 800x600 fits ~30 in flash
  c.jpeg_quality = 10;
  c.fb_count = 2;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;
  esp_err_t err = esp_camera_init(&c);  // also wakes the sensor from standby (it resets it)
  if (err != ESP_OK) Serial.printf("camera init failed 0x%x\n", err);
  else if (SENSOR_ROTATE_180) {  // flip + mirror = a half turn; init resets the sensor, so apply it on every start
    sensor_t *s = esp_camera_sensor_get();
    s->set_vflip(s, 1);
    s->set_hmirror(s, 1);
  }
  return err == ESP_OK;
}

// --- file names: date + time once a phone has set the clock, else a counter
bool clockSet() { return time(nullptr) > 1700000000; }

String newName() {
  char b[40];
  if (clockSet()) {
    time_t t = time(nullptr) + tzMin * 60;
    struct tm tm;
    gmtime_r(&t, &tm);
    strftime(b, sizeof b, "kukucs_%Y-%m-%d_%H%M%S", &tm);
    String n = String("/") + b + ".jpg";
    for (int i = 2; store.exists(n); i++) n = String("/") + b + "_" + i + ".jpg";
    return n;
  }
  Preferences p;
  p.begin("cam");
  uint32_t c = p.getUInt("n", 0) + 1;  // in NVS, so names never repeat after power loss
  p.putUInt("n", c);
  p.end();
  snprintf(b, sizeof b, "/kukucs_%05u.jpg", (unsigned)c);
  return b;
}

// saves a JPEG with the orientation tag added (see exif.h), so photos show upright without any pixel work
bool saveFile(const String &path, const uint8_t *buf, size_t len) {
  File f = store.open(path, FILE_WRITE);
  size_t at = EXIF_ORIENTATION == 1 ? 0 : exifInsertAt(buf, len);
  size_t w = 0;
  if (f && at) {
    uint8_t exif[EXIF_SEG_LEN];
    exifSegment(EXIF_ORIENTATION, exif);
    w = f.write(buf, at) + f.write(exif, sizeof exif) + f.write(buf + at, len - at);
    len += sizeof exif;
  } else if (f) {
    w = f.write(buf, len);
  }
  if (f) f.close();
  if (w == len) return true;
  store.remove(path);  // don't leave a truncated JPEG behind (storage full)
  Serial.printf("write failed %s (%u/%u bytes)\n", path.c_str(), (unsigned)w, (unsigned)len);
  return false;
}

// returns the saved photo's path, or "" if it failed
String takePhoto() {
  // first frames come out dark/green while auto-exposure settles
  for (int i = 0; i < 3; i++) esp_camera_fb_return(esp_camera_fb_get());
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) { Serial.println("capture failed"); return ""; }
  String name = newName();
  bool ok = saveFile(name, fb->buf, fb->len);
  if (ok) Serial.printf("saved %s (%u bytes) on %s\n", name.c_str(), (unsigned)fb->len, onSD ? "SD card" : "internal flash");
  esp_camera_fb_return(fb);
  if (!ok) return "";

  // tiny thumbnail, so the gallery grid doesn't make the phone load every full photo
  sensor_t *s = esp_camera_sensor_get();
  s->set_framesize(s, FRAMESIZE_QQVGA);
  for (int i = 0; i < 2; i++) esp_camera_fb_return(esp_camera_fb_get());  // frames still at the old size
  fb = esp_camera_fb_get();
  if (fb && saveFile(String(THUMBS) + name, fb->buf, fb->len)) Serial.printf("thumb %u bytes\n", (unsigned)fb->len);
  if (fb) esp_camera_fb_return(fb);
  return name;
}

// --- web gallery
// trust boundary: only flat names of our own shape, no paths
bool okName(const String &n) {
  if (n.length() < 5 || n.length() > 40 || !n.endsWith(".jpg")) return false;
  for (unsigned i = 0; i < n.length() - 4; i++)
    if (!isalnum((unsigned char)n[i]) && n[i] != '_' && n[i] != '-') return false;
  return true;
}

void sendList() {
  char head[48];
  snprintf(head, sizeof head, "{\"sd\":%s,\"free\":%llu,\"files\":[", onSD ? "true" : "false", (unsigned long long)freeBytes());
  srv.setContentLength(CONTENT_LENGTH_UNKNOWN);
  srv.send(200, "application/json", "");
  srv.sendContent(head);
  File dir = store.open("/");
  bool first = true;
  for (File f = dir.openNextFile(); f; f = dir.openNextFile()) {
    String n = f.name();
    if (f.isDirectory() || !okName(n)) continue;
    srv.sendContent(String(first ? "" : ",") + "{\"n\":\"" + n + "\",\"s\":" + String((unsigned)f.size()) + "}");
    first = false;
  }
  srv.sendContent("]}");
  srv.sendContent("");  // end chunked response
}

void sendJpeg(const String &dir) {
  String n = srv.arg("n");
  String path = dir + "/" + n;
  if (!okName(n) || !store.exists(path)) { srv.send(404, "text/plain", "not found"); return; }
  File f = store.open(path);
  if (srv.hasArg("dl")) srv.sendHeader("Content-Disposition", "attachment; filename=" + n);
  srv.sendHeader("Cache-Control", "max-age=86400");  // names never repeat, so the phone can keep them
  srv.streamFile(f, "image/jpeg");
  f.close();
}

// photo names from the request ("n" = comma-separated list), or every photo when there is none
std::vector<String> chosen(uint64_t *total = nullptr) {
  std::vector<String> names;  // collected first: don't read or delete files while iterating the directory
  if (total) *total = 0;
  if (srv.hasArg("n")) {
    String list = srv.arg("n") + ",";
    for (int a = 0, b; (b = list.indexOf(',', a)) >= 0; a = b + 1) {
      String n = list.substring(a, b);
      if (!okName(n) || !store.exists("/" + n)) continue;
      names.push_back(n);
      if (total) { File f = store.open("/" + n); *total += f.size() + 200; }
    }
    return names;
  }
  File dir = store.open("/");
  for (File f = dir.openNextFile(); f; f = dir.openNextFile())
    if (!f.isDirectory() && okName(f.name())) { names.push_back(f.name()); if (total) *total += f.size() + 200; }
  return names;
}

// chosen photos as one .zip, streamed file by file (see zipstream.h)
void sendZip() {
  uint64_t total;
  std::vector<String> names = chosen(&total);
  if (total > 0xFFF00000ULL || names.size() > 65000) { srv.send(507, "text/plain", "too many photos for one zip"); return; }

  srv.setContentLength(CONTENT_LENGTH_UNKNOWN);
  srv.sendHeader("Content-Disposition", "attachment; filename=kukucs.zip");
  srv.send(200, "application/zip", "");
  ZipStream z([](const uint8_t *b, size_t n) { srv.sendContent((const char *)b, n); }, esp_rom_crc32_le);
  static uint8_t buf[4096];
  for (auto &n : names) {
    if (!srv.client().connected()) return;  // phone gave up: stop reading the card
    File f = store.open("/" + n);
    if (!f) continue;
    time_t t = f.getLastWrite();
    z.begin(n.c_str(), t > 315532800 ? t + tzMin * 60 : 0);  // file times are UTC; zip wants local
    for (int r; (r = f.read(buf, sizeof buf)) > 0;) z.data(buf, r);
    z.end();
    f.close();
  }
  z.finish();
  srv.sendContent("");  // end chunked response
}

void removePhoto(const String &n) {
  store.remove("/" + n);
  store.remove(String(THUMBS) + "/" + n);
}

void handleDel() {  // "n" = one name or a comma-separated list
  if (!srv.hasArg("n")) { srv.send(400, "text/plain", "no names"); return; }
  for (auto &n : chosen()) removePhoto(n);
  srv.send(204);
}

void handleTime() {
  long long t = atoll(srv.arg("t").c_str());
  long tz = srv.arg("tz").toInt();
  if (t > 1700000000LL && tz >= -720 && tz <= 840) {
    timeval tv = {(time_t)t, 0};
    settimeofday(&tv, nullptr);
    tzMin = tz;
  }
  srv.send(204);
}

// remote shutter from the gallery: same as a short press while the hotspot runs
void handleShoot() {
  String path = initCamera() ? takePhoto() : "";
  cameraOff();
  if (path.isEmpty()) { srv.send(500, "text/plain", "photo failed"); return; }
  ledFlash(100);
  srv.send(200, "application/json", "{\"n\":\"" + path.substring(1) + "\"}");
}

void route(const char *path, HTTPMethod m, void (*fn)()) {
  srv.on(path, m, [fn]() { lastReq = millis(); fn(); });  // only real use keeps the hotspot awake
}

bool copyToCard(const String &path) {
  static uint8_t buf[4096];
  File in = LittleFS.open(path);
  if (!in) return false;
  File out = SD.open(path, FILE_WRITE);
  if (!out) return false;
  size_t total = 0;
  for (int r; (r = in.read(buf, sizeof buf)) > 0;) total += out.write(buf, r);
  bool ok = total == in.size();
  out.close();
  in.close();
  if (!ok) SD.remove(path);
  return ok;
}

// photos taken while no card was in move to the card once there is one
void moveToCard() {
  if (!onSD) return;
  std::vector<String> names;
  File dir = LittleFS.open("/");
  for (File f = dir.openNextFile(); f; f = dir.openNextFile())
    if (!f.isDirectory() && okName(f.name())) names.push_back(f.name());
  dir.close();
  for (auto &n : names) {
    if (!copyToCard("/" + n)) { Serial.printf("card full? kept %s in flash\n", n.c_str()); break; }
    copyToCard(String(THUMBS) + "/" + n);  // a missing thumbnail only costs the gallery a bit of speed
    LittleFS.remove("/" + n);  // only after the photo is safely on the card
    LittleFS.remove(String(THUMBS) + "/" + n);
    Serial.printf("moved %s to the card\n", n.c_str());
  }
}

void startHotspot() {
  cameraOff();  // not needed for browsing
  moveToCard();
  while (pressed()) delay(10);  // let go of the long press first
  if (!WiFi.softAP(AP_SSID, AP_PASS)) { Serial.println("hotspot failed to start"); sleepNow(); return; }
  Serial.printf("wifi mode %d, ssid '%s', channel %d\n", (int)WiFi.getMode(), WiFi.softAPSSID().c_str(), (int)WiFi.channel());
  dns.start(53, "*", WiFi.softAPIP());  // every name -> us, so phones pop the gallery up by themselves
  srv.begin();
  lastReq = lastPhone = millis();
  mode = HOTSPOT;
  Serial.printf("hotspot %s up at %s\n", AP_SSID, WiFi.softAPIP().toString().c_str());
}

// --- USB drive (SD builds): the PC reads and writes the card's sectors directly
#ifdef USB_DRIVE
volatile bool usbEjected = false;

int32_t mscRead(uint32_t lba, uint32_t off, void *buf, uint32_t size) {
  if (off % 512 || size % 512) return -1;
  for (uint32_t i = 0; i < size / 512; i++)
    if (!SD.readRAW((uint8_t *)buf + i * 512, lba + off / 512 + i)) return -1;
  return size;
}

int32_t mscWrite(uint32_t lba, uint32_t off, uint8_t *buf, uint32_t size) {
  if (off % 512 || size % 512) return -1;
  for (uint32_t i = 0; i < size / 512; i++)
    if (!SD.writeRAW(buf + i * 512, lba + off / 512 + i)) return -1;
  return size;
}

bool mscStartStop(uint8_t power, bool start, bool eject) {
  if (eject && !start) usbEjected = true;
  return true;
}

bool pcConnected() { return tud_mounted() && !tud_suspended(); }  // unplugged on battery = bus goes quiet

void startUsbDrive() {
  cameraOff();
  moveToCard();
  if (SD.sectorSize() != 512) { Serial.println("card sector size not 512"); sleepNow(); return; }
  msc.vendorID("kukucs");
  msc.productID("camera");
  msc.productRevision("1.0");
  msc.onRead(mscRead);
  msc.onWrite(mscWrite);
  msc.onStartStop(mscStartStop);
  msc.isWritable(true);
  msc.begin(SD.numSectors(), 512);
  msc.mediaPresent(true);
  usbEjected = false;
  mode = USBDRIVE;
  Serial.println("USB drive");
}
#endif

// the button-press path: photo + sleep, hotspot, or USB drive (then loop() serves it)
void wake() {
  uint32_t t0 = millis();
  bool cam = initCamera();  // ~0.5 s, overlaps with timing the press
  while (pressed() && millis() - t0 < LONG_MS) delay(10);
  if (pressed()) { startHotspot(); return; }
#ifdef USB_DRIVE
#ifdef FAKE_BTN
  bool drive = fakeDrive;
  fakeDrive = false;
#else
  while (!pcConnected() && millis() - t0 < USB_WAIT_MS) delay(10);  // a PC needs a moment to set us up
  bool drive = pcConnected();
#endif
  if (drive && onSD) { startUsbDrive(); return; }  // no card: nothing to show, take a photo instead
#endif
  if (cam) takePhoto();
  ledFlash(100);  // shutter confirmation
  sleepNow();
}

void setup() {
  Serial.begin(115200);
  rtc_gpio_deinit(BTN);  // pin is still RTC-muxed from sleep
  pinMode(BTN, INPUT_PULLUP);  // before sleepNow(), which reads the button

  // log what the hotspot sees: a phone joining, getting an address, leaving (with the reason code)
  WiFi.onEvent([](WiFiEvent_t e, WiFiEventInfo_t i) {
    if (e == ARDUINO_EVENT_WIFI_AP_STACONNECTED) Serial.println("wifi: phone joined");
    else if (e == ARDUINO_EVENT_WIFI_AP_STAIPASSIGNED) Serial.printf("wifi: phone got IP %s\n", IPAddress(i.wifi_ap_staipassigned.ip.addr).toString().c_str());
    else if (e == ARDUINO_EVENT_WIFI_AP_STADISCONNECTED) Serial.printf("wifi: phone left, reason %d\n", (int)i.wifi_ap_stadisconnected.reason);
  });
  route("/", HTTP_GET, []() { srv.send(200, "text/html", PAGE); });
  route("/api/list", HTTP_GET, sendList);
  route("/f", HTTP_GET, []() { sendJpeg(""); });
  route("/t", HTTP_GET, []() { sendJpeg(THUMBS); });
  route("/api/zip", HTTP_ANY, sendZip);  // GET = all, POST with "n" = selection
  route("/api/del", HTTP_POST, handleDel);
  route("/api/time", HTTP_POST, handleTime);
  route("/api/shoot", HTTP_POST, handleShoot);
  srv.onNotFound([]() {  // phones probe some URL to detect a login page: send them to the gallery
    srv.sendHeader("Location", "http://192.168.4.1/");
    srv.send(302, "text/plain", "");
  });

  if (!LittleFS.begin(true)) Serial.println("internal flash mount failed");
  onSD = SD.begin(LED) && SD.cardType() != CARD_NONE;  // FAT32 only: this core has no exFAT
  digitalWrite(LED, HIGH);  // LED off (= card not selected)
  pinMode(LED, OUTPUT);
  Serial.printf("storage: %s\n", onSD ? "SD card" : "internal flash (no card)");
  store.mkdir(THUMBS);

  if (esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_EXT0) wake();
  else sleepNow();  // power-on/reset: just sleep
}

void loop() {
#ifdef FAKE_BTN
  int c = Serial.read();
  if (mode == SLEEPING) {
    if (c == 's' || c == 'l' || c == 'd' || pressed()) {  // real button works here too
      if (c == 'l') fakeUntil = millis() + LONG_MS + 500;
      fakeDrive = c == 'd';
      wake();
    }
    delay(10);
    return;
  }
  if (c == 'l') fakeUntil = millis() + LONG_MS + 500;
  if (c == 's') fakeUntil = millis() + 200;
#endif
  if (mode == HOTSPOT) {
    dns.processNextRequest();
    srv.handleClient();
    if (WiFi.softAPgetStationNum() > 0) lastPhone = millis();
    if (millis() - lastReq > IDLE_MS || millis() - lastPhone > NOBODY_MS) { sleepNow(); return; }
    static uint32_t lastBlink = 0;  // "hotspot is on" heartbeat; safe here, no request is using the card
    if (millis() - lastBlink > 2000) { lastBlink = millis(); ledFlash(40); }
  }
#ifdef USB_DRIVE
  if (mode == USBDRIVE) {
    static uint32_t goneAt = 0;  // unplugged (or PC asleep) for 2 s, or ejected -> sleep
    if (pcConnected()) goneAt = 0;
    else if (!goneAt) goneAt = millis();
    if (usbEjected || (goneAt && millis() - goneAt > 2000)) { goneAt = 0; sleepNow(); return; }
  }
#endif

  // long press -> sleep; short press in hotspot mode -> photo, so a forgotten hotspot never blocks the shutter
  // (not as a USB drive: the PC owns the card then, writing to it too could corrupt it)
  static uint32_t downAt = 0;
  if (pressed()) {
    if (!downAt) downAt = millis();
    else if (millis() - downAt > LONG_MS) { downAt = 0; sleepNow(); return; }
  } else if (downAt) {
    bool tap = millis() - downAt > 30;  // debounce
    downAt = 0;
    if (tap && mode == HOTSPOT) {
      if (initCamera()) takePhoto();
      cameraOff();
      ledFlash(100);
      lastReq = millis();
    }
  }
  delay(2);
}
