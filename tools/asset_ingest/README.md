# asset_ingest

Turns manually downloaded 3D assets (manufacturer zips, SketchUp/Collada/FBX/OBJ/3DS/3ds Max files, IES photometry) into consistent files for **Blender → Unreal**. Nobody converts anything by hand.

```
assets/inbox/<source>/<item>/...      what you download, untouched (zips are fine)
        │  python ingest.py run
        ▼
assets/normalized/<source>/<item>/
    <item>.blend   original hierarchy, textures packed     → Blender
    <item>.glb     original hierarchy, textures embedded   → Blender / web preview
    <item>.fbx     joined into one mesh, textures embedded → Unreal
    <item>.usdc    (with --usd)                            → Unreal / USD workflows
    photometry/*.ies|*.ldt
    report.json, convert.log
assets/manifest.json                   one record per item (licence, size, outputs, warnings)
        │  ue_import.py (inside Unreal)
        ▼
/Game/Assets/<source>/<item>/          static meshes + IES light profiles
```

## Requirements

- **Python 3.9+** to run `ingest.py` (standard library only).
- **Blender 4.5 LTS as the converter.** As far as I know, Blender 5.x removed Collada import, while 4.5 still has it and opens everything else. Your scene work can stay on 5.x: it opens 4.5 `.blend` files.
  - Point `--blender` at it, or set `BLENDER_CONVERTER`.
- **One-time setup** installs the importers that Blender doesn't ship:
  ```
  python ingest.py setup --blender "C:/Program Files/Blender Foundation/Blender 4.5/blender.exe" [--skp-zip pyslapi.zip]
  ```
  - Without arguments: installs the **3DS** (`autodesk_3ds_format`) and **3ds Max `.max`** (`io_scene_max`) importers from extensions.blender.org. Needs internet once.
  - **`--skp-zip`, for SketchUp `.skp`:** also installs the free [pyslapi importer](https://github.com/martijnberger/pyslapi/releases) (SketchUp files up to 2025.1, Blender 4.x). **Windows or macOS only**: the SketchUp SDK has no Linux build.
  - Also `pip install`s **cascadio** (OpenCASCADE) into the Python running `ingest.py`, for **STEP/IGES** engineering CAD.
  - Safe to re-run. It finishes by checking that each importer actually loads.
- **Unreal step:** UE 5.x with the Python Editor Script Plugin enabled.

## Use

```
python ingest.py run --blender <blender-4.5> [--usd] [--only knoll/barcelona-stool] [--force]
```

- **Re-running is cheap.** Unchanged items are skipped, using a hash of the downloaded files.
- **Exit code 1** means something needs attention: a failed conversion, or an item with no usable model.
- Then, in Unreal:
  ```
  UnrealEditor-Cmd.exe Project.uproject -run=pythonscript -script="<path>/ue_import.py"
  ```
  Set `INGEST_MANIFEST` if `assets/` isn't next to the Unreal project folder.

### What happens to each item

1. **Unpack:** zips (and zips inside zips) are unpacked into `assets/normalized/_work/`.
2. **Pick a model, best format first:** `.blend` › `.glb/.gltf` › `.fbx` › `.usd*` › `.obj` › `.dae` › `.skp` › `.3ds` › `.max` › `.step/.stp/.iges/.igs` › `.stl/.ply`. If there are several of one type, the largest wins.
   - **STEP/IGES** (manufacturer CAD for pumps, valves, cranes, racking, machines) is meshed to `.glb` with cascadio, keeping part colours, then stood upright. STEP units come from the file, and IGES units from its header. Expect dense meshes, flat colours and no textures: re-material anything seen close up. `cad_tolerance_m` in `asset.json` sets the meshing detail (default 0.001 m).
   - Revit, DWG/DXF, Cinema 4D, Rhino and ArchiCAD files are recorded as `unsupported_files` and ignored. Download an FBX/OBJ/SKP version of those instead.
   - `.max` brings in geometry, but V-Ray/Corona materials don't survive. Expect to re-material.
3. **Import headless in Blender,** then remove cameras, lights and 2D linework.
4. **Fix the scale:** 1 unit = 1 m.
   - `.glb/.gltf`, `.usd*` and `.blend` carry real units and are trusted as they are, so a 30 m tank stays 30 m.
   - SketchUp works in inches and many OBJ files are in centimetres, so for those formats the unit is **guessed** (assuming an object between 2 cm and 8 m) and flagged as a warning.
   - To pin it exactly, give `real_height_m` in `asset.json`.
5. **Normalise:** apply transforms; put the origin at the **bottom centre** of the bounding box.
6. **Relink and embed textures:** find missing textures in the unpacked folder, then pack/embed them.
7. **Export** `.blend` / `.glb` / `.fbx` (/`.usdc`) and write `report.json` plus a manifest record.
8. **Texture-only downloads become materials.** When there's no model but there are images (stone, tile, fabric or cladding swatches):
   - Maps are recognised from file names: colour/albedo/diffuse, roughness (or gloss, inverted), normal, height/bump, metal.
   - Each set (e.g. one per colour variant) becomes a Principled material on a 1.2 m sample panel.
   - Real-world tiling comes from `real_size_m` (one texture tile, in metres; default 1 m, with a warning).
   - The manifest records `"kind": "material"`; the asset library turns these into **material assets**.
9. **Photometry:** copy `.ies`/`.ldt` files to `photometry/`. Unreal's light profiles need **`.ies`**; LDT-only items get a warning.

## `asset.json` (optional, per item folder)

```json
{
  "licence": "Manufacturer CAD terms – visualisation only, no redistribution",
  "url": "https://…/product-page",
  "attribution": null,
  "commercial_ok": true,
  "source_file": "Barcelona_Stool.skp",
  "real_height_m": 0.37,
  "real_size_m": 0.6,
  "kind": "furniture"
}
```

- **`kind`:**
  - `architecture` turns off unit guessing and mesh joining (for rooms and buildings).
  - `large` turns off unit guessing only, for anything over 8 m in a guessed format: vehicles, cranes, tanks, plant structures. Use it with `real_height_m` when the file's unit is unknown.
- **`real_size_m`:** for texture-only items, the real size of one texture tile in metres (e.g. 0.6 for a 60 × 60 cm tile).
- **Per-source defaults:** put a `source.json` with the same fields in `assets/inbox/<source>/`. It applies to every item in that source, so set the licence once for, say, 200 freebies. An item's own `asset.json` overrides it.
- **`licence`:** items without one are listed as `TODO` after each run, so the licence trail stays complete before any client render.

## Tested

| Status | What |
|---|---|
| Tested | Linux, Blender 4.5.15 LTS, 23 Oct 2026: FBX + textures in a zip (Poly Haven), texture-only zips becoming materials (map detection, gloss inversion, colour variants), OBJ in centimetres, Collada inside a nested zip, 3DS (after `setup`), a multi-part FBX, LDT-only and Revit-only items, a clear error for `.skp` without the importer, unchanged-item skipping, `setup` re-runs. Reimported outputs had the right size, the origin at z = 0 and embedded textures |
| Tested, 28 Oct 2026 | STEP in mm (a coloured two-part skid, 2 m; a 10 × 30 m column): right size, upright, part colours kept. IGES in mm and in inches: right size. OBJ in cm still guessed correctly. A clear error when cascadio is missing |
| Not tested here | Real `.skp` files (needs Windows/macOS), real `.max` files (no sample available) and `ue_import.py` (needs Unreal). Run one item through each before a batch |

## Known limits

- **Unit guessing** picks the first plausible unit (2 cm – 8 m). A tiny or huge object can be mis-scaled, so always read the warnings.
- **No LDT → IES conversion.** Most manufacturers (ERCO, Delta Light) offer both; download the IES.
- **Simplified models stay simplified.** Planning-grade CAD symbols (e.g. furniture-maker space-planning files) come in faithfully, but basic. Bevels and real materials are a later scene step.
