# asset_catalog

Turns the converted assets from [`asset_ingest`](../asset_ingest/README.md) into a searchable library:

```
wanted/*.json  ──inventory──▶  DOWNLOAD_STATUS.md        what's downloaded vs still missing
assets/manifest.json ─thumbs─▶ normalized/**/thumb.png   studio preview per asset (Blender, CPU)
      ─classify / collect──▶   assets/catalog.json        Claude tags: category, function, zones, theme, tier…
      ─library──▶              assets/library/            Blender Asset Browser library (catalogs, tags, previews)
      ─browse──▶               assets/catalog.html        filterable HTML catalogue
      ue_import.py ──▶         /Game/Assets/<Category>/<Sub>/<item> + searchable metadata in Unreal
```

## Commands

Run all commands from the project root.

```
python tools/asset_catalog/catalog.py inventory --wanted "wanted/*.json" --scan assets/inbox ~/Downloads
python tools/asset_catalog/catalog.py thumbs    --blender <blender-4.5>
python tools/asset_catalog/catalog.py classify  --taxonomy config/taxonomy.json            # estimate only
python tools/asset_catalog/catalog.py classify  --taxonomy config/taxonomy.json --yes      # submit (spends credits)
python tools/asset_catalog/catalog.py collect                                              # later: fetch results
python tools/asset_catalog/catalog.py library   --blender <blender-4.5 or 5.x>
python tools/asset_catalog/catalog.py browse    --title "My project assets"
```

### `inventory`

- **Wanted list:** a JSON list (or CSV) of `{"name", "url", ...}`. One file per source: the filename becomes the source name.
- **Matching:** each wanted item is matched against archive files and folders found under `--scan` (3 levels deep), using name tokens with fuzzy fallback.
- **Output:** `DOWNLOAD_STATUS.md` lists missing items as checkboxes with links, then the downloaded items, then local downloads that are on no list.

### `thumbs`

- **Four Cycles views per asset** (`--views`), neutral studio, auto-framed:
  - **hero:** a 512 px 3/4 view, used as the thumbnail
  - **front** and **side:** the true silhouette and proportions
  - **detail:** a close-up of the upper part, showing material, finish and texture quality
- **Measured surface colours** go to `views/palette.json`: each material's real base colour, weighted by area. Textures are split into their 2–3 main colours, so a leather + metal texture isn't averaged into mud. This is the asset's true colour, independent of the studio lighting.
- Re-renders only what's missing or older than the `.blend`.
- Takes about 15–20 s per asset on a multi-core CPU.

### `classify` / `collect`: Claude Message Batches API

- **What it sends, so tags describe how the asset actually looks:**
  - all four views
  - the measured colours
  - the **maker's own product photo** when the download includes one (file names containing preview/render/photo/thumb…)
  - measured metadata: real size, triangle count, source, warnings
- **Output:** a strict JSON schema built from `config/taxonomy.json` (see [`taxonomy.example.json`](taxonomy.example.json)):
  - `display_name`, `category`, `subcategory`, `function`, `description`
  - **Appearance:**
    - `appearance`: silhouette, proportions, structure and details, as seen
    - `form` (cantilever, slender legs, tufted…)
    - `finishes` (brushed stainless, matte black powder coat…)
    - `colour_palette`: named colours with measured hex values and roles
    - `design_reference` (the design language or iconic piece it resembles)
    - `visual_quality` (photoreal / good / basic / placeholder)
    - `matches_maker_photo`: render vs maker photo; mismatches go into `issues`
  - `materials`, `colours`, `style`, `zones`, `theme_fit`
  - `tier` (hero / mid / background), `tags`, `scale_plausible`, `issues`
- **Defaults:** `claude-opus-5-5` at effort `low` (simple per-image classification). `--model` / `--effort` change them.
- **Cost:** batches bill at **50 %**. Prints an estimate first; nothing is sent without `--yes`.
  - The estimate counts the images and assumes about 1.6k output tokens: roughly **$0.02 per asset** on Opus 5.5 with four views. Check the first batch's real usage before a large run.
  - Batches are split under the 256 MB limit. Most finish within an hour; the maximum is 24 h. Results stay available for 29 days.
- **`collect` statuses:** each asset is recorded as `ok`, `refused`, `errored`, `expired`, `truncated` or `bad-json`. `classify --redo` resends anything that isn't `ok`.
  - Server-side refusal fallbacks are not available on the Batches API, so refused items are kept for a re-run instead.
- **Credentials:** standard Anthropic SDK resolution: `ANTHROPIC_API_KEY`, or an `ant auth login` profile. Install with `pip install anthropic`.

### `library`

- **Output:** one `.blend` per asset in `assets/library/<Category>/<Subcategory>/`, plus `blender_assets.cats.txt`.
- **Each asset is a single collection marked as an asset** (for material swatches, each **material** is the asset, so you can drag it onto objects), with:
  - its catalog
  - description (including the licence)
  - author (the source)
  - tags (tags + zones + tier + theme)
  - the thumbnail as its preview
- **To use it:** in Blender, add the folder under *Preferences › File Paths › Asset Libraries*, then drag assets in from the Asset Browser.

### `browse`

- **Output:** a self-contained HTML page next to `assets/`:
  - thumbnails, the appearance text, colour swatches, finishes and design reference
  - a warning chip when the render doesn't match the maker's photo
  - filters (category, zone, theme, tier, source)
  - search on looks (e.g. "black leather", "brushed steel slender"): every word must match
- Click a path to copy it.

## Tested

| Status | What |
|---|---|
| Tested | Linux, Blender 4.5.15, 23 Oct 2026: `inventory`, `thumbs` (four views + measured colours, incl. texture clustering), `classify --dry-run` (request, schema, views, palette and maker photo in the request), `library` (collection and material assets; marking, catalogs, tags and preview verified by reopening the file), `browse` |
| Not tested here | Live `classify --yes` / `collect` (no API credentials in the build environment) and the catalogue-aware `ue_import.py` (no Unreal). Run a 3–5 asset batch first and check `catalog.json` |
