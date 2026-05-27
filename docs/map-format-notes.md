# Map Format Notes

These notes cover the Phase 9 Python map loader. The loader reads classic DOOM
map lumps that `tools/wad.py` has already found after a map marker such as
`E1M1` or `MAP01`.

## Loader Scope

Phase 9 decodes the core gameplay and geometry records:

```text
THINGS
LINEDEFS
SIDEDEFS
VERTEXES
SECTORS
```

It deliberately does not emit any x86 map loading logic yet. It also does not
parse BSP traversal data such as `SEGS`, `SSECTORS`, or `NODES`; those remain
later rendering concerns.

## Endianness

Classic DOOM map records are little-endian. Most numeric fields are 16-bit
values. Coordinate and height fields are signed because map geometry can use
negative positions or floor heights.

## VERTEXES

Each vertex is 4 bytes:

```text
offset  size  field
0       2     x coordinate, signed int16
2       2     y coordinate, signed int16
```

Linedefs reference vertices by zero-based index.

## THINGS

Each thing is 10 bytes:

```text
offset  size  field
0       2     x coordinate, signed int16
2       2     y coordinate, signed int16
4       2     angle
6       2     thing type
8       2     flags
```

Player starts use thing types `1`, `2`, `3`, and `4`. Phase 9 reports them in
the summary so later emitted stages can find a spawn point.

## LINEDEFS

Each linedef is 14 bytes:

```text
offset  size  field
0       2     start vertex index
2       2     end vertex index
4       2     flags
6       2     special type
8       2     sector tag
10      2     right sidedef index
12      2     left sidedef index, or 0xffff when absent
```

A linedef with no left sidedef is one-sided. A linedef with both sidedefs is
two-sided and usually separates two sectors.

## SIDEDEFS

Each sidedef is 30 bytes:

```text
offset  size  field
0       2     x texture offset, signed int16
2       2     y texture offset, signed int16
4       8     upper texture name
12      8     lower texture name
20      8     middle texture name
28      2     sector index
```

Texture names are fixed 8-byte ASCII fields. Shorter names are NUL-padded.
The `-` name means no texture for that slot.

## SECTORS

Each sector is 26 bytes:

```text
offset  size  field
0       2     floor height, signed int16
2       2     ceiling height, signed int16
4       8     floor flat name
12      8     ceiling flat name
20      2     light level, signed int16
22      2     special type
24      2     tag
```

Phase 9 reports height and light ranges to quickly prove the sector data was
decoded sensibly.

## CLI

Summarize a Freedoom map from the repository root:

```powershell
python tools/map_loader.py build/third_party/freedoom/freedoom2.wad --map MAP01
```

If `--map` is omitted, the loader tries `MAP01`, then `E1M1`, then the first
classic map marker present in the WAD.
