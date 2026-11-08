// Browser-side Gerber renderer for the flashlight driver board.
// Uses pcb-stackup (bundled locally at ./vendor/pcb-stackup.min.js, no
// network access needed at view time) to turn the real Gerber + Excellon
// files in pcb/gerbers/ into SVG renders, directly in the browser.

const GERBER_DIR = "../../pcb/gerbers/";
const FILES = [
  "flashlight_driver_v1-F_Cu.gbr",
  "flashlight_driver_v1-B_Cu.gbr",
  "flashlight_driver_v1-F_Silkscreen.gbr",
  "flashlight_driver_v1-F_Mask.gbr",
  "flashlight_driver_v1-B_Mask.gbr",
  "flashlight_driver_v1-Edge_Cuts.gbr",
  "flashlight_driver_v1.drl",
];

const statusEl = document.getElementById("status");
const boardsEl = document.getElementById("boards");

async function fetchLayer(filename) {
  const res = await fetch(GERBER_DIR + filename);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${filename}: ${res.status}`);
  }
  const gerber = await res.text();
  return { filename, gerber };
}

function renderCard(title, svgString) {
  const card = document.createElement("div");
  card.className = "board-card";
  const h2 = document.createElement("h2");
  h2.textContent = title;
  const holder = document.createElement("div");
  holder.className = "svg-holder";
  holder.innerHTML = svgString;
  card.appendChild(h2);
  card.appendChild(holder);
  boardsEl.appendChild(card);
}

async function main() {
  try {
    const layers = await Promise.all(FILES.map(fetchLayer));
    statusEl.textContent = `Fetched ${layers.length} layers, rendering…`;

    // pcb-stackup is a global (UMD build) exposing pcbStackup(layers, opts)
    const stackup = await window.pcbStackup(layers, {
      color: {
        fr4: "#1C1F26",
        cu: "#c9a86a",
        cf: "#F4F1EC",
        sm: "#263047",
        ss: "#F4F1EC",
        sp: "#c9a86a",
        out: "#4FD1FF",
      },
    });

    renderCard("Top side (F.Cu + F.Silkscreen + F.Mask)", stackup.top.svg);
    renderCard("Bottom side (B.Cu + B.Mask)", stackup.bottom.svg);

    statusEl.textContent =
      "Rendered from pcb/gerbers/ — structurally valid Gerbers, not DRC-checked (see pcb/README.md).";
  } catch (err) {
    statusEl.textContent = "Failed to render Gerbers — see console.";
    console.error(err);
  }
}

main();
