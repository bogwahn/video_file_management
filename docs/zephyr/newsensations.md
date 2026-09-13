# TamperMonkey — newsensations.com

Install / verify the Zephyr title normalizer for **New Sensations** scene pages.

## Install

1. Open TamperMonkey → **Create a new script** (or import).
2. Paste / load `userscripts/zephyr-title-normalizer.user.js` from this repo (v0.3.0+).
3. Confirm `@match` covers:
   - `*://newsensations.com/*`
   - `*://www.newsensations.com/*`
4. Save. Script should show as enabled for those hosts only.

Built-in per-host config ships for both `newsensations.com` and `www.newsensations.com`. Operator JSON overrides (TM menu) merge on top of defaults.

## What to open

Use a **tour scene / update** page, typically under:

- `/tour_ns/updates/…`
- `/updates/…`

Not the homepage grid and not DVD-only pages (`/dvds/…`) — those lack the scene actor+title block the selectors expect.

## What Bud should verify on a real page

1. Open a known scene (member or tour) with at least one performer linked under the models row.
2. TM menu → **Zephyr: Preview filename** — actors, studio compact `NewSensations`, scene title; resolution only if page exposes quality.
3. Confirm the browser tab title (and `document.title`) matches the locked grammar.

   **With resolution** (quality known on page / download link):

   `Paris.White.NewSensations.Babysitter.Paris.White.Is.On.The.Naughty.Slut.List.4k.mp4`

   **Without resolution** (tour HTML often has none — omit token, do **not** invent `.4k.`):

   `Paris.White.NewSensations.Babysitter.Paris.White.Is.On.The.Naughty.Slut.List.mp4`

4. Start Video DownloadHelper; suggested name should follow that title (DH pointed at `/Internal/Zetc/Download`).
5. After FileWatcher routes the file, missing resolution may be filled via in-repo `metadata_reader` / ffprobe enrichment (see `docs/zephyr/README.md`).
6. If the site rewrites `<title>` after load, watch for ~2s — the script resists overwrite via MutationObserver + interval.

## Selectors (durable sources)

Aligned to [stash CommunityScrapers `NewSensationsMain.yml`](https://github.com/stashapp/CommunityScrapers/blob/master/scrapers/NewSensationsMain.yml) (+ NetworkSites fallbacks):

| Field | Primary | Fallbacks |
|-------|---------|-----------|
| Title | XPath `//div[@class='indScene']/h1` | `indScene/h2`, `div.update_title`, `span.title_bar_hilite`, matching CSS |
| Actors | XPath `//div[@class='sceneTextLink']/p/span[@class='tour_update_models']/a` | bare `span.tour_update_models a`, `span.update_models a` |
| Studio | Fixed `New Sensations` → filename **`NewSensations`** (compact; no whitespace/dots) | — |
| Resolution | Quality UI / `.mp4` link text when present | Infer from href/text; else **omit** (FileWatcher may enrich later) |
| VR | `isVr: false` for this host | Path `/vr/` or explicit badges only if layout changes |

Actors are normalized to `First.Last`, joined with `.And.`, **max 3**.

## Brittle spots / risks

- **Tour vs member markup drift:** Class names (`indScene`, `tour_update_models`) are long-lived on NS network tours but member skins can differ; if Preview shows empty actors/title, use **Zephyr: Edit site selectors** for that host.
- **Resolution often missing** on public tour HTML — filename **omits** the resolution token. Prefer member download UI when quality is known; otherwise rely on watcher ffprobe enrichment after the file lands.
- **DVD / listing pages:** `indSceneDVD` / grid cards are not supported; title rewrite stays off (incomplete meta).
- **Network sister tours** (`tour_rs`, FamilyXXX, etc.) share similar markup but are **not** `@match`ed yet — scaffolding only; do not assume this script runs there.
- **Live site not fetchable from CI egress** — selectors were taken from community scrapers, not a live DOM dump in this environment. Always spot-check on Bud’s browser.
- **Duplicate actor hits:** Multiple overlapping selectors may match; script dedupes before `.And.` join.

## Related

- Grammar / pipeline: project spike plan + `docs/zephyr/README.md`
- DownloadHelper path: `docs/zephyr/download-helper.md`
