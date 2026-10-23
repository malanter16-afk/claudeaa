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

- One 512 px Cycles render per asset: neutral studio, 3/4 view, auto-framed.
- Re-renders only when the `.blend` is newer than the thumbnail.
- Takes about 10 s per asset on CPU.

### `classify` / `collect`: Claude Message Batches API

- **What it sends:** each request carries the thumbnail plus measured metadata (real size, triangle count, source, warnings).
- **Output:** a strict JSON schema built from `config/taxonomy.json` (see [`taxonomy.example.json`](taxonomy.example.json)):
  - `display_name`, `category`, `subcategory`, `function`, `description`
  - `materials`, `colours`, `style`, `zones`, `theme_fit`
  - `tier` (hero / mid / background), `tags`, `scale_plausible`, `issues`
- **Defaults:** `claude-opus-5-5` at effort `low` (simple per-image classification). `--model` / `--effort` change them.
- **Cost:** batches bill at **50 %**. Prints an estimate first; nothing is sent without `--yes`.
  - The estimate assumes about 1.8k input and 1.2k output tokens per asset: roughly $0.016 per asset on Opus 5.5. Check the first batch's real usage before a large run.
  - Batches are split under the 256 MB limit. Most finish within an hour; the maximum is 24 h. Results stay available for 29 days.
- **`collect` statuses:** each asset is recorded as `ok`, `refused`, `errored`, `expired`, `truncated` or `bad-json`. `classify --redo` resends anything that isn't `ok`.
  - Server-side refusal fallbacks are not available on the Batches API, so refused items are kept for a re-run instead.
- **Credentials:** standard Anthropic SDK resolution: `ANTHROPIC_API_KEY`, or an `ant auth login` profile. Install with `pip install anthropic`.

### `library`

- **Output:** one `.blend` per asset in `assets/library/<Category>/<Subcategory>/`, plus `blender_assets.cats.txt`.
- **Each asset is a single collection marked as an asset,** with:
  - its catalog
  - description (including the licence)
  - author (the source)
  - tags (tags + zones + tier + theme)
  - the thumbnail as its preview
- **To use it:** in Blender, add the folder under *Preferences › File Paths › Asset Libraries*, then drag assets in from the Asset Browser.

### `browse`

- **Output:** a self-contained HTML page next to `assets/` with thumbnails and filters (category, zone, theme, tier, source), plus text search.
- Click a path to copy it.

## Tested

| Status | What |
|---|---|
| Tested | Linux, Blender 4.5.15, 23 Oct 2026: `inventory`, `thumbs`, `classify --dry-run` (request and schema construction), `library` (asset marking, catalogs, tags and preview verified by reopening the file), `browse` |
| Not tested here | Live `classify --yes` / `collect` (no API credentials in the build environment) and the catalogue-aware `ue_import.py` (no Unreal). Run a 3–5 asset batch first and check `catalog.json` |
