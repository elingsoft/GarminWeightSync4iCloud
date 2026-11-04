# -*- coding: utf-8 -*-
"""Pure-Python FIT writer for a weight-scale file (weight only, stdlib only).

Produces a minimal but valid FIT file:
  file_id message (type = weight) + one weight_scale message (timestamp + weight).
Verified by round-tripping through fitparse. Garmin Connect import of the
resulting file is verified live on the first real weigh-in; if Connect ever
rejects it, the fallback is the JSON weight API (same data, different carrier).
"""
import struct
import datetime

GARMIN_EPOCH_OFFSET = 631065600  # 1989-12-31 00:00:00 UTC in Unix seconds

_CRC_TABLE = [
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
]


def fit_crc(data: bytes, crc: int = 0) -> int:
    for b in data:
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[b & 0xF]
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[(b >> 4) & 0xF]
    return crc


def _def_message(local_num: int, global_num: int, fields) -> bytes:
    """fields: list of (field_number, size, base_type)."""
    out = bytearray()
    out.append(0x40 | local_num)  # definition message
    out.append(0)                  # reserved
    out.append(0)                  # little-endian architecture
    out += struct.pack("<H", global_num)
    out.append(len(fields))
    for num, size, btype in fields:
        out += bytes([num, size, btype])
    return bytes(out)


def build_weight_fit(when_utc: datetime.datetime, weight_kg: float) -> bytes:
    """when_utc: aware UTC datetime of the weigh-in. Returns FIT file bytes."""
    if when_utc.tzinfo is None:
        when_utc = when_utc.replace(tzinfo=datetime.timezone.utc)
    fit_ts = int(when_utc.timestamp()) - GARMIN_EPOCH_OFFSET
    weight_raw = int(round(weight_kg * 100))  # scale 100

    body = bytearray()
    # file_id (global 0), local 0: type(0, uint8 enum), manufacturer(1, uint16),
    # product(2, uint16), time_created(4, uint32 date_time)
    body += _def_message(0, 0, [(0, 1, 0x00), (1, 2, 0x84), (2, 2, 0x84), (4, 4, 0x86)])
    body += bytes([0x00])
    body += struct.pack("<BHHI", 9, 255, 0, fit_ts)  # type=weight, mfr=development
    # weight_scale (global 30), local 1: timestamp(253, uint32), weight(0, uint16)
    body += _def_message(1, 30, [(253, 4, 0x86), (0, 2, 0x84)])
    body += bytes([0x01])
    body += struct.pack("<IH", fit_ts, weight_raw)

    header12 = struct.pack("<BBHI", 14, 0x20, 2084, len(body)) + b".FIT"
    header = header12 + struct.pack("<H", fit_crc(header12))
    blob = header + bytes(body)
    blob += struct.pack("<H", fit_crc(blob))
    return blob


if __name__ == "__main__":
    import sys
    dt = datetime.datetime(2026, 11, 3, 7, 0, tzinfo=datetime.timezone.utc)
    blob = build_weight_fit(dt, 55.6)
    open("/tmp/test_weight.fit", "wb").write(blob)
    print("wrote", len(blob), "bytes")
