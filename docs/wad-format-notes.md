# WAD Format Notes

These notes cover the small subset of the DOOM WAD format needed by the
Python parser in Phase 6 and the later emitted WAD probe.

## Header

A WAD begins with a 12-byte little-endian header:

```text
offset  size  field
0       4     identification: "IWAD" or "PWAD"
4       4     number of directory entries
8       4     byte offset of the directory
```

`IWAD` files contain a complete game data set. `PWAD` files are patch WADs.
For this project the parser accepts both, because the binary structures are the
same at this level.

## Directory

The directory is an array of 16-byte entries. The header tells us where the
array starts and how many entries it has.

```text
offset  size  field
0       4     lump file offset
4       4     lump size in bytes
8       8     lump name, ASCII, NUL-padded when shorter than 8 bytes
```

Directory entries are the table of contents for the WAD. Lump data does not
need to appear in the same order as the directory, so code should trust the
directory entry offsets and sizes rather than assuming the data is packed in
directory order.

Some entries are markers instead of real data. Markers often have size zero and
are used to delimit sections such as maps, sprites, flats, or patches.

## Lump Names

Classic DOOM lump names are at most 8 ASCII bytes. Matching should be
case-insensitive for convenience, but tools should preserve the original name
from the directory for display.

Important global lumps for early milestones:

- `PLAYPAL`: palette data.
- `COLORMAP`: light-level color maps.
- `TITLEPIC`: title screen picture in many IWADs.

For "title picture or equivalent" probing, `tools/wad.py` also checks common
display candidates such as `INTERPIC`, `CREDIT`, `HELP1`, and `HELP2`.

## Map Markers

Classic maps begin with a zero-size marker lump. There are two common marker
styles:

```text
E1M1   episode/mission map name used by DOOM 1 style IWADs
MAP01  numbered map name used by DOOM 2 style IWADs
```

The map data follows the marker as a contiguous group of lumps. The classic
order is:

```text
THINGS
LINEDEFS
SIDEDEFS
VERTEXES
SEGS
SSECTORS
NODES
SECTORS
REJECT
BLOCKMAP
```

The Phase 6 parser treats these as the important map lumps to locate. The core
geometry and gameplay-starting subset is:

```text
THINGS, LINEDEFS, SIDEDEFS, VERTEXES, SEGS, SSECTORS, NODES, SECTORS
```

Later phases can parse the binary payloads of these lumps into map structures.
Phase 6 only identifies their names, offsets, and sizes.

## CLI

Inspect a WAD summary from the repository root:

```powershell
python tools/wad.py third_party/freedoom/freedoom2.wad --summary
```

List every lump:

```powershell
python tools/wad.py third_party/freedoom/freedoom2.wad --list
```

Show the important lumps for one map:

```powershell
python tools/wad.py third_party/freedoom/freedoom2.wad --map MAP01
```
