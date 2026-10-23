# asset_fetch

Downloads **open-licence assets that need no login** straight into `assets/inbox/<source>/<id>/`, each with an `asset.json` (licence, URL, real tile size), so `asset_ingest` converts them and the licence trail is complete.

```
python tools/asset_fetch/fetch_open.py --list wanted/open_assets.json --res 2k      # all
python tools/asset_fetch/fetch_open.py --list wanted/open_assets.json --only marble_01
SKETCHFAB_TOKEN=... python tools/asset_fetch/fetch_open.py --list wanted/sketchfab.json
```

| Source | What | Notes |
|---|---|---|
| Poly Haven (CC0) | Models (glTF + textures), textures (saved as `<id>_color/rough/normal/height`), HDRIs (to `assets/hdri/`) | Uses the public API with a unique User-Agent, as Poly Haven asks; fetches only listed items, no mirroring. The real tile size comes from the API |
| ambientCG (CC0) | Material zips; only the PBR map JPGs are kept | Set `real_size_m` per entry when known |
| Sketchfab | glTF download through the **official API** with *your* token | Refuses non-commercial and no-derivatives licences; writes the attribution line. Untested here (no token) |
| `url` | Any direct file, e.g. the Survey of India political map PDF | That server returned HTTP 500 from outside India on 23 Oct 2026; download it by hand if the fetch fails |

Items already in the inbox are skipped, so nothing is downloaded twice. Standard library only.

## Tested
Linux, 23 Oct 2026, end to end:
- **Fetched:** a Poly Haven model (`potted_plant_01`), a Poly Haven texture (`marble_01`) and an ambientCG material (`Marble012`).
- **Converted:** `ingest` built the plant at its real 1.35 m height and both marbles as full PBR materials (`marble_01` at its real 1.5 m tile).
- **Licences:** recorded automatically.
