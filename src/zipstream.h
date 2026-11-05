// Streaming .zip writer, no compression (JPEGs don't shrink). Each file's CRC and size go in a data
// descriptor after its data, so nothing has to be known up front and the whole zip never sits in memory.
// shortcut: no zip64, so the archive must stay under 4 GB / 65535 files; upgrade if photo sets get that big.
#pragma once
#include <cstdint>
#include <ctime>
#include <functional>
#include <string>
#include <vector>

class ZipStream {
 public:
  using Sink = std::function<void(const uint8_t *, size_t)>;
  using Crc = uint32_t (*)(uint32_t, const uint8_t *, uint32_t);  // zlib-style: crc(0, ...) then chain

  ZipStream(Sink out, Crc crc) : out_(out), crc_(crc) {}

  void begin(const std::string &name, time_t localTime) {
    cur_ = {name, 0, 0, pos_, 0, 0};
    dos(localTime, cur_.time, cur_.date);
    u32(0x04034b50); u16(20); u16(8); u16(0);  // version 2.0, flag 3: sizes follow the data, stored
    u16(cur_.time); u16(cur_.date); u32(0); u32(0); u32(0);
    u16(name.size()); u16(0); raw((const uint8_t *)name.data(), name.size());
  }

  void data(const uint8_t *b, size_t n) {
    cur_.crc = crc_(cur_.crc, b, n);
    cur_.size += n;
    flush();
    out_(b, n);  // big file chunks go straight through
    pos_ += n;
  }

  void end() {
    u32(0x08074b50); u32(cur_.crc); u32(cur_.size); u32(cur_.size);
    files_.push_back(cur_);
  }

  void finish() {
    uint32_t cd = pos_;
    for (auto &e : files_) {
      u32(0x02014b50); u16(20); u16(20); u16(8); u16(0); u16(e.time); u16(e.date);
      u32(e.crc); u32(e.size); u32(e.size); u16(e.name.size()); u16(0); u16(0); u16(0); u16(0); u32(0);
      u32(e.off); raw((const uint8_t *)e.name.data(), e.name.size());
    }
    uint32_t cdSize = pos_ - cd;
    u32(0x06054b50); u16(0); u16(0); u16(files_.size()); u16(files_.size()); u32(cdSize); u32(cd); u16(0);
    flush();
  }

 private:
  struct Entry { std::string name; uint32_t crc, size, off; uint16_t time, date; };
  Sink out_;
  Crc crc_;
  Entry cur_;
  std::vector<Entry> files_;
  uint32_t pos_ = 0;
  uint8_t buf_[256];
  size_t n_ = 0;

  void flush() { if (n_) out_(buf_, n_); n_ = 0; }
  void raw(const uint8_t *b, size_t n) {  // headers are small: batch them so the sink isn't hit per byte
    for (size_t i = 0; i < n; i++) { if (n_ == sizeof buf_) flush(); buf_[n_++] = b[i]; }
    pos_ += n;
  }
  void u16(uint16_t v) { uint8_t b[2] = {uint8_t(v), uint8_t(v >> 8)}; raw(b, 2); }
  void u32(uint32_t v) { uint8_t b[4] = {uint8_t(v), uint8_t(v >> 8), uint8_t(v >> 16), uint8_t(v >> 24)}; raw(b, 4); }

  static void dos(time_t t, uint16_t &time, uint16_t &date) {
    struct tm tm;
    gmtime_r(&t, &tm);  // t is already local time
    if (tm.tm_year < 80) { time = 0; date = (1 << 5) | 1; return; }  // before 1980 (clock never set): 1980-01-01
    time = (tm.tm_hour << 11) | (tm.tm_min << 5) | (tm.tm_sec / 2);
    date = ((tm.tm_year - 80) << 9) | ((tm.tm_mon + 1) << 5) | tm.tm_mday;
  }
};
