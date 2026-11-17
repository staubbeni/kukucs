// Minimal EXIF segment that carries only the orientation tag. Inserted into a JPEG, it makes viewers turn the
// picture (phone galleries, browsers, PC viewers), so the camera needs no pixel work.
// Orientation: 1 = as is, 3 = 180 degrees, 6 = quarter turn clockwise, 8 = quarter turn counter-clockwise.
#pragma once
#include <cstddef>
#include <cstdint>

static const size_t EXIF_SEG_LEN = 36;

inline void exifSegment(uint8_t orientation, uint8_t out[EXIF_SEG_LEN]) {
  const uint8_t seg[EXIF_SEG_LEN] = {
      0xFF, 0xE1, 0x00, 0x22,                          // APP1 marker, length 34 (without the marker)
      'E', 'x', 'i', 'f', 0, 0,
      'I', 'I', 0x2A, 0x00, 0x08, 0x00, 0x00, 0x00,    // TIFF header, little endian, first IFD at offset 8
      0x01, 0x00,                                      // one entry
      0x12, 0x01, 0x03, 0x00, 0x01, 0x00, 0x00, 0x00,  // tag 0x0112 (Orientation), SHORT, count 1
      orientation, 0x00, 0x00, 0x00,                   // the value
      0x00, 0x00, 0x00, 0x00};                         // no further IFD
  for (size_t i = 0; i < EXIF_SEG_LEN; i++) out[i] = seg[i];
}

// Where the segment goes: after the SOI and the JFIF header the camera writes. Returns 0 if this is not a JPEG.
inline size_t exifInsertAt(const uint8_t *jpg, size_t len) {
  if (len < 4 || jpg[0] != 0xFF || jpg[1] != 0xD8) return 0;
  if (len > 6 && jpg[2] == 0xFF && jpg[3] == 0xE0) {
    size_t at = 4 + ((size_t)jpg[4] << 8 | jpg[5]);  // SOI + marker + length field (which includes itself)
    if (at <= len) return at;
  }
  return 2;
}
