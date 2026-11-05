// Host check for src/zipstream.h:  g++ -std=c++17 test/zip_selftest.cpp -lz -o /tmp/zt && /tmp/zt /tmp/t.zip
// then: python3 -c "import zipfile; z=zipfile.ZipFile('/tmp/t.zip'); assert z.testzip() is None; print(z.infolist()[0].date_time)"
#include <cassert>
#include <cstdio>
#if __has_include(<zlib.h>)
#include <zlib.h>
#else
#include ZCRC_H
#endif
#include "../src/zipstream.h"

static uint32_t zcrc(uint32_t c, const uint8_t *b, uint32_t n) { return crc32(c, b, n); }

int main(int argc, char **argv) {
  FILE *f = fopen(argv[1], "wb");
  ZipStream z([f](const uint8_t *b, size_t n) { fwrite(b, 1, n, f); }, zcrc);
  std::string big(10000, 'x');
  for (size_t i = 0; i < big.size(); i++) big[i] = char(i * 31 + 7);
  z.begin("2026-11-04_191502.jpg", 1793819702);  // 2026-11-04 19:15:02
  z.data((const uint8_t *)big.data(), 4096);      // in chunks, like the firmware
  z.data((const uint8_t *)big.data() + 4096, big.size() - 4096);
  z.end();
  z.begin("IMG_00001.jpg", 0);                    // clock never set
  z.data((const uint8_t *)"hello", 5);
  z.end();
  z.begin("empty.jpg", 0);
  z.end();
  z.finish();
  fclose(f);
  return 0;
}
