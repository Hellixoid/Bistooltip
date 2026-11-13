"""WDC5 .db2 decoder.

Parses the WDC5 container (the DB2 format used by WoW 11.x / MoP-Classic 5.5.x
clients) and decodes records into {column_name: value} dicts shaped by a
WoWDBDefs version block.

Pure-Python port of DBCD.IO's WDC5Reader + row decoding (MIT), via the
wowsims/mop db2tool `wdc` package. Keyless: encrypted sections (zero-filled by
the BLTE layer) are skipped, exactly as upstream does.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from . import dbd

WDC5_MAGIC = b"WDC5"

FLAG_SPARSE = 0x1
FLAG_SECONDARY_KEY = 0x2
FLAG_INDEX = 0x4

COMP_NONE = 0
COMP_IMMEDIATE = 1
COMP_COMMON = 2
COMP_PALLET = 3
COMP_PALLET_ARRAY = 4
COMP_SIGNED_IMMEDIATE = 5


class BitReader:
    __slots__ = ("data", "position", "offset")

    def __init__(self, data: bytes):
        self.data = data
        self.position = 0  # bits, relative to offset
        self.offset = 0    # bytes

    def read_uint32(self, num_bits: int) -> int:
        byteoff = self.offset + (self.position >> 3)
        v = int.from_bytes(self.data[byteoff:byteoff + 4].ljust(4, b"\x00"), "little")
        shift_l = (32 - num_bits - (self.position & 7)) & 31
        v = (v << shift_l) & 0xFFFFFFFF
        result = v >> ((32 - num_bits) & 31)
        self.position += num_bits
        return result

    def read_uint64(self, num_bits: int) -> int:
        byteoff = self.offset + (self.position >> 3)
        v = int.from_bytes(self.data[byteoff:byteoff + 8].ljust(8, b"\x00"), "little")
        shift_l = (64 - num_bits - (self.position & 7)) & 63
        v = (v << shift_l) & 0xFFFFFFFFFFFFFFFF
        result = v >> ((64 - num_bits) & 63)
        self.position += num_bits
        return result

    def read_value64_signed(self, num_bits: int) -> int:
        r = self.read_uint64(num_bits)
        sign = 1 << ((num_bits - 1) & 63)
        return (sign ^ r) - sign

    def read_cstring(self) -> str:
        out = bytearray()
        while True:
            n = self.read_uint32(8)
            if n == 0:
                break
            out.append(n)
        return out.decode("utf-8", "replace")


@dataclass
class _Section:
    tact_key_lookup: int
    file_offset: int
    num_records: int
    string_table_size: int
    offset_records_end: int
    index_data_size: int
    parent_lookup_size: int
    offset_map_id_count: int
    copy_table_count: int


@dataclass
class _ColumnMeta:
    record_offset: int
    size: int
    additional_data_size: int
    compression_type: int
    a: int
    b: int
    c: int


@dataclass
class _RawRow:
    offset: int
    position: int
    id: int
    ref_id: int
    record_index: int


@dataclass
class Table:
    records_count: int = 0
    fields_count: int = 0
    record_size: int = 0
    table_hash: int = 0
    layout_hash: str = ""
    min_index: int = 0
    flags: int = 0
    id_field_index: int = 0

    sections: list = field(default_factory=list)
    meta_bits: list = field(default_factory=list)      # per field: (bits, offset)
    column_meta: list = field(default_factory=list)
    pallet_data: list = field(default_factory=list)
    common_data: list = field(default_factory=list)
    string_table: dict = field(default_factory=dict)
    records_data: bytes = b""
    rows: list = field(default_factory=list)
    copy_data: list = field(default_factory=list)


class _Cursor:
    def __init__(self, buf: bytes):
        self.buf = buf
        self.pos = 0

    def take(self, n: int) -> bytes:
        if self.pos + n > len(self.buf):
            raise EOFError(f"need {n} bytes at {self.pos}, file is {len(self.buf)}")
        b = self.buf[self.pos:self.pos + n]
        self.pos += n
        return b

    def i32(self) -> int:
        return struct.unpack("<i", self.take(4))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.take(2))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self.take(8))[0]


def _pad(data: bytes) -> bytes:
    return data + b"\x00" * 8


def _read_string_table(dst: dict, data: bytes, base: int) -> None:
    if not data:
        return
    cur = 0
    for part in data.split(b"\x00"):
        if cur == len(data):
            break
        dst[base + cur] = part.decode("utf-8", "replace")
        cur += len(part) + 1


def read(buf: bytes) -> Table:
    if len(buf) < 200 or buf[:4] != WDC5_MAGIC:
        raise ValueError(f"unsupported DB2 format {buf[:4]!r} (only WDC5)")
    c = _Cursor(buf)
    c.pos = 4
    t = Table()

    c.u32()          # schema version
    c.take(128)      # schema string
    rc, fc, rs, sts, th, lh, mn, mx, loc = struct.unpack("<9i", c.take(36))
    t.records_count, t.fields_count, t.record_size = rc, fc, rs
    t.table_hash = th & 0xFFFFFFFF
    t.layout_hash = f"{lh & 0xFFFFFFFF:08X}"
    t.min_index = mn
    t.flags = c.u16()
    t.id_field_index = c.u16()
    total_fields, packed_off, lookup_cols, colmeta_size, common_size, pallet_size, sections_count = \
        struct.unpack("<7i", c.take(28))

    for _ in range(sections_count):
        tact = c.u64()
        (fo, nr, stsz, ore, idx, par, omi, cpy) = struct.unpack("<8i", c.take(32))
        t.sections.append(_Section(tact, fo, nr, stsz, ore, idx, par, omi, cpy))

    empty = sections_count == 0 or t.records_count == 0

    for _ in range(t.fields_count):
        try:
            b = c.take(4)
        except EOFError:
            if empty:
                break
            raise
        bits, off = struct.unpack("<hH", b)
        t.meta_bits.append((bits, off))

    for _ in range(t.fields_count):
        if empty and c.pos + 24 > len(buf):
            break
        ro = c.u16()
        sz = c.u16()
        ads = c.u32()
        ct = c.u32()
        a, bb, cc = c.i32(), c.i32(), c.i32()
        t.column_meta.append(_ColumnMeta(ro, sz, ads, ct, a, bb, cc))

    if empty:
        return t

    # pallet data
    t.pallet_data = [None] * len(t.column_meta)
    for i, cm in enumerate(t.column_meta):
        if cm.compression_type in (COMP_PALLET, COMP_PALLET_ARRAY):
            n = cm.additional_data_size // 4
            t.pallet_data[i] = [c.u32() for _ in range(n)]

    # common data
    t.common_data = [None] * len(t.column_meta)
    for i, cm in enumerate(t.column_meta):
        if cm.compression_type == COMP_COMMON:
            n = cm.additional_data_size // 8
            m = {}
            for _ in range(n):
                k = c.i32()
                v = c.u32()
                m[k] = v
            t.common_data[i] = m

    # encrypted id lists (unused)
    for s in t.sections:
        if s.tact_key_lookup == 0:
            continue
        n = c.i32()
        c.take(n * 4)

    prev_strtab = 0
    prev_records = 0
    for s in t.sections:
        c.pos = s.file_offset
        if t.flags & FLAG_SPARSE == 0:
            raw = c.take(s.num_records * t.record_size)
            records_data = _pad(raw)
            strdata = c.take(s.string_table_size)
            _read_string_table(t.string_table, strdata, prev_strtab)
            prev_strtab += s.string_table_size
        else:
            raw = c.take(s.offset_records_end - s.file_offset)
            records_data = _pad(raw)
            if c.pos != s.offset_records_end:
                raise ValueError("stream position != offset_records_end")

        # skip encrypted (zero-filled) sections
        if s.tact_key_lookup != 0 and _all_zero(raw):
            completely_zero = False
            if s.index_data_size > 0 or s.copy_table_count > 0:
                completely_zero = struct.unpack_from("<I", buf, c.pos)[0] == 0
            elif s.offset_map_id_count > 0:
                completely_zero = struct.unpack_from("<H", buf, c.pos + 4)[0] == 0
            else:
                completely_zero = True
            if completely_zero:
                prev_records += s.num_records
                continue

        # index (id) data
        index_data = [c.i32() for _ in range(s.index_data_size // 4)]
        if index_data and all(x == 0 for x in index_data):
            index_data = [t.min_index + prev_records + i for i in range(len(index_data))]

        # copy table
        for _ in range(s.copy_table_count):
            dest = c.i32()
            src = c.i32()
            if dest != src:
                t.copy_data.append((dest, src))

        sparse_entries = []
        if s.offset_map_id_count > 0:
            for _ in range(s.offset_map_id_count):
                b = c.take(6)
                sparse_entries.append((struct.unpack_from("<I", b, 0)[0],
                                       struct.unpack_from("<H", b, 4)[0]))

        if s.offset_map_id_count > 0 and (t.flags & FLAG_SECONDARY_KEY):
            index_data = _read_sparse_index(c, s, index_data)

        # parent lookup (relation) data
        ref_entries: dict[int, int] = {}
        if s.parent_lookup_size > 0:
            num = c.i32()
            c.take(8)  # min, max id
            for _ in range(num):
                rid = c.i32()
                ridx = c.i32()
                ref_entries[ridx] = rid

        if s.offset_map_id_count > 0 and not (t.flags & FLAG_SECONDARY_KEY):
            index_data = _read_sparse_index(c, s, index_data)

        position = 0
        for i in range(s.num_records):
            if t.flags & FLAG_SPARSE:
                row_pos = position
                row_off = 0
                position += sparse_entries[i][1] * 8
            else:
                row_pos = 0
                row_off = i * t.record_size

            if t.flags & FLAG_SECONDARY_KEY:
                ref_id = ref_entries.get(index_data[i], 0)
            else:
                ref_id = ref_entries.get(i, 0)

            row_id = index_data[i] if s.index_data_size != 0 else -1

            t.rows.append((_RawRow(row_off, row_pos, row_id, ref_id, i + prev_records), records_data))

        prev_records += s.num_records

    return t


def _read_sparse_index(c: _Cursor, s: _Section, index_data: list) -> list:
    sparse_index = [c.i32() for _ in range(s.offset_map_id_count)]
    if s.index_data_size > 0 and len(index_data) != len(sparse_index):
        raise ValueError("index_data length != sparse_index length")
    return sparse_index


def _all_zero(b: bytes) -> bool:
    return not any(b)


# --------------------------------------------------------------------------- #
# field decode
# --------------------------------------------------------------------------- #

@dataclass
class _Plan:
    name: str
    kind: str          # "int" | "float" | "string"
    size: int
    signed: bool
    arr_length: int
    is_noninline_rel: bool
    is_id: bool


def _build_plans(version: dbd.VersionDefinitions, cols: dict) -> list:
    plans = []
    for d in version.definitions:
        col = cols[d.name]
        p = _Plan(d.name, "", d.size, d.is_signed, d.arr_length,
                  d.is_relation and d.is_noninline, d.is_id)
        if col.type in ("int", "uint"):
            p.kind = "int"
            if d.size not in (8, 16, 32, 64):
                raise ValueError(f"{d.name}: unsupported int size {d.size}")
        elif col.type == "float":
            p.kind = "float"
        elif col.type in ("string", "locstring"):
            p.kind = "string"
        else:
            raise ValueError(f"{d.name}: bad type {col.type}")
        if p.is_noninline_rel:
            p.kind, p.size, p.signed = "int", 32, True
        plans.append(p)
    return plans


def _raw_to_int(raw: int, size: int, signed: bool) -> int:
    mask = (1 << size) - 1
    raw &= mask
    if signed and (raw & (1 << (size - 1))):
        raw -= 1 << size
    return raw


def decode(t: Table, version: dbd.VersionDefinitions, cols: dict) -> list[dict]:
    """Decode all rows (incl. copy-table duplicates) into {name: value} dicts."""
    plans = _build_plans(version, cols)
    by_id: dict[int, dict] = {}

    for raw_row, records_data in t.rows:
        rid, values = _decode_row(t, raw_row, records_data, plans)
        by_id[rid] = values

    if t.copy_data:
        id_name = plans[t.id_field_index].name
        for dest, src in t.copy_data:
            if src in by_id:
                v = dict(by_id[src])
                v[id_name] = dest
                by_id[dest] = v

    return [by_id[k] for k in sorted(by_id)]


def _decode_row(t: Table, row: _RawRow, records_data: bytes, plans: list):
    r = BitReader(records_data)
    r.position = row.position
    r.offset = row.offset

    rid = row.id
    values: dict = {}
    index_field_offset = 0

    for i, p in enumerate(plans):
        if i == t.id_field_index:
            if rid != -1:
                index_field_offset += 1
            else:
                rid = _get_field_raw(t, rid, r, 0) & 0xFFFFFFFF
            values[p.name] = rid
            continue

        field_index = i - index_field_offset
        if field_index >= len(t.meta_bits):
            values[p.name] = row.ref_id
            continue

        if p.arr_length != 0:
            values[p.name] = _read_array(t, r, field_index, p, row)
        else:
            values[p.name] = _read_scalar(t, rid, r, field_index, p, row)

    return rid, values


def _read_scalar(t: Table, rid: int, r: BitReader, field_index: int, p: _Plan, row: _RawRow):
    if p.kind == "string":
        if t.flags & FLAG_SPARSE:
            return r.read_cstring()
        record_offset = (row.record_index * t.record_size) - (t.records_count * t.record_size)
        byte_pos = r.position >> 3
        raw = _get_field_raw(t, rid, r, field_index)
        index = max(record_offset + byte_pos + _signed32(raw), 0)
        s = t.string_table.get(index)
        if s is None:
            raise ValueError(f"string table miss at {index}")
        return s

    raw = _get_field_raw(t, rid, r, field_index)
    if p.kind == "float":
        return struct.unpack("<f", struct.pack("<I", raw & 0xFFFFFFFF))[0]
    return _raw_to_int(raw, p.size, p.signed)


def _read_array(t: Table, r: BitReader, field_index: int, p: _Plan, row: _RawRow):
    bits, _ = t.meta_bits[field_index]
    cm = t.column_meta[field_index]

    if p.kind == "string":
        bit_size = 32 - bits
        if bit_size <= 0:
            bit_size = cm.b
        count = cm.size // 32
        record_offset = (row.record_index * t.record_size) - (t.records_count * t.record_size)
        out = []
        for _ in range(count):
            byte_pos = r.position >> 3
            raw = r.read_uint64(bit_size)
            index = max(byte_pos + record_offset + _signed32(raw), 0)
            out.append(t.string_table.get(index, ""))
        return out

    elem_bits = p.size if p.kind == "int" else 32
    raws = []
    if cm.compression_type == COMP_NONE:
        bit_size = 32 - bits
        if bit_size <= 0:
            bit_size = cm.b
        count = cm.size // elem_bits
        raws = [r.read_uint64(bit_size) for _ in range(count)]
    elif cm.compression_type == COMP_PALLET_ARRAY:
        cardinality = cm.c
        idx = r.read_uint32(cm.b)
        pallet = t.pallet_data[field_index]
        raws = [pallet[j + cardinality * idx] for j in range(cardinality)]
    else:
        raise ValueError(f"unexpected compression {cm.compression_type} for array")

    if p.kind == "float":
        return [struct.unpack("<f", struct.pack("<I", x & 0xFFFFFFFF))[0] for x in raws]
    return [_raw_to_int(x, p.size, p.signed) for x in raws]


def _get_field_raw(t: Table, rid: int, r: BitReader, field_index: int) -> int:
    bits, _ = t.meta_bits[field_index]
    cm = t.column_meta[field_index]
    ct = cm.compression_type

    if ct == COMP_NONE:
        bit_size = 32 - bits
        if bit_size <= 0:
            bit_size = cm.b
        return r.read_uint64(bit_size)
    if ct == COMP_SIGNED_IMMEDIATE:
        return r.read_value64_signed(cm.b) & 0xFFFFFFFFFFFFFFFF
    if ct == COMP_IMMEDIATE:
        return r.read_uint64(cm.b)
    if ct == COMP_COMMON:
        m = t.common_data[field_index]
        if rid in m:
            return m[rid]
        return cm.a & 0xFFFFFFFF
    if ct == COMP_PALLET:
        idx = r.read_uint32(cm.b)
        return t.pallet_data[field_index][idx]
    if ct == COMP_PALLET_ARRAY:
        idx = r.read_uint32(cm.b)
        return t.pallet_data[field_index][idx]
    raise ValueError(f"unexpected compression {ct}")


def _signed32(raw: int) -> int:
    raw &= 0xFFFFFFFF
    if raw & 0x80000000:
        raw -= 1 << 32
    return raw
