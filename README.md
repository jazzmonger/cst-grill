# CST Grill (Home Assistant integration)

Install from HACS and a **CST Grills** dashboard appears for your Chain Smoker 1-Pot grill, using the app-style
[cst-grill-card](https://github.com/jazzmonger/cst-grill-card).

This integration **creates no entities**. Your grill is already in Home Assistant through the native ESPHome
integration; this adds the card and the dashboard on top. Everything stays local (no cloud, no MQTT).

## What it does
- Serves the bundled card at `/cst_grill/cst-grill-card.js` and registers it as a dashboard resource
  (`?v=<card version>` for cache-busting). In YAML resource mode it uses `add_extra_js_url` instead.
- **CST 1-Pot only.** The config flow lists ESPHome devices that look like a CST 1-Pot:
  `select.*_cook_mode` + `sensor.*_chamber_temperature` + `number.*_smoker_set_temperature`.
- Optional **CST Grills** dashboard (sidebar) with one tab per grill: `custom:cst-grill-card` pinned by `device_id`.
  Tabs you add yourself are kept. Your other dashboards are never touched.
- Removing the last grill removes the dashboard and the resource.

## Install
1. HACS → ⋮ → Custom repositories → `https://github.com/jazzmonger/cst-grill`, category **Integration**
   (private repo: HACS needs a GitHub token with access, or make it public). Install, then restart HA.
   Manual: copy `custom_components/cst_grill` to `/config/custom_components/` and restart.
2. Settings → Devices & services → Add integration → **CST Grill** → pick your grill.
3. Open **CST Grills** in the sidebar. Hard-refresh once.

If you previously added `/local/cst-grill-card.js` by hand, remove that resource; the integration serves the card now.

## Updating the card
The card source lives in `jazzmonger/cst-grill-card`. To vendor a new build:
```
scripts/update_card.sh ../cst-grill-card   # builds, copies dist, updates CARD_VERSION
```
Then bump `manifest.json` `version`, commit, and tag a release.
