"""Minimal local-CASC reader for a World of Warcraft install.

Resolves a FileDataID to its decoded bytes straight out of the local install,
with no CDN access and no external tools:

    .build.info (pick build/product)
      -> build config (names the root + encoding files)
      -> encoding       (content key  -> encoded key)
      -> root           (file data id -> content key)
      -> local .idx     (encoded key  -> data.NNN archive + offset)
      -> BLTE decode    (zlib chunks)

This is a pure-Python port of the local-only path of TACTSharp's BuildInstance
(https://github.com/wowdev/TACTSharp, MIT), by way of the wowsims/mop db2tool
`tact` package. Keyless: encrypted ('E') BLTE chunks are left zero-filled, which
is exactly what the WDC5 reader's encrypted-section skip expects.
"""

from __future__ import annotations

import os
import struct
import zlib
from bisect import bisect_left
from dataclasses import dataclass


def _be32(b: bytes, off: int = 0) -> int:
    return (b[off] << 24) | (b[off + 1] << 16) | (b[off + 2] << 8) | b[off + 3]


# --------------------------------------------------------------------------- #
# .build.info / build config
# --------------------------------------------------------------------------- #

@dataclass
class AvailableBuild:
    build_config: str
    version: str
    product: str


def parse_build_info(path: str) -> list[AvailableBuild]:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    entries: list[AvailableBuild] = []
    header: dict[str, int] = {}
    for line in raw.replace("\r\n", "\n").split("\n"):
        if not line:
            continue
        parts = line.split("|")
        if parts[0].startswith("Branch!"):
            for i, col in enumerate(parts):
                header[col.split("!")[0]] = i
            continue

        def col(name: str) -> str:
            idx = header.get(name, -1)
            return parts[idx] if 0 <= idx < len(parts) else ""

        entries.append(AvailableBuild(col("Build Key"), col("Version"), col("Product")))
    if not entries:
        raise ValueError(f"{path}: no build entries found")
    return entries


def select_build(entries: list[AvailableBuild], product: str) -> AvailableBuild:
    for e in entries:
        if e.product == product:
            return e
    raise ValueError(f"product {product!r} not found in .build.info")


def build_number(version: str) -> int:
    parts = version.split(".")
    if len(parts) != 4:
        raise ValueError(f"invalid build version {version!r}")
    return int(parts[3])


def load_config(base_dir: str, hash_: str) -> dict[str, list[str]]:
    if len(hash_) != 32:
        raise ValueError(f"invalid config hash {hash_!r}")
    path = os.path.join(base_dir, "Data", "config", hash_[0:2], hash_[2:4], hash_)
    with open(path, "rb") as f:
        raw = f.read()
    if not raw or raw[0:1] != b"#":
        raise ValueError(f"{path}: config file is unreadable")
    values: dict[str, list[str]] = {}
    for line in raw.decode("utf-8").split("\n"):
        if "=" in line:
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip().split(" ")
    return values


# --------------------------------------------------------------------------- #
# local .idx indices + data.NNN archives
# --------------------------------------------------------------------------- #

_IDX_HEADER_SIZE = 40
_STORAGE_FRAME = 30  # per-record BLTE storage frame prefixed inside data.NNN


class _CascIndex:
    def __init__(self, raw: bytes):
        version = struct.unpack_from("<H", raw, 8)[0]
        if version != 7:
            raise ValueError(f"unsupported .idx version {version} (want 7)")
        self.entry_size_bytes = raw[12]
        self.entry_offset_bytes = raw[13]
        self.entry_key_bytes = raw[14]
        self.entry_size = self.entry_size_bytes + self.entry_offset_bytes + self.entry_key_bytes
        entries_size = struct.unpack_from("<I", raw, 32)[0]
        if _IDX_HEADER_SIZE + entries_size > len(raw):
            raise ValueError("entries block exceeds .idx file size")
        self.entries = raw[_IDX_HEADER_SIZE:_IDX_HEADER_SIZE + entries_size]
        self.count = len(self.entries) // self.entry_size
        self._keys = [self._key(i) for i in range(self.count)]  # sorted ascending

    def _key(self, i: int) -> bytes:
        o = i * self.entry_size
        return self.entries[o:o + self.entry_key_bytes]

    def lookup(self, ekey: bytes):
        """Return (archive_offset, size, archive_index) or None."""
        needle = ekey[:self.entry_key_bytes]
        i = bisect_left(self._keys, needle)
        if i >= self.count or self._keys[i] != needle:
            return None
        o = i * self.entry_size
        entry = self.entries[o:o + self.entry_size]
        k = self.entry_key_bytes
        index_high = entry[k]
        index_low = struct.unpack_from(">I", entry, k + 1)[0]
        size = struct.unpack_from("<I", entry, k + 5)[0] - _STORAGE_FRAME
        archive_index = (index_high << 2) | ((index_low & 0xC0000000) >> 30)
        archive_offset = (index_low & 0x3FFFFFFF) + _STORAGE_FRAME
        return archive_offset, size, archive_index


def _bucket_for_ekey(ekey: bytes) -> int:
    i = 0
    for b in ekey[:9]:
        i ^= b
    return (i & 0xF) ^ (i >> 4)


class _CascStore:
    def __init__(self, base_dir: str):
        self.data_dir = os.path.join(base_dir, "Data", "data")
        highest: dict[int, int] = {}
        for name in os.listdir(self.data_dir):
            if not name.endswith(".idx") or "tempfile" in name:
                continue
            stem = name[:-4]
            if len(stem) != 10:
                continue
            try:
                bucket = int(stem[0:2], 16)
                version = int(stem[2:], 16)
            except ValueError:
                continue
            if bucket not in highest or version > highest[bucket]:
                highest[bucket] = version
        if not highest:
            raise ValueError(f"no .idx files found in {self.data_dir}")
        self.buckets: dict[int, _CascIndex] = {}
        for bucket, version in highest.items():
            path = os.path.join(self.data_dir, f"{bucket:02x}{version:08x}.idx")
            with open(path, "rb") as f:
                self.buckets[bucket] = _CascIndex(f.read())

    def read_ekey(self, ekey: bytes) -> bytes:
        bucket = _bucket_for_ekey(ekey)
        idx = self.buckets.get(bucket)
        if idx is None:
            raise KeyError(f"no .idx bucket {bucket:02x}")
        info = idx.lookup(ekey)
        if info is None:
            raise KeyError(f"ekey {ekey.hex()} not found in local CASC indices")
        offset, size, archive_index = info
        path = os.path.join(self.data_dir, f"data.{archive_index:03d}")
        with open(path, "rb") as f:
            f.seek(offset)
            buf = f.read(size)
        if len(buf) != size:
            raise IOError(f"short read from {path} @{offset}+{size}")
        return buf


# --------------------------------------------------------------------------- #
# BLTE
# --------------------------------------------------------------------------- #

def blte_decode(data: bytes, total_decomp_size: int = 0) -> bytes:
    if len(data) < 8 or data[:4] != b"BLTE":
        raise ValueError("invalid BLTE header")
    header_size = _be32(data, 4)

    if header_size == 0:
        mode = data[8]
        payload = data[9:]
        if mode == ord("N"):
            return payload if total_decomp_size == 0 else payload[:total_decomp_size]
        if total_decomp_size == 0:
            raise ValueError("total_decomp_size required for single non-normal BLTE block")
        out = bytearray(total_decomp_size)
        _handle_block(mode, payload, out, 0, total_decomp_size)
        return bytes(out)

    if data[8] != 0xF:
        raise ValueError(f"unexpected BLTE table format 0x{data[8]:x}")
    chunk_count = (data[9] << 16) | (data[10] << 8) | data[11]
    info_start = 12
    block_info_size = 24

    if total_decomp_size == 0:
        o = info_start + 4
        for _ in range(chunk_count):
            total_decomp_size += _be32(data, o)
            o += block_info_size

    out = bytearray(total_decomp_size)
    info_off = info_start
    comp_off = header_size
    decomp_off = 0
    for chunk in range(chunk_count):
        comp_size = _be32(data, info_off)
        decomp_size = _be32(data, info_off + 4)
        if comp_off + comp_size > len(data) or decomp_off + decomp_size > len(out):
            raise ValueError(f"BLTE chunk {chunk} out of bounds")
        _handle_block(data[comp_off], data[comp_off + 1:comp_off + comp_size],
                      out, decomp_off, decomp_size)
        info_off += block_info_size
        comp_off += comp_size
        decomp_off += decomp_size
    return bytes(out)


def _handle_block(mode: int, comp: bytes, out: bytearray, out_off: int, out_len: int) -> None:
    if mode == ord("N"):
        out[out_off:out_off + out_len] = comp[:out_len]
    elif mode == ord("Z"):
        dec = zlib.decompress(comp)
        out[out_off:out_off + out_len] = dec[:out_len]
    elif mode == ord("E"):
        # Keyless: leave the output range zero-filled.
        return
    elif mode == ord("F"):
        raise ValueError("BLTE frame ('F') decompression not implemented")
    else:
        raise ValueError(f"invalid BLTE chunk mode {chr(mode)!r}")


# --------------------------------------------------------------------------- #
# encoding table (CKey -> EKey)
# --------------------------------------------------------------------------- #

class _Encoding:
    def __init__(self, data: bytes):
        if len(data) < 22 or data[0:2] != b"EN":
            raise ValueError("invalid encoding file magic")
        if data[2] != 1:
            raise ValueError(f"unsupported encoding version {data[2]}")
        self.data = data
        self.ckey_size = data[3]
        self.ekey_size = data[4]
        self.page_size = ((data[5] << 8) | data[6]) * 1024
        self.page_count = _be32(data, 9)
        espec_block_size = _be32(data, 0x12)
        self.header_off = 22 + espec_block_size
        self.pages_off = self.header_off + self.page_count * (self.ckey_size + 0x10)
        if self.pages_off + self.page_count * self.page_size > len(data):
            raise ValueError("encoding ckey pages exceed file size")
        self._entry = self.ckey_size + 0x10
        self._page_keys = [
            self.data[self.header_off + i * self._entry:
                      self.header_off + i * self._entry + self.ckey_size]
            for i in range(self.page_count)
        ]

    def find(self, ckey: bytes):
        """Return (ekey, decoded_size) or None."""
        # last page whose first key <= ckey
        lo, hi = 0, self.page_count
        while lo < hi:
            mid = (lo + hi) // 2
            if self._page_keys[mid] <= ckey:
                lo = mid + 1
            else:
                hi = mid
        page_index = lo - 1
        if page_index < 0:
            return None
        page = self.data[self.pages_off + page_index * self.page_size:
                         self.pages_off + (page_index + 1) * self.page_size]
        cs, es = self.ckey_size, self.ekey_size
        pos = 0
        while pos + 1 + 5 + cs <= len(page):
            key_count = page[pos]
            rec_len = 5 + cs + es * key_count
            if pos + 1 + rec_len > len(page):
                break
            rec = page[pos + 1:pos + 1 + rec_len]
            if key_count != 0 and rec[5:5 + cs] == ckey:
                size = (rec[0] << 32) | (rec[1] << 24) | (rec[2] << 16) | (rec[3] << 8) | rec[4]
                return rec[5 + cs:5 + cs + es], size
            pos += 1 + rec_len
        return None


# --------------------------------------------------------------------------- #
# root table (FileDataID -> CKey)
# --------------------------------------------------------------------------- #

_LOCALE_ENUS = 0x2
_LOCALE_ALL_WOW = (0x2 | 0x4 | 0x10 | 0x20 | 0x40 | 0x80 | 0x100 | 0x200
                   | 0x1000 | 0x2000 | 0x4000 | 0x8000 | 0x10000)
_CONTENT_LOW_VIOLENCE = 0x80
_CONTENT_NO_NAMES = 0x10000000
_TSFM_MAGIC = 0x4D465354  # "TSFM" little-endian


def _parse_root(data: bytes) -> dict[int, bytes]:
    by_fdid: dict[int, bytes] = {}
    if len(data) < 12:
        raise ValueError("root file too small")

    new_root = False
    df_version = 0
    offset = 0
    if struct.unpack_from("<I", data, 0)[0] == _TSFM_MAGIC:
        new_root = True
        offset = 12
        total_files = struct.unpack_from("<I", data, 4)[0]
        named_files = struct.unpack_from("<I", data, 8)[0]
        if named_files in (1, 2):
            # Post-10.1.7 header: [magic, headerSize, dfVersion, ...]
            df_version = named_files
            offset = total_files  # headerSize

    n = len(data)
    while offset < n:
        count = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        if df_version == 2:
            locale_flags = struct.unpack_from("<I", data, offset)[0]
            unk = struct.unpack_from("<I", data, offset + 4)[0]
            unk2 = struct.unpack_from("<I", data, offset + 8)[0]
            unk_byte = data[offset + 12]
            offset += 13
            content_flags = unk | unk2 | (unk_byte << 17)
        else:
            content_flags = struct.unpack_from("<I", data, offset)[0]
            locale_flags = struct.unpack_from("<I", data, offset + 4)[0]
            offset += 8

        locale_skip = (locale_flags & _LOCALE_ALL_WOW) != _LOCALE_ALL_WOW and (locale_flags & _LOCALE_ENUS) == 0
        content_skip = (content_flags & _CONTENT_LOW_VIOLENCE) != 0
        skip_chunk = locale_skip or content_skip

        separate_lookup = new_root
        do_lookup = (not new_root) or (content_flags & _CONTENT_NO_NAMES) == 0
        size_fdid, size_chash, size_lookup = 4, 16, 8
        stride_chash = size_chash if separate_lookup else size_chash + size_lookup

        offset_fdid = offset
        offset_chash = offset_fdid + count * size_fdid
        block_size = count * (size_fdid + size_chash)
        if do_lookup:
            block_size += count * size_lookup
        if offset + block_size > n:
            raise ValueError(f"truncated root block at {offset}")

        if not skip_chunk:
            file_data_index = 0
            oc = offset_chash
            of = offset_fdid
            for _ in range(count):
                fdid_delta = struct.unpack_from("<I", data, of)[0]
                of += size_fdid
                fdid = file_data_index + fdid_delta
                file_data_index = fdid + 1
                if fdid not in by_fdid:
                    by_fdid[fdid] = data[oc:oc + size_chash]
                oc += stride_chash

        offset += block_size
    return by_fdid


# --------------------------------------------------------------------------- #
# Build: ties it all together
# --------------------------------------------------------------------------- #

class Build:
    def __init__(self, base_dir: str, product: str):
        entries = parse_build_info(os.path.join(base_dir, ".build.info"))
        self.entry = select_build(entries, product)
        self.build_number = build_number(self.entry.version)

        cfg = load_config(base_dir, self.entry.build_config)
        self._store = _CascStore(base_dir)

        enc_keys = cfg.get("encoding")
        if not enc_keys or len(enc_keys) < 2:
            raise ValueError("no encoding key pair in build config")
        encoding_raw = blte_decode(self._store.read_ekey(bytes.fromhex(enc_keys[1])))
        self._encoding = _Encoding(encoding_raw)

        root_key = cfg.get("root")
        if not root_key:
            raise ValueError("no root key in build config")
        root_raw = self.open_by_ckey(bytes.fromhex(root_key[0]))
        self._root = _parse_root(root_raw)

    def open_by_ckey(self, ckey: bytes) -> bytes:
        found = self._encoding.find(ckey)
        if found is None:
            raise KeyError(f"ckey {ckey.hex()} not found in encoding")
        ekey, decoded_size = found
        return blte_decode(self._store.read_ekey(ekey), decoded_size)

    def open_by_fdid(self, fdid: int) -> bytes:
        ckey = self._root.get(fdid)
        if ckey is None:
            raise KeyError(f"fdid {fdid} not found in root")
        return self.open_by_ckey(ckey)
