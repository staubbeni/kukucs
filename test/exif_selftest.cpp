// Host check for src/exif.h. Build and run (any C++17 compiler):
//   c++ -std=c++17 test/exif_selftest.cpp -o /tmp/et && /tmp/et in.jpg out.jpg
// then check: python3 -c "from PIL import Image; im=Image.open('out.jpg'); im.load(); print(im.getexif()[0x112])"
#include <cassert>
#include <cstdio>
#include <vector>
#include "../src/exif.h"

int main(int argc, char **argv) {
  // where to insert
  const uint8_t withJfif[] = {0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 'J', 'F', 'I', 'F', 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0xFF, 0xDB};
  assert(exifInsertAt(withJfif, sizeof withJfif) == 20);                        // right after the 16-byte JFIF segment
  const uint8_t noJfif[] = {0xFF, 0xD8, 0xFF, 0xDB, 0x00, 0x43, 0, 0};
  assert(exifInsertAt(noJfif, sizeof noJfif) == 2);                             // straight after the SOI
  const uint8_t notJpeg[] = {'G', 'I', 'F', '8', '9', 'a', 0, 0};
  assert(exifInsertAt(notJpeg, sizeof notJpeg) == 0);
  const uint8_t lying[] = {0xFF, 0xD8, 0xFF, 0xE0, 0xFF, 0xFF, 0, 0};          // header claims more than we have
  assert(exifInsertAt(lying, sizeof lying) == 2);

  // the segment itself
  uint8_t seg[EXIF_SEG_LEN];
  exifSegment(8, seg);
  assert(seg[0] == 0xFF && seg[1] == 0xE1 && ((seg[2] << 8 | seg[3]) == EXIF_SEG_LEN - 2) && seg[28] == 8 && seg[20] == 0x12 && seg[21] == 0x01);

  if (argc < 3) { std::puts("insert logic OK (give in.jpg out.jpg to also write a tagged file)"); return 0; }
  FILE *f = fopen(argv[1], "rb");
  std::vector<uint8_t> in;
  for (int c; (c = fgetc(f)) != EOF;) in.push_back((uint8_t)c);
  fclose(f);
  size_t at = exifInsertAt(in.data(), in.size());
  assert(at);
  FILE *o = fopen(argv[2], "wb");
  fwrite(in.data(), 1, at, o);
  fwrite(seg, 1, sizeof seg, o);
  fwrite(in.data() + at, 1, in.size() - at, o);
  fclose(o);
  std::puts("insert logic OK, wrote tagged file");
  return 0;
}
