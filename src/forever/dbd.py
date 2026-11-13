"""Parser for WoWDBDefs `.dbd` definition files + version selection.

A `.dbd` file has a COLUMNS block (name -> type) followed by one or more
version blocks (LAYOUT / BUILD headers + an ordered field list). This picks the
version block matching our client — by layout hash (robust across the odd
version strings a private-server client reports), falling back to exact build
number.

Pure-Python port of WoWDBDefs' DBDReader (BSD-3-Clause) via the wowsims/mop
db2tool `dbd` package.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ColumnDefinition:
    type: str = ""
    foreign_table: str = ""
    foreign_column: str = ""


@dataclass
class Definition:
    name: str = ""
    size: int = 0
    arr_length: int = 0
    is_id: bool = False
    is_relation: bool = False
    is_noninline: bool = False
    is_signed: bool = False


@dataclass
class VersionDefinitions:
    builds: list[int] = field(default_factory=list)
    build_ranges: list[tuple[int, int]] = field(default_factory=list)
    layout_hashes: list[str] = field(default_factory=list)
    definitions: list[Definition] = field(default_factory=list)


@dataclass
class DBDefinition:
    column_definitions: dict[str, ColumnDefinition] = field(default_factory=dict)
    version_definitions: list[VersionDefinitions] = field(default_factory=list)


def _read_lines(raw: str) -> list[str]:
    s = raw.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    lines = s.split("\n")
    if lines and lines[-1] == "" and s.endswith("\n"):
        lines = lines[:-1]
    if len(lines) == 1 and lines[0] == "":
        return []
    return lines


def _build_number(s: str) -> int:
    return int(s.split(".")[3])


def parse(raw: str) -> DBDefinition:
    lines = _read_lines(raw)
    if not lines or not lines[0].startswith("COLUMNS"):
        raise ValueError("file does not start with column definitions")

    cols: dict[str, ColumnDefinition] = {}
    i = 1
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.strip() == "":
            break
        type_end = min((p for p in (line.find(" "), line.find("<")) if p >= 0), default=-1)
        col_type = line[:type_end]
        if col_type not in ("uint", "int", "float", "string", "locstring"):
            raise ValueError(f"invalid column type {col_type!r}")
        cd = ColumnDefinition(type=col_type)
        if line.startswith(col_type + "<"):
            lt, gt = line.index("<"), line.index(">")
            fk = line[lt + 1:gt].split("::")
            if len(fk) == 2:
                cd.foreign_table, cd.foreign_column = fk
        # column name: token after the first space (up to next space)
        first = line.index(" ")
        if line.rindex(" ") == first:
            name = line[first + 1:]
        else:
            second = line.index(" ", first + 1)
            name = line[first + 1:second]
        if name.endswith("?"):
            name = name[:-1]
        cols[name] = cd

    versions: list[VersionDefinitions] = []
    defs: list[Definition] = []
    layout_hashes: list[str] = []
    builds: list[int] = []
    build_ranges: list[tuple[int, int]] = []

    def flush():
        nonlocal defs, layout_hashes, builds, build_ranges
        if builds or build_ranges or layout_hashes:
            versions.append(VersionDefinitions(list(builds), list(build_ranges),
                                               list(layout_hashes), list(defs)))

    n = len(lines)
    for idx in range(i, n):
        line = lines[idx]
        if line.strip() == "":
            flush()
            defs, layout_hashes, builds, build_ranges = [], [], [], []

        if line.startswith("LAYOUT"):
            layout_hashes.extend(line[7:].split(", "))
        elif line.startswith("BUILD"):
            for tok in line[6:].split(", "):
                if "-" in tok:
                    a, b = tok.split("-")
                    build_ranges.append((_build_number(a), _build_number(b)))
                else:
                    builds.append(_build_number(tok))
        elif line.startswith("COMMENT"):
            pass
        elif line.strip() != "":
            d = Definition()
            # $annotations$
            if "$" in line:
                a_start = line.index("$")
                a_end = line.index("$", 1)
                for a in line[a_start + 1:a_end].split(","):
                    if a == "id":
                        d.is_id = True
                    elif a == "noninline":
                        d.is_noninline = True
                    elif a == "relation":
                        d.is_relation = True
                line = line[:a_start] + line[a_start + a_end + 1:]
            # <size>
            if "<" in line:
                lt, gt = line.index("<"), line.index(">")
                size = line[lt + 1:gt]
                if size.startswith("u"):
                    d.is_signed = False
                    d.size = int(size.replace("u", ""))
                else:
                    d.is_signed = True
                    d.size = int(size)
                line = line[:lt] + line[gt + 1:]
            # [array]
            if "[" in line:
                lb, rb = line.index("["), line.index("]")
                d.arr_length = int(line[lb + 1:rb])
                line = line[:lb] + line[rb + 1:]
            # trailing comment
            ci = line.find("//")
            if ci >= 0:
                line = line[:ci].strip()
            d.name = line
            if d.name not in cols:
                raise ValueError(f"unknown column {d.name!r} in version block")
            if cols[d.name].type == "uint":
                d.is_signed = False
            defs.append(d)

        if idx == n - 1:
            flush()

    return DBDefinition(cols, versions)


def select(defn: DBDefinition, layout_hash: str, build: int) -> VersionDefinitions:
    """Pick the version block by layout hash (preferred) or exact build number."""
    layout_hash = layout_hash.upper()
    for v in reversed(defn.version_definitions):
        if layout_hash in (h.upper() for h in v.layout_hashes):
            return v
    for v in reversed(defn.version_definitions):
        if build in v.builds:
            return v
    for v in reversed(defn.version_definitions):
        if any(lo <= build <= hi for lo, hi in v.build_ranges):
            return v
    raise ValueError(f"no version block matches layout {layout_hash} / build {build}")
