# Viewers

Two static, browser-based viewers. Both are fully self-contained — all JS
libraries are vendored into the repo, so no network access is needed at
view time, only a static file server (the browser's `fetch()`/module
loader won't load local files over `file://`, so you do need *some* server,
even a trivial one).

## Run either viewer

From the repo root:

```bash
python3 -m http.server 8080
```

Then open:

- CAD viewer: http://localhost:8080/viewers/cad-viewer/
- PCB viewer: http://localhost:8080/viewers/pcb-viewer/

## cad-viewer

Loads `cad/stl/flashlight_body_v1.stl` with three.js (`STLLoader` +
`OrbitControls`, vendored under `vendor/three/`) and displays the model's
bounding-box width/height/depth on screen.

## pcb-viewer

Fetches the real Gerber + Excellon files from `pcb/gerbers/` and renders
them client-side into SVG using `pcb-stackup` (vendored UMD build under
`vendor/pcb-stackup.min.js` — see `package.json` for how it was obtained
via `npm install`). Renders top and bottom sides. Carries the same
not-DRC-checked caveat as `pcb/README.md`.
