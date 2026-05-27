# Source Trace Manifest

This manifest records the source routines that the next emitted binary should
port first. It is the working contract for source-guided emission: read the C,
then write Python emitter routines that generate equivalent x86 machine code.

## Stage: source_stage01_wad_map

Output:

```text
build/source_stage01_wad_map.exe
```

Scope:

- Runtime WAD directory loading.
- Runtime lump lookup.
- Runtime loading of the core map setup lumps needed before BSP rendering.
- On-screen count/sanity output, not a renderer yet.

| Source routine | Source file | Starts at | Emitted label | Status | Validation target |
| --- | --- | ---: | --- | --- | --- |
| `W_NumLumps` | `reference/chocolate-doom/src/w_wad.c` | 249 | `wad_num_lumps` | planned | Returns loaded directory count. |
| `W_CheckNumForName` | `reference/chocolate-doom/src/w_wad.c` | 261 | `wad_check_num_for_name` | planned | Finds `MAP01`, returns -1 for missing names. |
| `W_GetNumForName` | `reference/chocolate-doom/src/w_wad.c` | 310 | `wad_get_num_for_name` | planned | Fails visibly when `MAP01` is unavailable. |
| `W_LumpLength` | `reference/chocolate-doom/src/w_wad.c` | 329 | `wad_lump_length` | planned | Reports exact byte size for selected lumps. |
| `W_ReadLump` | `reference/chocolate-doom/src/w_wad.c` | 346 | `wad_read_lump` | planned | Reads a selected lump into the emitted data arena. |
| `P_LoadVertexes` | `reference/chocolate-doom/src/doom/p_setup.c` | 120 | `map_load_vertexes` | planned | Converts signed 16-bit map coordinates to 16.16 fixed. |
| `P_LoadSectors` | `reference/chocolate-doom/src/doom/p_setup.c` | 275 | `map_load_sectors` | planned | Converts floor/ceiling heights to 16.16 fixed and keeps light/tag fields. |
| `P_LoadSideDefs` | `reference/chocolate-doom/src/doom/p_setup.c` | 495 | `map_load_sidedefs` | planned | Preserves offsets, texture names or ids, and sector links. |
| `P_LoadLineDefs` | `reference/chocolate-doom/src/doom/p_setup.c` | 414 | `map_load_linedefs` | planned | Builds vertex links, dx/dy, bbox, side indexes, and sector links. |

## Important Source Ordering

`P_SetupLevel` loads these map structures in this order:

```text
P_LoadBlockMap
P_LoadVertexes
P_LoadSectors
P_LoadSideDefs
P_LoadLineDefs
P_LoadSubsectors
P_LoadNodes
P_LoadSegs
P_GroupLines
P_LoadReject
P_LoadThings
```

The first source-guided stage intentionally stops after `P_LoadLineDefs`. That
keeps the slice small while preserving the real dependency order: linedefs need
loaded vertexes, sidedefs, and sectors.

## Notes From Initial Read

- `W_CheckNumForName` scans backwards when no lump hash table exists. The first
  emitted stage can use that linear path before implementing `W_GenerateHashTable`.
- `W_LumpLength` and `W_ReadLump` are good early ports because their behavior is
  small but they exercise the real lump directory layout.
- `P_LoadVertexes` is the cleanest first map conversion routine: each 4-byte map
  vertex becomes two 32-bit fixed-point coordinates.
- `P_LoadLineDefs` should come after sectors and sidedefs because it stores
  front/back sector pointers derived through sidedef indexes.
