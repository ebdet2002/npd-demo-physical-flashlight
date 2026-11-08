import * as THREE from "three";
import { STLLoader } from "./vendor/three/examples/jsm/loaders/STLLoader.js";
import { OrbitControls } from "./vendor/three/examples/jsm/controls/OrbitControls.js";

const holder = document.getElementById("canvas-holder");
const statusEl = document.getElementById("status");
const dimX = document.getElementById("dim-x");
const dimY = document.getElementById("dim-y");
const dimZ = document.getElementById("dim-z");
const select = document.getElementById("stl-select");

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0c0e);

const camera = new THREE.PerspectiveCamera(
  45,
  holder.clientWidth / holder.clientHeight,
  0.1,
  2000
);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(holder.clientWidth, holder.clientHeight);
holder.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

// Lighting: a product-shot style three-point rig.
scene.add(new THREE.AmbientLight(0xffffff, 0.5));
const key = new THREE.DirectionalLight(0xffffff, 1.2);
key.position.set(100, 150, 150);
scene.add(key);
const rim = new THREE.DirectionalLight(0x4fd1ff, 0.6);
rim.position.set(-120, -60, 80);
scene.add(rim);

// A faint grid on the "ground" for scale reference.
const grid = new THREE.GridHelper(300, 30, 0x4fd1ff, 0x1c1f26);
grid.position.y = -40;
scene.add(grid);

let mesh = null;

function loadSTL(path) {
  statusEl.textContent = "Loading STL…";
  const loader = new STLLoader();
  loader.load(
    path,
    (geometry) => {
      if (mesh) {
        scene.remove(mesh);
        mesh.geometry.dispose();
      }
      geometry.computeBoundingBox();
      geometry.computeVertexNormals();

      const material = new THREE.MeshStandardMaterial({
        color: 0xc9cdd3,
        metalness: 0.75,
        roughness: 0.35,
      });
      mesh = new THREE.Mesh(geometry, material);

      const bbox = geometry.boundingBox;
      const size = new THREE.Vector3();
      bbox.getSize(size);
      const center = new THREE.Vector3();
      bbox.getCenter(center);
      mesh.position.sub(center); // center the model at the origin

      scene.add(mesh);

      dimX.textContent = `${size.x.toFixed(2)} mm`;
      dimY.textContent = `${size.y.toFixed(2)} mm`;
      dimZ.textContent = `${size.z.toFixed(2)} mm`;
      statusEl.textContent = `Loaded ${path.split("/").pop()}`;

      // Frame the camera on the model.
      const maxDim = Math.max(size.x, size.y, size.z);
      const dist = maxDim * 2.2;
      camera.position.set(dist * 0.6, dist * 0.4, dist * 0.8);
      camera.lookAt(0, 0, 0);
      controls.target.set(0, 0, 0);
      controls.update();
    },
    undefined,
    (err) => {
      statusEl.textContent = "Failed to load STL — see console.";
      console.error(err);
    }
  );
}

select.addEventListener("change", () => loadSTL(select.value));

function onResize() {
  camera.aspect = holder.clientWidth / holder.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(holder.clientWidth, holder.clientHeight);
}
window.addEventListener("resize", onResize);

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

loadSTL(select.value);
animate();
