"""Build the SAIL Experience Centre asset download list PDF."""
import sys
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT = sys.argv[1]
F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("Sans", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Sans-B", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Serif-B", F + "DejaVuSerif-Bold.ttf"))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-B", italic="Sans", boldItalic="Sans-B")

NAVY = colors.HexColor("#1d2a4a")
GOLD = colors.HexColor("#c9a227")
TEAL = colors.HexColor("#1b8fa6")
LIGHT = colors.HexColor("#f2f4f8")
GREEN = colors.HexColor("#2e7d4f")
GREY = colors.HexColor("#5b6375")

st = {
    "title": ParagraphStyle("t", fontName="Serif-B", fontSize=24, leading=29, textColor=NAVY),
    "kicker": ParagraphStyle("k", fontName="Sans-B", fontSize=8.5, leading=11, textColor=GOLD),
    "sub": ParagraphStyle("s", fontName="Sans", fontSize=10, leading=14, textColor=GREY),
    "h1": ParagraphStyle("h1", fontName="Serif-B", fontSize=16, leading=20, textColor=NAVY, spaceBefore=4, spaceAfter=4),
    "h2": ParagraphStyle("h2", fontName="Sans-B", fontSize=10.5, leading=14, textColor=TEAL, spaceBefore=8, spaceAfter=4),
    "body": ParagraphStyle("b", fontName="Sans", fontSize=8.8, leading=12.2, textColor=colors.black),
    "cell": ParagraphStyle("c", fontName="Sans", fontSize=7.9, leading=10.2),
    "cellb": ParagraphStyle("cb", fontName="Sans-B", fontSize=8, leading=10.4, textColor=NAVY),
    "head": ParagraphStyle("hd", fontName="Sans-B", fontSize=7.8, leading=10, textColor=colors.white),
    "note": ParagraphStyle("n", fontName="Sans", fontSize=7.6, leading=10, textColor=GREY),
    "box": ParagraphStyle("x", fontName="Sans", fontSize=8.5, leading=11.8),
}


def L(url, text=None):
    return f'<link href="{url}" color="#1b6fa6"><u>{text or url}</u></link>'


def P(t, s="cell"):
    return Paragraph(t, st[s])


PAGE_W = landscape(A4)[0] - 30 * mm


def table(rows, cols=("", "What to grab", "Where (click)", "Zone / use", "Notes"),
          widths=(7, 62, 62, 52, 84), check=True):
    w = [x * mm for x in widths]
    scale = PAGE_W / sum(w)
    w = [x * scale for x in w]
    data = [[P(c, "head") for c in cols]]
    for r in rows:
        data.append(([P("☐", "cell")] if check else []) + [P(r[0], "cellb")] + [P(x) for x in r[1:]])
    t = Table(data, colWidths=w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#d5d9e2")),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def callout(paras, color=GOLD, bg=colors.HexColor("#fbf6e6")):
    t = Table([[[P(p, "box") for p in paras]]], colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def footer(c, doc):
    c.saveState()
    c.setFont("Sans", 7)
    c.setFillColor(GREY)
    c.drawString(15 * mm, 9 * mm, "KiXR  |  SAIL Experience Centre, Lodhi Road  •  Asset download list  •  links checked 23 Oct 2026")
    c.drawRightString(landscape(A4)[0] - 15 * mm, 9 * mm, str(doc.page))
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.line(15 * mm, landscape(A4)[1] - 11 * mm, 45 * mm, landscape(A4)[1] - 11 * mm)
    c.restoreState()


s = []
# ---------------------------------------------------------------- cover
s += [P("SAIL  |  EXPERIENCE CENTRE VISUALISATION", "kicker"), Spacer(1, 4),
      P("Asset Download List", "title"), Spacer(1, 4),
      P("Part A: what only you can download (accounts, logins, manual clicks). "
        "Part B: what Claude fetches or builds itself. Tick the boxes as you go.", "sub"),
      Spacer(1, 10)]

s.append(P("How to use this", "h2"))
how = [
    ["Part A: you", "Everything here needs <b>your</b> account, a login, a purchase or a manual click, or the site's terms ban scripts and bots. "
     "Claude cannot and should not automate these."],
    ["Part B: Claude", "Public APIs and open data (CC0 / CC-BY / public domain), plus everything built procedurally in Blender. Don't spend your time on these."],
    ["Where files go", "Drop each download, still zipped, into <b>assets/inbox/&lt;source&gt;/&lt;item&gt;/</b> "
     "(e.g. assets/inbox/knoll/barcelona-chair/). Claude handles conversion, real-world scale, origin, materials, bevels and the licence manifest."],
    ["Pick this format", "FBX → OBJ → 3DS → SKP → DWG 3D, in that order. <b>Skip Revit .rfa</b> (no Blender import). "
     "Lighting: .ies preferred, .ldt is fine (Claude converts LDT → IES)."],
    ["Link status", "Every link was opened in search on 23 Oct 2026. Where a row says <i>search on page</i>, the portal is confirmed but the exact product page was not."],
]
s.append(table(how, cols=("Step", "Detail"), widths=(30, 230), check=False))
s.append(Spacer(1, 8))
s.append(callout([
    "<b>On 'internal only'.</b> Internal use doesn't make pirated packs, research-only datasets or non-commercial (NC) models usable. "
    "The renders also go to SAIL inside a pitch, which counts as commercial work. Everything in this list is legitimately usable for that. "
    "With manufacturer files: put them in scenes and renders freely, but never pass the model files themselves on to anyone.",
    "<b>The big idea:</b> SAIL is a steel company, so make the furniture steel too. Barcelona, Bertoia, Prouvé, Breuer/Stam cantilevers, "
    "the Eames Wire chair and USM Haller are all design-history steel. Chrome and satin pieces suit Contemporary Steel; "
    "raw and blackened pieces (Tolix, Prouvé) suit Forged Heritage.",
]))
s.append(Spacer(1, 8))
s.append(P("Accounts to create (one sitting, about 20 minutes)", "h2"))
acc = [
    ["Trimble ID", L("https://3dwarehouse.sketchup.com/", "3D Warehouse"), "Official brand models, including Vitra"],
    ["myERCO", L("https://download.erco.com/en/planning_luminaire/ies", "download.erco.com"), "Full IES archive"],
    ["Sketchfab", L("https://sketchfab.com/", "sketchfab.com"), "Industrial artefact scans, palms"],
    ["Design Connected, Dimensiva", L("https://www.designconnected.com/freebies", "designconnected.com") + ", " + L("https://dimensiva.com/free-3d-models/", "dimensiva.com"), "Free designer models + paid steel pieces"],
    ["Muuto Professionals", L("https://professionals.muuto.com/faq", "professionals.muuto.com"), "2D/3D files"],
    ["Epic / Fab", L("https://www.fab.com/limited-time-free", "fab.com"), "Bi-weekly free drops"],
    ["Adobe ID", L("https://www.mixamo.com/", "Mixamo") + " + " + L("https://substance3d.adobe.com/assets", "Substance 3D Assets"), "Animated people, free materials"],
    ["Poliigon, 3dsky, BIMobject, pCon", L("https://www.poliigon.com/", "poliigon.com") + ", " + L("https://3dsky.org/", "3dsky.org") + ", " + L("https://www.bimobject.com/", "bimobject.com") + ", " + L("https://catalogs.pcon-solutions.com/", "pCon.catalog"), "Materials and brand catalogues"],
]
s.append(table(acc, cols=("", "Account", "Site", "Why"), widths=(7, 45, 100, 120)))

# ---------------------------------------------------------------- part A
s += [PageBreak(), P("PART A: ONLY YOU CAN DOWNLOAD", "kicker"), P("A1. Steel furniture: manufacturer portals", "h1")]
a1 = [
    ["Knoll: Barcelona chair, stool, table, couch",
     L("https://www.knoll.com/design-plan/resources/furniture-symbols/showcase-symbols?searchtext=Barcelona", "knoll.com › Furniture Symbol Library › Barcelona"),
     "Z1 VIP lounge / reception", "Chromed flat-bar steel (Mies, 1929): the most famous steel chair there is. Take the SketchUp file."],
    ["Knoll: MR chair/chaise, Bertoia Diamond + side chair + stools, Platner",
     L("https://www.knoll.com/design-plan/resources/furniture-symbols/showcase-symbols", "knoll.com › Furniture Symbol Library"),
     "Z1 lounge, Z5 touch-table stools, Z7", "<i>Search on page</i> for MR, Bertoia, Platner. Bertoia = welded steel rod; Platner = nickel-plated steel rod."],
    ["Herman Miller: Eames Wire Chair (all bases)",
     L("https://www.hermanmiller.com/resources/3d-models-and-planning-tools/product-models/individual/eames-wire-chair-wire-base-upholstered-seat/", "hermanmiller.com › Eames Wire Chair"),
     "Z5 / café edge", "Steel wire. Revit, SketchUp, AutoCAD 2D/3D: take SketchUp. Sibling pages cover dowel and 4-leg bases."],
    ["Herman Miller: Eames Tandem Sling Seating, Eames Aluminum Group",
     L("https://www.hermanmiller.com/en_in/resources/3d-models-and-planning-tools/", "hermanmiller.com (India) › 3D Models & Planning Tools"),
     "Passage waiting, meeting room", "<i>Search on page.</i> Tandem Sling is airport-style beam seating, ideal along the passage."],
    ["Vitra: Standard chair (Jean Prouvé)",
     L("https://www.vitra.com/en-un/product/standard", "vitra.com › Standard › CAD data"),
     "Meeting room, Z7, Forged Heritage", "Folded sheet steel. Same portal: <i>search</i> Fauteuil Direction, EM Table, Potence lamp, Aluminium Chairs."],
    ["Vitra: official 3D Warehouse profile (155 models)",
     L("https://3dwarehouse.sketchup.com/by/vitra", "3dwarehouse.sketchup.com/by/vitra"),
     "Everywhere", "The fastest Vitra route. SKP; Claude converts."],
    ["Vitra: Professionals downloads hub",
     L("https://www.vitra.com/en-us/professionals/downloads", "vitra.com › Professionals › Downloads"),
     "Everywhere", "'2D & 3D CAD Data' category."],
    ["Thonet: S 32 / S 64 (Breuer), S 33 / S 34 (Mart Stam), S 35 lounge, S 533",
     L("https://www.thonet.de/en/all-products/detail/s-54-pf", "thonet.de › All products (e.g. S 54 PF)"),
     "Z1 lounge, meeting room, Z7", "Tubular-steel Bauhaus cantilevers. CAD on each product page; bulk CAD in Thonet's media database."],
    ["USM Haller: modular chrome-steel storage",
     L("https://www.usm.com/en/support-for-architects-and-designers", "usm.com › Architects & designers"),
     "Z5/Z6 sample library, low vitrines", "Configure to size, then download 3D. Also on BIMobject and pCon."],
    ["Steelcase: 3D Models / CAD",
     L("https://www.steelcase.com/asia-en/resources/3d-models-cad/", "steelcase.com › 3D Models/CAD (Asia)"),
     "Meeting room, back office", "Steel-frame tables and seating."],
    ["Muuto: Linear Steel table + bench",
     L("https://professionals.muuto.com/faq", "professionals.muuto.com"), "Café edge, Z7", "Log in, then the 2D/3D files page."],
    ["HAY: Hee chair, stool, lounge (steel)",
     L("https://www.hay.com/", "hay.com › Image Bank (2D/3D files)"), "Café edge, setback", "Per HAY product sheets the 3D files are in the Image Bank."],
    ["Tolix Marais A chair + stools (raw steel)",
     L("https://pieceof3d.gumroad.com/l/collectionmaraispartone", "Piece of3D Marais set (Gumroad, €4.50)"),
     "Forged Heritage café, Z5", "No official Tolix files. This set ships a native .blend."],
]
s.append(table(a1))

s += [Spacer(1, 6), P("A2. Model libraries (account needed)", "h1")]
a2 = [
    ["3D Warehouse", L("https://3dwarehouse.sketchup.com/", "3dwarehouse.sketchup.com"), "All zones",
     "Prefer verified brand profiles. Clearest licence for client renders; daily caps on free accounts."],
    ["Design Connected: Freebies", L("https://www.designconnected.com/freebies", "designconnected.com/freebies"), "All zones",
     "Free designer models, accurately scaled, cm units. Also " + L("http://www.designconnected.com/catalog/manufacturers_3d_pages/official-Manufacturers-Free-3D-Models", "official manufacturers' free list") + "."],
    ["Design Connected: paid steel pieces worth buying",
     L("https://www.designconnected.com/Seating/Armchairs/Steelwood-Chair_p2456", "Magis Steelwood") + ", " +
     L("https://www.designconnected.com/Seating/Chairs/Hee-Chair_p791", "HAY Hee") + ", " +
     L("https://designconnected.com/Seating/Armchairs/navy-armchair_p2705", "Emeco Navy"), "Z1, Z5, café",
     "Photoreal models. One purchase gets every format."],
    ["Dimensiva", L("https://dimensiva.com/free-3d-models/", "dimensiva.com/free-3d-models"), "All zones",
     "Free account. FBX/OBJ, some with .blend. Blender packs: " + L("https://superhivemarket.com/products/free-3d-models---dimensiva--3dshaker-freepack-01", "Dimensiva + 3Dshaker Free Pack 01") + " (packs 02 to 04 too)."],
    ["3dsky free", L("https://3dsky.org/", "3dsky.org"), "Fill", "3 free models per 24 h. Mostly .max; check who uploaded it."],
    ["BIMobject", L("https://www.bimobject.com/", "bimobject.com"), "USM, brands", "Official interfaces only, no bulk."],
    ["pCon.catalog", L("https://catalogs.pcon-solutions.com/", "pCon.catalog"), "Arper, Muuto, USM", "Free account; manufacturer CAD."],
    ["Blendkit (formerly BlenderKit)", L("https://github.com/BlenderKit/Blendkit", "Blendkit add-on"), "Fill, plants",
     "Free plan about 23.7k models. Through the add-on only, no scripts."],
    ["Fab limited-time free", L("https://www.fab.com/limited-time-free", "fab.com/limited-time-free"), "Anything",
     "Rotates every 2 weeks; claim archviz items whenever you see them. Fab Standard licence works in any DCC."],
]
s.append(table(a2))

s += [PageBreak(), P("PART A: ONLY YOU CAN DOWNLOAD", "kicker"), P("A3. Steel and industrial artefacts (Sketchfab, credit the author)", "h1")]
a3 = [
    ["Heavy Section Rolling Mill: real museum scan",
     L("https://sketchfab.com/3d-models/heavy-section-rolling-mill-80e01ff6ebc24bc9a4f784eddcfab047", "Skebobruks museum on Sketchfab"),
     "Z3 Legacy Tree historic equipment", "<b>Best find.</b> CC-BY, about 1.4M tris: the 'authentic machine' in front of the tree. Claude decimates it."],
    ["Gearbox, two-stage helical", L("https://sketchfab.com/3d-models/gearbox-a8a313efec1c48988f946b99b64638ad", "Steven Samuel on Sketchfab"),
     "Z3 / Z6", "CC-BY, about 1.2M tris. Works as a cutaway artefact."],
    ["Gearbox (conical)", L("https://sketchfab.com/3d-models/gearbox-conical-60f023924ee0456daa758eb590b6064b", "T-FLEX CAD on Sketchfab"),
     "Z6 configurator", "CC-BY."],
    ["Typical Steel Connection Details", L("https://sketchfab.com/3d-models/typical-steel-connection-details-c01ea88e05c54b45a7df495f2b2acf2f", "ntklong.501 on Sketchfab"),
     "Z6 configurator", "Beam-column joints. <i>Check the licence on the page.</i>"],
    ["Areca palm (PlantCatalog, 62 variants)", L("https://sketchfab.com/models/25ad87ca263c45e99739175acfb225ec", "PlantCatalog areca on Sketchfab"),
     "Planters, Z1/Z2", "CC-BY, render only; never bundle the files. From your L&amp;T Exteriors doc."],
    ["SKIP: 'Stainless Steel Coil' (IM-SEGEV)", L("https://sketchfab.com/3d-models/stainless-steel-coil-408da6a9b2f04a6f92e3a0f305df53de", "Sketchfab"),
     "n/a", "Non-commercial / no-derivatives. Claude builds coils procedurally instead (Part B)."],
]
s.append(table(a3))

s += [Spacer(1, 6), P("A4. Lighting photometry: IES / LDT (the biggest realism gain)", "h1")]
a4 = [
    ["ERCO: complete IES/LDT archive", L("https://download.erco.com/en/planning_luminaire/ies", "download.erco.com"),
     "Every artefact, every zone", "The museum standard. Free myERCO account gets the full archive. Parscan / Pollux / Eclipse track spots, Quintessence downlights."],
    ["iGuzzini: per-product IES, LDT, Revit", L("https://iguzzini.com/cn/2180", "iguzzini.com › Laser Blade (e.g. 2180)"),
     "Slat ceilings (Contemporary)", "Download section on each product page. <i>Search</i> Palco for spots."],
    ["Flos Professional Space", L("https://professional.flos.com/en/global/catalogs/architectural/", "professional.flos.com › Architectural"),
     "Downlights, accents", "LDT/IES per product (Light Shadow Pro and others)."],
    ["Artemide: whole range as Eulumdat", L("https://www.artemide.com/en/download", "artemide.com/en/download"),
     "Decorative + architectural", "One zip of .ldt files; Claude converts them to IES."],
    ["IES Library", L("https://ieslibrary.com/", "ieslibrary.com"), "Gap filler",
     "90k+ files by manufacturer. Free key expires in 15 min, so download by hand."],
    ["Acuity Brands IES downloads", L("https://acuitybrands.ca/resources/technical-resources/ies-downloads", "acuitybrands.ca › IES downloads"),
     "Cove / linear LED", "For the amber and white cove lighting in both themes."],
]
s.append(table(a4))

s += [PageBreak(), P("PART A: ONLY YOU CAN DOWNLOAD", "kicker"), P("A5. People, plants, materials, maps", "h1")]
a5 = [
    ["RenderPeople: free posed, rigged, animated", L("https://renderpeople.com/free-3d-people/", "renderpeople.com/free-3d-people"),
     "Delegation scenes", "Blender/FBX/GLB. Commercial visualisation OK. Desktop only."],
    ["RenderPeople Posed (paid): business wear", L("https://renderpeople.com/posed/", "renderpeople.com/posed"),
     "Z1, Z2 hero shots", "Buy 6 to 10 suited figures to match the concept renders; look for South Asian scans."],
    ["Mixamo: animated walkers", L("https://www.mixamo.com/", "mixamo.com"), "Unreal walkthrough", "Adobe ID; royalty-free in renders."],
    ["Botaniq (paid)", L("https://polygoniq.com/3d/botaniq/", "polygoniq.com › botaniq"), "All planters",
     "Starter $1.99 / Lite about $50 / Full about $129. Includes houseplants. The one purchase that moves realism most."],
    ["Poliigon: free tier + add-on", L("https://www.poliigon.com/", "poliigon.com"), "Stainless, travertine, oak slats",
     "Never automate: the terms ban scripts."],
    ["Adobe Substance 3D Assets", L("https://substance3d.adobe.com/assets", "substance3d.adobe.com/assets"), "Forged Heritage",
     "About 175 free with an Adobe ID. Blackened steel, bronze patina."],
    ["Textures.com", L("https://www.textures.com/", "textures.com"), "Gap filler", "Daily free credits; scripts banned."],
    ["ShareTextures", L("https://www.sharetextures.com/", "sharetextures.com"), "Stone, wood", "Manual download only."],
    ["Survey of India: state maps / boundary database", L("https://onlinemaps.surveyofindia.gov.in/ProductSearch.aspx", "onlinemaps.surveyofindia.gov.in"),
     "Z4 relief map (detail)", "Sign-in and cart. Needed only for state or district detail; Claude fetches the national map (B1)."],
]
s.append(table(a5))
s.append(Spacer(1, 10))
s.append(callout([
    "<b>Order of attack:</b> (1) the ERCO archive and the Knoll + Herman Miller + Vitra chairs; (2) the Sketchfab rolling mill; "
    "(3) RenderPeople free figures and Botaniq Lite. That alone lifts every zone. Drop them in assets/inbox/ and Claude takes it from there.",
], color=TEAL, bg=colors.HexColor("#e9f4f6")))


# ---------------------------------------------------------------- part B
s += [PageBreak(), P("PART B: CLAUDE FETCHES OR BUILDS", "kicker"),
      P("B1. Scripted downloads: public APIs and open data", "h1")]
b1 = [
    ["Poly Haven (CC0)", L("https://polyhaven.com/", "polyhaven.com") + " API", "All zones",
     "HDRIs (indoor, studio, sky), metal, concrete, marble and wood textures, 521 models, and houseplants potted_plant_01/02/04, anthurium, calathea, pachira, fern."],
    ["ambientCG (CC0)", L("https://ambientcg.com/", "ambientcg.com") + " API v3", "All surfaces",
     "Brushed and sheet metal, metal plates, concrete, terrazzo, marble, plus <b>fingerprint, smudge and imperfection sets</b> (what sells satin stainless)."],
    ["Amazon Berkeley Objects (CC-BY)", L("https://amazon-berkeley-objects.s3.amazonaws.com/index.html", "ABO dataset (S3)"), "Back office, café",
     "7,900+ retail furniture and home-goods GLBs with 4K PBR."],
    ["Google Scanned Objects (CC-BY)", "Hugging Face mirror", "Reception, café props", "1,030 scanned small goods: cups, bottles, desk items."],
    ["Survey of India: Political Map of India 2025", L("https://surveyofindia.gov.in/webroot/UserFiles/files/Polmap-eng-2025.pdf", "surveyofindia.gov.in (PDF)"),
     "Z4 relief map outline", "Official boundary. SAIL is a central PSU, so the map must match it exactly."],
    ["Copernicus DEM GLO-90", "AWS Open Data (no login)", "Z4 relief map", "Real elevation for the illuminated India relief, clipped to the official outline."],
    ["Google Fonts (OFL)", "github.com/google/fonts", "Signage, placards", "Noto Sans/Serif Devanagari for the Hindi SAIL wordmark and signage, plus Latin faces."],
    ["Objaverse CC0/CC-BY subset", "pip objaverse", "Industrial props", "Filtered by licence; attribution logged."],
]
s.append(table(b1, cols=("Source", "Access", "Zone / use", "What Claude pulls"), widths=(55, 55, 45, 120), check=False))

s += [Spacer(1, 6),
      P("B2. Built procedurally in Blender, to real SAIL product dimensions", "h1")]
b2 = [
    ["Steel coils (HR / CR / galvanised)", "Z1 welcome anchor, Z5", "Parametric width, ID/OD, banding straps, edge sheen, coil-end marking."],
    ["Rail section: IRS 52 kg / UIC 60 profile", "Z2 Living Stories plinth", "Bhilai rail profile, mill-scale and polished-face variants."],
    ["Structural sections: ISMB / ISMC / angles per IS 808, plates, pipes, TMT bars", "Z5 sample library, Z6 configurator", "Exact section tables; cut faces with machining marks."],
    ["Legacy Tree branching steel structure", "Z3", "Bronze-toned (Forged) and satin (Contemporary) versions, digital frames on branches."],
    ["Vitrines, plinths, benches, reception desk, kiosks, ceilings", "All zones", "Stainless or blackened steel, low-iron glass, backlit bases; wood-slat ceiling, acoustic panels, coves, 12 ft clear height."],
    ["AV hardware from published dimensions", "Z2, Z5, Z6", L("https://pro.sony/ue_US/products/spatial-reality-displays/elf-sr2", "Sony ELF-SR2 SRD") +
     ", touch table, LED wall, P2.5 transparent LED strips, digital frames."],
    ["Building shell from the Option 4 plan", "Whole site", "The plan is not to scale; confirmed wall lengths are needed before this is final."],
    ["LDT → IES conversion + licence manifest", "Pipeline", "Every file from Part A logged with source, licence and date; licence check before final renders."],
]
s.append(table(b2, cols=("Asset", "Zone", "Notes"), widths=(95, 55, 120), check=False))
doc = SimpleDocTemplate(OUT, pagesize=landscape(A4), leftMargin=15 * mm, rightMargin=15 * mm,
                        topMargin=15 * mm, bottomMargin=15 * mm,
                        title="SAIL Experience Centre: Asset Download List", author="KiXR")
doc.build(s, onFirstPage=footer, onLaterPages=footer)
print("ok", OUT)
