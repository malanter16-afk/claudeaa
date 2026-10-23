# SAIL Experience Centre: download list

Your checklist for the SAIL Lodhi Road visualisation (Blender 5.2 + Cycles, Unreal 5.8).
Links were researched on 23 Oct 2026 and every one was opened from a script. Sites that block scripts (Vitra, Fab, Poliigon, BIMobject, mtextur, Syncronia, Evermotion, Acuity) still open normally in a browser.

- **Sections 1–11:** only **you** can get these. Each needs your account, a login, a purchase or a manual click, or the site's terms ban bots.
- **Section 12:** what **Claude downloads automatically**. Skip those.

**Tags:** `account` = free sign-up · `paid` = purchase · `manual` = free, no login, but click-only · `check` = portal confirmed, exact file/licence not confirmed

---

## 0. Before you start

**Where files go:** drop every download, still zipped, into `assets/inbox/<source>/<item>/`
(e.g. `assets/inbox/knoll/barcelona-chair/`). Claude handles conversion, real-world scale, origin, materials, bevels and the licence manifest.

**Format to pick:** FBX → OBJ → glTF → 3DS → SKP → DWG-3D. **Skip Revit `.rfa`** (Blender can't open it). Lighting: `.ies` best, `.ldt` fine (Claude converts).

**Licence rule:** the renders go to SAIL in a pitch, so treat it as commercial use. Nothing here is pirated, non-commercial or research-only.
Use manufacturer models in scenes and renders, but never pass the model files themselves on to anyone. Credit CC-BY authors in `ATTRIBUTIONS.md` (Claude writes it).

**Accounts to create (one sitting):**
- [ ] Trimble ID (3D Warehouse)
- [ ] myERCO
- [ ] My Deltalight
- [ ] Sketchfab
- [ ] Design Connected
- [ ] Dimensiva
- [ ] Epic Games (Fab + MetaHuman)
- [ ] Adobe ID (Mixamo + Substance 3D Assets)
- [ ] Poliigon
- [ ] Margraf download area
- [ ] mtextur
- [ ] BIS standards portal
- [ ] Muuto Professionals
- [ ] Evermotion
- [ ] 3dsky, BIMobject, Architonic (as needed)

---

## 1. Start here: the 10 downloads that lift every zone

1. [ ] **ERCO full IES/LDT archive**: museum-grade track spots on every artefact → [download.erco.com](https://download.erco.com/en/planning_luminaire/ies) `account`
2. [ ] **Delta Light bulk IES/LDT + 3D fixtures** → [technical downloads](https://www.deltalight.com/en/my-deltalight/technical-downloads) `account`
3. [ ] **Knoll Barcelona + Bertoia** (chromed flat-bar steel, welded steel rod) → [Knoll symbol library](https://www.knoll.com/design-plan/resources/furniture-symbols/showcase-symbols?searchtext=Barcelona) `manual`
4. [ ] **Herman Miller Eames Wire Chair + Tandem Sling seating** → [Eames Wire Chair](https://www.hermanmiller.com/resources/3d-models-and-planning-tools/product-models/individual/eames-wire-chair-wire-base-upholstered-seat/) `check`
5. [ ] **Vitra official 3D Warehouse profile** (155 models) → [3dwarehouse.sketchup.com/by/vitra](https://3dwarehouse.sketchup.com/by/vitra) `account`
6. [ ] **Heavy Section Rolling Mill (real museum scan)**, the Legacy Tree's historic machine → [Sketchfab](https://sketchfab.com/3d-models/heavy-section-rolling-mill-80e01ff6ebc24bc9a4f784eddcfab047) `account` CC-BY
7. [ ] **Steelworks blast furnace (drone photogrammetry)** for Zone 4 → [Sketchfab](https://sketchfab.com/3d-models/steelworks-factory-blast-furnace-c2c1673b1e054becb0e0253001fc59ed) `account` CC-BY
8. [ ] **Kvadrat PBR fabrics** for the lounge upholstery → [Remix 3](https://www.kvadrat.dk/en/products/upholstery/2968-remix-3), [Hallingdal 65](https://www.kvadrat.dk/en/products/upholstery/1000-hallingdal-65) `check`
9. [ ] **Margraf marble library**: real Italian marble scans for the pale-stone floors → [downloadarea.margraf.it](https://downloadarea.margraf.it) `account`
10. [ ] **People + plants:** [RenderPeople free](https://renderpeople.com/free-3d-people/) `manual` and [Globe Plants](https://globeplants.com/) indoor & office packs `paid`

---

## 2. Steel furniture: manufacturer files

The story here: SAIL is a steel company, so the furniture is steel too. Chrome and satin pieces suit **Contemporary Steel**; raw and blackened pieces suit **Forged Heritage**.

| ✓ | What | Where | Zone | Notes |
|---|---|---|---|---|
| [ ] | Knoll **Barcelona** chair, stool, table, couch | [Knoll FSL › Barcelona](https://www.knoll.com/design-plan/resources/furniture-symbols/showcase-symbols?searchtext=Barcelona) | Z1 VIP lounge | Take the SketchUp file |
| [ ] | Knoll **MR** chair/chaise, **Bertoia** Diamond/side/stool, **Platner** | [Knoll FSL](https://www.knoll.com/design-plan/resources/furniture-symbols/showcase-symbols) | Z1, Z5 stools, Z7 | Search on page |
| [ ] | Herman Miller **Eames Wire Chair** (wire, dowel, 4-leg bases) | [hermanmiller.com](https://www.hermanmiller.com/resources/3d-models-and-planning-tools/product-models/individual/eames-wire-chair-wire-base-upholstered-seat/) | Z5, café edge | SKP; may need a free HM Pro sign-up |
| [ ] | Herman Miller **Eames Tandem Sling**, **Aluminum Group** | [HM India 3D models](https://www.hermanmiller.com/en_in/resources/3d-models-and-planning-tools/) | Passage, meeting room | Search on page |
| [ ] | Vitra **Standard** (Prouvé, sheet steel) | [vitra.com › Standard](https://www.vitra.com/en-un/product/standard) | Meeting room, Z7 | "CAD data" section; also Fauteuil Direction, EM Table, Potence |
| [ ] | Vitra brand profile | [3D Warehouse › Vitra](https://3dwarehouse.sketchup.com/by/vitra) | Everywhere | Fastest Vitra route |
| [ ] | Vitra professionals hub | [vitra.com › downloads](https://www.vitra.com/en-us/professionals/downloads) | Everywhere | "2D & 3D CAD data" |
| [ ] | Thonet **S 32 / S 64**, **S 33 / S 34**, **S 35** lounge, **S 533** | [thonet.de › products](https://www.thonet.de/en/all-products/detail/s-54-pf) | Z1, meeting, Z7 | CAD on each product page + media database |
| [ ] | **USM Haller** chrome-steel storage | [usm.com › architects](https://www.usm.com/en/support-for-architects-and-designers) | Z5/Z6 sample library | Configure, then download 3D |
| [ ] | **Steelcase** 3D models | [steelcase.com › 3D/CAD](https://www.steelcase.com/asia-en/resources/3d-models-cad/) | Meeting, back office | |
| [ ] | **Muuto** Linear Steel table + bench | [professionals.muuto.com](https://professionals.muuto.com/faq) | Café edge, Z7 | Login → 2D/3D files |
| [ ] | **HAY** Hee chair/stool/lounge | [hay.com › Image Bank](https://www.hay.com/) | Café, setback | Per HAY product sheets |
| [ ] | **Tolix Marais A** chair + stools (raw steel) | [Piece of3D set](https://pieceof3d.gumroad.com/l/collectionmaraispartone) | Forged café, Z5 | `paid €4.50`, native .blend; no official Tolix files exist |
| [ ] | Design Connected steel pieces: Magis **Steelwood**, HAY **Hee**, Emeco **Navy** | [Steelwood](https://www.designconnected.com/Seating/Armchairs/Steelwood-Chair_p2456) · [Hee](https://www.designconnected.com/Seating/Chairs/Hee-Chair_p791) · [Navy](https://designconnected.com/Seating/Armchairs/navy-armchair_p2705) | Z1, Z5, café | `paid`, photoreal |

---

## 3. Model libraries (account needed)

| ✓ | Library | Link | What's there |
|---|---|---|---|
| [ ] | 3D Warehouse | [3dwarehouse.sketchup.com](https://3dwarehouse.sketchup.com/) | Verified brand profiles (Vitra, Delta Light…); clearest licence for client renders |
| [ ] | Design Connected freebies | [designconnected.com/freebies](https://www.designconnected.com/freebies) | Free designer models, scaled, cm units · [official manufacturers' free list](http://www.designconnected.com/catalog/manufacturers_3d_pages/official-Manufacturers-Free-3D-Models) |
| [ ] | Dimensiva | [dimensiva.com/free-3d-models](https://dimensiva.com/free-3d-models/) | High-end designer furniture, FBX/OBJ, some .blend; Blender packs: [Free Pack 01](https://superhivemarket.com/products/free-3d-models---dimensiva--3dshaker-freepack-01) (02–04 too) |
| [ ] | Evermotion free Archmodels | [evermotion.org › Archmodels](https://evermotion.org/shop/cat/396/Archmodels/0) | Vol. 152 = 76 free designer lamps; free sample models; registered users only |
| [ ] | Architonic | [architonic.com](https://www.architonic.com/en) | Brand CAD/BIM downloads after free login; search *Kusch+Co* (beam seating), Bene, Wilkhahn `check` |
| [ ] | BIMobject | [bimobject.com](https://www.bimobject.com/) | USM, Hunter Douglas ceilings, many brands |
| [ ] | pCon.catalog | [catalogs.pcon-solutions.com](https://catalogs.pcon-solutions.com/) | Arper, Muuto, USM and others |
| [ ] | 3dsky free | [3dsky.org](https://3dsky.org/) | 3 free models per 24 h; mostly .max |
| [ ] | Blendkit (formerly BlenderKit) | [blenderkit.com](https://www.blenderkit.com/) | About 23.7k free models; add-on only |
| [ ] | Fab limited-time free | [fab.com/limited-time-free](https://www.fab.com/limited-time-free) | Rotates every 2 weeks; claim every archviz drop |

---

## 4. Steel-industry artefacts (Sketchfab, credit the author)

| ✓ | What | Link | Zone | Licence / notes |
|---|---|---|---|---|
| [ ] | **Heavy Section Rolling Mill** (Skebobruks museum scan) | [Sketchfab](https://sketchfab.com/3d-models/heavy-section-rolling-mill-80e01ff6ebc24bc9a4f784eddcfab047) | Z3 historic machine | CC-BY, about 1.4M tris (Claude decimates) |
| [ ] | **Steelworks, factory, blast furnace** (Metazeon drone scan) | [Sketchfab](https://sketchfab.com/3d-models/steelworks-factory-blast-furnace-c2c1673b1e054becb0e0253001fc59ed) | Z4 plant miniature, Z2 content | CC-BY, about 946k tris |
| [ ] | Gearbox, two-stage helical | [Sketchfab](https://sketchfab.com/3d-models/gearbox-a8a313efec1c48988f946b99b64638ad) | Z3 / Z6 | CC-BY |
| [ ] | Gearbox (conical), T-FLEX | [Sketchfab](https://sketchfab.com/3d-models/gearbox-conical-60f023924ee0456daa758eb590b6064b) | Z6 | CC-BY |
| [ ] | Typical steel connection details | [Sketchfab](https://sketchfab.com/3d-models/typical-steel-connection-details-c01ea88e05c54b45a7df495f2b2acf2f) | Z6 configurator | `check` licence on page |
| [ ] | steeluniversity **Steelmaking** collection | [Sketchfab collection](https://sketchfab.com/steeluniversity/collections/steelmaking-en-3719a8ad0cba428b8ff606591fcbe3bf) | Z4 miniatures, Z6 | `check`: may be view-only; at least a modelling reference |
| [ ] | Sketchfab **Museums** collection (388 scans) | [Sketchfab](https://sketchfab.com/Sketchfab/collections/museums-a2dbe67aaa85476e96a9b4788d185cb0) | Z3, Z7 | Browse for CC-BY industrial heritage |

> 💡 **Shortcut:** give Claude a Sketchfab API token (Sketchfab › Settings › Password & API). Claude can then pull all the CC-BY picks through Sketchfab's official download API and log the credits. That's allowed; scraping isn't.

---

## 5. Lighting: IES photometry + fixture models (the biggest realism gain)

| ✓ | What | Link | Use |
|---|---|---|---|
| [ ] | **ERCO** complete IES/LDT archive | [download.erco.com](https://download.erco.com/en/planning_luminaire/ies) | Parscan / Pollux / Eclipse spots on artefacts, Quintessence downlights |
| [ ] | **Delta Light**: one-click bulk of all LDT + IES files | [technical downloads](https://www.deltalight.com/en/my-deltalight/technical-downloads) | Every fixture family |
| [ ] | **Delta Light** planning files (per product: IES, 3D, Revit) | [planning files](https://deltalight.com/en/download/planning-files) | 3D fixture bodies (450+ also on 3D Warehouse) |
| [ ] | **iGuzzini** per-product IES/LDT/3D | [Laser Blade example](https://iguzzini.com/cn/2180) | Linear downlights in slat ceilings; search Palco spots |
| [ ] | **Flos** Professional Space | [professional.flos.com](https://professional.flos.com/en/global/catalogs/architectural/) | Light Shadow Pro downlights, accents |
| [ ] | **Artemide** all-range Eulumdat zip | [artemide.com/en/download](https://www.artemide.com/en/download) | Decorative + architectural |
| [ ] | **IES Library** (90k+ files) | [ieslibrary.com](https://ieslibrary.com/) | Gap filler; free key expires in 15 min |
| [ ] | **Acuity** IES downloads | [acuitybrands.ca](https://acuitybrands.ca/resources/technical-resources/ies-downloads) | Cove / linear LED |

---

## 6. Materials and textures (manufacturer high-res)

| ✓ | What | Link | Use |
|---|---|---|---|
| [ ] | **Kvadrat**: tileable images + **PBR materials** on product pages | [Remix 3](https://www.kvadrat.dk/en/products/upholstery/2968-remix-3) · [Hallingdal 65](https://www.kvadrat.dk/en/products/upholstery/1000-hallingdal-65) | Lounge upholstery, acoustic panels |
| [ ] | **Margraf** marble libraries (Italian marble maker) | [downloadarea.margraf.it](https://downloadarea.margraf.it) (or via [margraf.it](https://www.margraf.it/)) | Pale stone floors, reception desk top (Contemporary) |
| [ ] | **mtextur** (10k+ manufacturer materials, e.g. Interface carpet tiles) | [mtextur.com](https://www.mtextur.com/materials/60503?locale=en) | Carpet in meeting room, floors, walls `check` |
| [ ] | **Syncronia** facade/cladding/masonry textures | [syncronia.com](https://syncronia.com/en/download-3d-textures-claddings-facades-masonry) | Charcoal mineral walls (Forged) |
| [ ] | **EGGER** decor data (wood/stone decors) | [EGGER textures FAQ](https://support.egger.com/hc/en-us/articles/360001075438-Do-you-offer-information-about-Surface-Textures) | Oak panels; log in to myEGGER for decor data / CAD packages `check` |
| [ ] | **Poliigon** free tier + Blender add-on | [poliigon.com](https://www.poliigon.com/) | Brushed stainless, travertine, oak slats. Never automate. |
| [ ] | **Adobe Substance 3D Assets** (about 175 free) | [substance3d.adobe.com/assets](https://substance3d.adobe.com/assets) | Blackened steel, bronze patina (Forged) |
| [ ] | **Textures.com** daily credits | [textures.com](https://www.textures.com/) | Gap filler |
| [ ] | **ShareTextures** | [sharetextures.com](https://www.sharetextures.com/) | Stone, wood, fabric (manual only) |
| [ ] | **Fab / Megascans** | [fab.com](https://www.fab.com/) | Paid since 2025; anything claimed before 2025 still usable |

---

## 7. AV and tech hardware

| ✓ | What | Link | Notes |
|---|---|---|---|
| [ ] | **Genelec** BIM objects (installed-sound 4000 series) | [Genelec](https://www.genelec.com/-/news/bim-objects-for-genelec-installed-sound-models-now-available) | Ceiling/wall speakers for zone audio; downloads on product pages |
| [ ] | **LG** commercial display BIM library (incl. transparent OLED, LED) | [lg.com BIM library](https://www.lg.com/us/business/commercial-display/bim-library) | **Revit only.** Grab it only if someone can export FBX from Revit |
| [ ] | 3D Warehouse brand search: Samsung, LG, Sony, Shure, Chief, Peerless-AV | [3D Warehouse](https://3dwarehouse.sketchup.com/) | `check` per model |

Sony's Spatial Reality Display, the touch table, the LED walls and the transparent LED strips have no official 3D files, so **Claude models them** from published dimensions.

---

## 8. People

| ✓ | What | Link | Notes |
|---|---|---|---|
| [ ] | **RenderPeople** free posed/rigged/animated | [renderpeople.com/free-3d-people](https://renderpeople.com/free-3d-people/) | Blender/FBX/GLB; commercial viz OK; desktop only |
| [ ] | **RenderPeople Posed** (business wear) | [renderpeople.com/posed](https://renderpeople.com/posed/) | `paid`; 6 to 10 suited figures; look for South Asian scans |
| [ ] | **MetaHuman** (Epic) | [metahuman.com/license](https://www.metahuman.com/license) | Now usable in Blender too (via the free [Character DNA add-on](https://digitalproduction.com/2026/07/22/character-dna-goes-free/)); free under $1M revenue, UE seat licence above. Best for the Unreal walkthrough |
| [ ] | **Mixamo** animated walkers | [mixamo.com](https://www.mixamo.com/) | Adobe ID |
| [ ] | **AXYZ metropoly** | [axyz-design.com](https://secure.axyz-design.com/en/metropoly) | `paid`, top-tier scans, royalty-free |

---

## 9. Plants

| ✓ | What | Link | Notes |
|---|---|---|---|
| [ ] | **Globe Plants**: indoor & office plant packs | [globeplants.com](https://globeplants.com/) | `paid` (the old $3 Gumroad volumes are offline); Blender + FBX formats |
| [ ] | **Botaniq** | [polygoniq.com/3d/botaniq](https://polygoniq.com/3d/botaniq/) | `paid` Starter $1.99 / Lite ≈ $50 / Full ≈ $129 |
| [ ] | **DOSCH Indoor Plants** (66 potted plants) | [doschdesign.com](https://doschdesign.com/products/3d/indoor-plants.html) | `paid` ≈ €39 |
| [ ] | **PlantCatalog areca palm** (62 variants) | [Sketchfab](https://sketchfab.com/models/25ad87ca263c45e99739175acfb225ec) | CC-BY, render only |

---

## 10. Exact dimensions: standards, sections, maps

| ✓ | What | Link | Why |
|---|---|---|---|
| [ ] | **BIS IS 808** (beam/channel/angle sections), **IS 1786** (TMT), **IS 2062** | [BIS: how to download](https://www.bis.gov.in/wp-content/uploads/2021/09/STEPS-TO-DOWNLOAD-INDIAN-STANDARDS.pdf) | Free after registering; exact section sizes for Z5/Z6 samples. Keep the PDFs internal |
| [ ] | **ArcelorMittal** sections (DWG) | [constructalia › CAD](https://constructalia.arcelormittal.com/en/tools/cad) | Cross-check section profiles |
| [ ] | **Survey of India** state/district maps | [onlinemaps.surveyofindia.gov.in](https://onlinemaps.surveyofindia.gov.in/ProductSearch.aspx) | Only if Z4 needs state detail (Claude has the national map) |
| [ ] | **SAIL logo + brand guide** | from SAIL's corporate comms | Use the official vector, never a web rip |

---

## 11. Skip these

- **"Stainless Steel Coil" (IM-SEGEV, Sketchfab):** non-commercial and no-derivatives. Claude builds coils instead.
- **MBD_VR blast furnace:** CC-BY-NC-SA. **MRowa "Steel Works":** CC-BY-SA, a share-alike risk.
- **TurboSquid / RenderHub "Editorial use only"** models, **free3d mirrors** of Evermotion or 3dsky packs.
- **Chaos Cosmos:** only works inside Chaos renderers, not Blender.
- **3D-FRONT / 3D-FUTURE, CubiCasa5k, IKEA 3D dataset:** research or non-commercial only.

---

## 12. Not yours: Claude downloads these automatically

Claude checked both APIs from this session on 23 Oct 2026, and both respond. No account is needed.

**Poly Haven (CC0)**: 521 models, 869 textures, 301 indoor HDRIs
- Seating: `metal_stool_01/02/03`, `modern_arm_chair_01`, `mid_century_lounge_chair`, `sofa_02/03`, `Ottoman_01`, `bar_chair_round_01`, `modular_street_seating`
- Lighting: `modern_ceiling_lamp_01`, `desk_lamp_arm_01`, `hanging_industrial_lamp`, `industrial_wall_sconce`, `brass_diya_lantern`
- Plants: `potted_plant_01/02/04`, `anthurium_botany_01`, `calathea_orbifolia_01`, `pachira_aquatica_01`, `fern_02`
- Z7 worker tools and industrial props: `bench_vice_01`, `drill_press_01`, `metal_tool_chest`, `adjustable_wrench`, `combination_wrench`, `industrial_microscope`
- Textures: `metal_plate`, `metal_plate_02`, `blue_metal_plate`, `rusty_metal*` (Forged), `marble_01`, `grey_cartago_01/03`, `terrazzo_tiles`, `brushed_concrete*`, 43 fabrics

**ambientCG (CC0)**
- 248 metals (incl. `Metal048B` fingerprinted metal), `Fingerprints001–009`, `Smear002–004`, scratched metals
- 85 marble/onyx, 15 travertine, 32 terrazzo, 15 granite
- 328 wood, 117 fabric + 28 carpet, 56 leather, 39 plaster

**Datasets and data**
- **Amazon Berkeley Objects** (CC-BY): 7,900+ retail furniture GLBs
- **Google Scanned Objects** (CC-BY): cups, bottles, desk props
- **Objaverse** CC0/CC-BY subset
- **Survey of India Political Map 2025** (official PDF) + **Copernicus DEM** for the Z4 relief map
- **Google Fonts** Noto Devanagari for Hindi signage

**Needs one thing from you**
- **Smithsonian 3D** (CC0): a free api.data.gov key
- **Sketchfab CC-BY picks**: your API token (see the shortcut in section 4)

**Built procedurally by Claude**
- Steel coils, IRS 52 kg / UIC 60 rail sections, IS 808 sections, plates, pipes, TMT bars
- The Legacy Tree structure, vitrines, plinths, reception desk
- AV hardware (SRD, touch table, LED walls), slat ceilings, the building shell
- LDT → IES conversion and the licence manifest
