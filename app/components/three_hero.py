"""Three.js WebGL 3D Federated Learning Network Hero component.

Renders an interactive, offline-capable WebGL 3D visualization of the Federated
Learning aggregator-client topology inside a frosted-glass container using an
inlined UMD build of Three.js (r128) with a graceful 2D Canvas fallback.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import streamlit.components.v1 as components

THREE_ASSET = Path(__file__).resolve().parents[1] / "assets" / "three.min.js"


@lru_cache(maxsize=1)
def _three_js_source() -> str:
    """Read and cache the vendored UMD Three.js bundle once per process."""
    if not THREE_ASSET.exists():
        raise FileNotFoundError(
            f"Missing vendored Three.js bundle at {THREE_ASSET}."
        )
    return THREE_ASSET.read_text(encoding="utf-8")


def _format_clients(n_clients: int) -> str:
    """Format integer with dot thousand separator (e.g. 9116 -> '9.116')."""
    return f"{int(n_clients):,}".replace(",", ".")


def fl_three_hero_html(height: int = 360, n_clients: int = 9116) -> str:
    """Build the self-contained HTML document for the 3D FL topology hero."""
    h = max(240, int(height))
    clients_label = _format_clients(n_clients)
    three_src = _three_js_source()

    html = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700&display=swap');

  :root {
    --orange: #FF5A1F;
    --orange-hover: #EA580C;
    --orange-ink: #C2410C;
    --orange-soft: #FFF7ED;
    --ink: #0F172A;
    --slate: #475569;
    --muted: #64748B;
    --border-glass: rgba(255, 255, 255, 0.92);
    --border-hairline: rgba(15, 23, 42, 0.08);
    --mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    --sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  * { box-sizing: border-box; }

  html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: __HEIGHT__px;
    overflow: hidden;
    background: transparent;
    font-family: var(--sans);
    -webkit-font-smoothing: antialiased;
    user-select: none;
  }

  .fl-stage {
    position: relative;
    width: 100%;
    height: 100%;
    border-radius: 16px;
    overflow: hidden;
    background:
      radial-gradient(ellipse 62% 58% at 52% 48%, rgba(255, 90, 31, 0.14) 0%, rgba(255, 138, 91, 0.05) 38%, rgba(255, 255, 255, 0) 72%),
      radial-gradient(circle at 18% 82%, rgba(15, 23, 42, 0.035) 0%, transparent 48%),
      radial-gradient(rgba(15, 23, 42, 0.095) 1px, transparent 1px),
      rgba(255, 255, 255, 0.72);
    background-size: 100% 100%, 100% 100%, 18px 18px, 100% 100%;
    border: 1px solid var(--border-glass);
    box-shadow:
      0 0 0 1px var(--border-hairline) inset,
      0 1px 0 rgba(255, 255, 255, 0.96) inset,
      0 12px 30px -14px rgba(15, 23, 42, 0.14);
    backdrop-filter: blur(18px) saturate(175%);
    -webkit-backdrop-filter: blur(18px) saturate(175%);
    cursor: grab;
  }

  .fl-stage.is-dragging {
    cursor: grabbing;
  }

  /* Subtle top specular reflection */
  .fl-stage::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(255,255,255,0.58) 0%, rgba(255,255,255,0) 26%);
    pointer-events: none;
    z-index: 2;
  }

  #canvas-host {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    z-index: 1;
  }

  #canvas-host canvas {
    display: block;
    width: 100%;
    height: 100%;
  }

  /* Frosted HUD overlays */
  .hud {
    position: absolute;
    z-index: 4;
    pointer-events: none;
  }

  .hud-top-left {
    top: 12px;
    left: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .hud-top-right {
    top: 12px;
    right: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .hud-bottom-left {
    bottom: 12px;
    left: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    pointer-events: auto;
  }

  .hud-bottom-right {
    bottom: 12px;
    right: 12px;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 5px 10px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(255, 255, 255, 0.94);
    box-shadow:
      0 0 0 1px rgba(15, 23, 42, 0.06),
      0 4px 12px -4px rgba(15, 23, 42, 0.09);
    backdrop-filter: blur(12px) saturate(160%);
    -webkit-backdrop-filter: blur(12px) saturate(160%);
    font-family: var(--mono);
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.055em;
    color: var(--ink);
    line-height: 1;
    white-space: nowrap;
  }

  .pill-muted {
    color: var(--slate);
    font-weight: 500;
  }

  .pill-round {
    color: var(--orange-ink);
    background: rgba(255, 247, 237, 0.88);
    border-color: rgba(253, 186, 116, 0.75);
  }

  .live-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--orange);
    box-shadow: 0 0 0 0 rgba(255, 90, 31, 0.55);
    animation: flDotPulse 2.1s cubic-bezier(0.22, 1, 0.36, 1) infinite;
    flex: 0 0 auto;
  }

  .live-dot.is-paused {
    background: #94A3B8;
    animation: none;
    box-shadow: none;
  }

  @keyframes flDotPulse {
    0% { box-shadow: 0 0 0 0 rgba(255, 90, 31, 0.52); }
    70% { box-shadow: 0 0 0 6px rgba(255, 90, 31, 0); }
    100% { box-shadow: 0 0 0 0 rgba(255, 90, 31, 0); }
  }

  .ctrl-btn {
    appearance: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 999px;
    font-family: var(--sans);
    font-size: 11.5px;
    font-weight: 600;
    letter-spacing: 0.01em;
    line-height: 1;
    cursor: pointer;
    transition:
      transform 160ms cubic-bezier(0.22, 1, 0.36, 1),
      box-shadow 180ms cubic-bezier(0.22, 1, 0.36, 1),
      background-color 160ms ease,
      border-color 160ms ease;
    outline: none;
  }

  .ctrl-btn:active {
    transform: scale(0.975);
  }

  .ctrl-btn:focus-visible {
    box-shadow: 0 0 0 3px rgba(255, 90, 31, 0.22);
  }

  .ctrl-primary {
    color: #FFFFFF;
    background: linear-gradient(180deg, #FF5A1F 0%, #EA580C 100%);
    border: 1px solid rgba(194, 65, 12, 0.45);
    box-shadow:
      0 1px 0 rgba(255, 255, 255, 0.26) inset,
      0 6px 16px -6px rgba(234, 88, 12, 0.55);
  }

  .ctrl-primary:hover {
    background: linear-gradient(180deg, #FF6A33 0%, #EA580C 100%);
    box-shadow:
      0 1px 0 rgba(255, 255, 255, 0.3) inset,
      0 8px 20px -6px rgba(234, 88, 12, 0.65);
    transform: translateY(-1px);
  }

  .ctrl-primary:active {
    transform: translateY(0) scale(0.975);
  }

  .ctrl-glass {
    color: var(--ink);
    background: rgba(255, 255, 255, 0.80);
    border: 1px solid rgba(255, 255, 255, 0.95);
    box-shadow:
      0 0 0 1px rgba(15, 23, 42, 0.08),
      0 4px 12px -4px rgba(15, 23, 42, 0.10);
    backdrop-filter: blur(12px) saturate(160%);
    -webkit-backdrop-filter: blur(12px) saturate(160%);
  }

  .ctrl-glass:hover {
    background: rgba(255, 255, 255, 0.94);
    border-color: rgba(253, 186, 116, 0.85);
    color: var(--orange-ink);
  }

  .legend {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 5px 10px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(255, 255, 255, 0.90);
    box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.05);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 500;
    color: var(--slate);
  }

  .lg-item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .lg-dot {
    width: 6.5px;
    height: 6.5px;
    border-radius: 50%;
    display: inline-block;
  }

  .icon-svg {
    width: 12px;
    height: 12px;
    display: inline-block;
    flex: 0 0 auto;
  }

  @media (max-width: 520px) {
    .hud-top-right .pill-meta,
    .hud-bottom-right {
      display: none;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .live-dot { animation: none; }
  }
</style>
</head>
<body>
<div class="fl-stage" id="fl-stage" role="region" aria-label="3D Federated Learning Network Topology">
  <div id="canvas-host"></div>

  <div class="hud hud-top-left">
    <div class="pill">
      <span class="live-dot" id="live-dot"></span>
      <span id="mode-label">WEBGL · FEDERATED TOPOLOGY</span>
    </div>
  </div>

  <div class="hud hud-top-right">
    <div class="pill pill-muted pill-meta">__CLIENTS__ CLIENTS · 0 B RAW DATA</div>
    <div class="pill pill-round" id="round-pill">FEDAVG R-01</div>
  </div>

  <div class="hud hud-bottom-left">
    <button type="button" class="ctrl-btn ctrl-primary" id="btn-pulse" title="Trigger FedAvg synchronization wave">
      <svg class="icon-svg" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="8" cy="8" r="2.2" fill="currentColor" stroke="none"/>
        <path d="M4.2 4.2a5.4 5.4 0 0 0 0 7.6M11.8 4.2a5.4 5.4 0 0 1 0 7.6"/>
      </svg>
      <span>Pulse Round</span>
    </button>
    <button type="button" class="ctrl-btn ctrl-glass" id="btn-toggle" aria-pressed="false" title="Pause or resume animation">
      <span id="toggle-icon">❚❚</span>
      <span id="toggle-label">Pause</span>
    </button>
  </div>

  <div class="hud hud-bottom-right">
    <div class="legend">
      <span class="lg-item"><span class="lg-dot" style="background:#FF5A1F"></span>Active</span>
      <span class="lg-item"><span class="lg-dot" style="background:#0F172A"></span>Synced</span>
      <span class="lg-item"><span class="lg-dot" style="background:#94A3B8"></span>Idle</span>
    </div>
  </div>
</div>

<script>__THREE_JS__</script>
<script>
(function () {
  "use strict";

  var stage = document.getElementById("fl-stage");
  var host = document.getElementById("canvas-host");
  var btnPulse = document.getElementById("btn-pulse");
  var btnToggle = document.getElementById("btn-toggle");
  var toggleIcon = document.getElementById("toggle-icon");
  var toggleLabel = document.getElementById("toggle-label");
  var liveDot = document.getElementById("live-dot");
  var modeLabel = document.getElementById("mode-label");
  var roundPill = document.getElementById("round-pill");

  var prefersReduced = false;
  try {
    prefersReduced = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (_) {}

  var state = {
    paused: prefersReduced,
    round: 1,
    dragging: false,
    lastX: 0,
    lastY: 0,
    pointerX: 0,
    pointerY: 0,
    smoothPX: 0,
    smoothPY: 0,
    orbitYaw: 0.35,
    orbitPitch: 0.22,
    velYaw: 0,
    velPitch: 0,
    waveActive: false,
    waveProgress: 0,
    coreFlare: 0,
    autoWaveTimer: 0
  };

  function updateToggleUI() {
    if (state.paused) {
      toggleIcon.textContent = "▶";
      toggleLabel.textContent = "Play";
      btnToggle.setAttribute("aria-pressed", "true");
      liveDot.classList.add("is-paused");
    } else {
      toggleIcon.textContent = "❚❚";
      toggleLabel.textContent = "Pause";
      btnToggle.setAttribute("aria-pressed", "false");
      liveDot.classList.remove("is-paused");
    }
  }
  updateToggleUI();

  function formatRound(n) {
    return "FEDAVG R-" + (n < 10 ? "0" + n : String(n));
  }

  // Deterministic PRNG for clean, repeatable Fibonacci node states
  function mulberry32(seed) {
    return function () {
      var t = (seed += 0x6D2B79F5);
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function buildTopologyData() {
    var rand = mulberry32(202604);
    var N = 84;
    var goldenAngle = Math.PI * (3 - Math.sqrt(5));
    var nodes = [];

    for (var i = 0; i < N; i++) {
      var yUnit = 1 - (i / (N - 1)) * 2; // 1 to -1
      var rAtY = Math.sqrt(Math.max(0, 1 - yUnit * yUnit));
      var theta = goldenAngle * i;

      // Subtle architectural multi-shell distribution, slightly wider horizontally
      var shellRadius = 3.05 + (i % 3) * 0.34 + (rand() - 0.5) * 0.22;
      var x = Math.cos(theta) * rAtY * shellRadius * 1.18;
      var y = yUnit * shellRadius * 0.86;
      var z = Math.sin(theta) * rAtY * shellRadius * 1.06;

      // Role breakdown: ~28 active (#FF5A1F), ~32 synced (#0F172A), ~24 idle (#94A3B8)
      var rPick = rand();
      var role = "idle";
      if (i % 3 === 0 || rPick < 0.12) {
        role = "active";
      } else if (rPick < 0.64) {
        role = "synced";
      }

      var dist = Math.sqrt(x * x + y * y + z * z);
      nodes.push({
        idx: i,
        x: x,
        y: y,
        z: z,
        dist: dist,
        role: role,
        phase: rand() * Math.PI * 2,
        flash: 0
      });
    }
    return nodes;
  }

  var nodesData = buildTopologyData();
  var activeIndices = [];
  for (var i = 0; i < nodesData.length; i++) {
    if (nodesData[i].role === "active") {
      activeIndices.push(i);
    }
  }

  // Shared pointer & drag interaction
  function bindInteractions(targetEl, onPulseHook) {
    targetEl.addEventListener("pointerdown", function (ev) {
      if (ev.target && ev.target.closest && ev.target.closest("button")) return;
      state.dragging = true;
      state.lastX = ev.clientX;
      state.lastY = ev.clientY;
      stage.classList.add("is-dragging");
      if (targetEl.setPointerCapture) {
        try { targetEl.setPointerCapture(ev.pointerId); } catch (_) {}
      }
    });

    targetEl.addEventListener("pointermove", function (ev) {
      var rect = stage.getBoundingClientRect();
      var nx = ((ev.clientX - rect.left) / Math.max(1, rect.width)) * 2 - 1;
      var ny = ((ev.clientY - rect.top) / Math.max(1, rect.height)) * 2 - 1;
      state.pointerX = Math.max(-1, Math.min(1, nx));
      state.pointerY = Math.max(-1, Math.min(1, ny));

      if (state.dragging) {
        var dx = ev.clientX - state.lastX;
        var dy = ev.clientY - state.lastY;
        state.lastX = ev.clientX;
        state.lastY = ev.clientY;
        state.velYaw = dx * 0.0068;
        state.velPitch = dy * 0.0052;
        state.orbitYaw += state.velYaw;
        state.orbitPitch = Math.max(-1.05, Math.min(1.05, state.orbitPitch + state.velPitch));
      }
    });

    function endDrag(ev) {
      if (!state.dragging) return;
      state.dragging = false;
      stage.classList.remove("is-dragging");
      if (targetEl.releasePointerCapture && ev && ev.pointerId !== undefined) {
        try { targetEl.releasePointerCapture(ev.pointerId); } catch (_) {}
      }
    }

    targetEl.addEventListener("pointerup", endDrag);
    targetEl.addEventListener("pointercancel", endDrag);
    targetEl.addEventListener("pointerleave", function () {
      state.pointerX = 0;
      state.pointerY = 0;
    });

    btnToggle.addEventListener("click", function () {
      state.paused = !state.paused;
      updateToggleUI();
    });

    btnPulse.addEventListener("click", function () {
      if (state.paused) {
        state.paused = false;
        updateToggleUI();
      }
      onPulseHook(true);
    });
  }

  // Create radial glow texture on offscreen 2D canvas (works cleanly on light bg)
  function makeGlowTexture(THREE, innerRgba, midRgba, outerRgba) {
    var c = document.createElement("canvas");
    c.width = 128;
    c.height = 128;
    var ctx = c.getContext("2d");
    var g = ctx.createRadialGradient(64, 64, 2, 64, 64, 62);
    g.addColorStop(0.0, innerRgba);
    g.addColorStop(0.32, midRgba);
    g.addColorStop(0.72, outerRgba);
    g.addColorStop(1.0, "rgba(255, 90, 31, 0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 128, 128);
    var tex = new THREE.CanvasTexture(c);
    tex.needsUpdate = true;
    return tex;
  }

  // =========================================================================
  // PRIMARY RENDERER: THREE.JS WEBGL
  // =========================================================================
  function initWebGL() {
    if (typeof window.THREE === "undefined") return false;
    var THREE = window.THREE;

    var renderer;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        powerPreference: "high-performance"
      });
    } catch (_) {
      return false;
    }

    if (!renderer || !renderer.getContext()) return false;

    var width = Math.max(1, host.clientWidth || stage.clientWidth || 640);
    var height = Math.max(1, host.clientHeight || stage.clientHeight || __HEIGHT__);

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    renderer.setClearColor(0x000000, 0);
    host.appendChild(renderer.domElement);

    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100);
    camera.position.set(0, 0.35, 9.6);

    // Architectural studio lighting tailored for crisp white + Signal Orange
    var ambient = new THREE.AmbientLight(0xffffff, 0.88);
    scene.add(ambient);

    var keyLight = new THREE.DirectionalLight(0xffffff, 0.92);
    keyLight.position.set(6, 8, 9);
    scene.add(keyLight);

    var rimLight = new THREE.DirectionalLight(0xffb088, 0.55);
    rimLight.position.set(-7, -4, -6);
    scene.add(rimLight);

    var coreLight = new THREE.PointLight(0xff5a1f, 1.35, 11, 1.6);
    coreLight.position.set(0, 0, 0);
    scene.add(coreLight);

    var root = new THREE.Group();
    scene.add(root);

    // -----------------------------------------------------------------------
    // 1. Central Global Aggregator
    // -----------------------------------------------------------------------
    var aggGroup = new THREE.Group();
    root.add(aggGroup);

    // Outer faceted #0F172A wireframe icosahedron
    var icoOuterGeo = new THREE.IcosahedronGeometry(1.18, 1);
    var icoEdgesGeo = new THREE.EdgesGeometry(icoOuterGeo, 1);
    var icoWireMat = new THREE.LineBasicMaterial({
      color: 0x0f172a,
      transparent: true,
      opacity: 0.34
    });
    var icoWire = new THREE.LineSegments(icoEdgesGeo, icoWireMat);
    aggGroup.add(icoWire);

    // Secondary delicate inner orange wireframe accent
    var icoAccentGeo = new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(1.06, 0), 1);
    var icoAccentMat = new THREE.LineBasicMaterial({
      color: 0xff5a1f,
      transparent: true,
      opacity: 0.28
    });
    var icoAccent = new THREE.LineSegments(icoAccentGeo, icoAccentMat);
    aggGroup.add(icoAccent);

    // Translucent glass inner icosahedron
    var icoGlassGeo = new THREE.IcosahedronGeometry(0.98, 1);
    var icoGlassMat = new THREE.MeshPhysicalMaterial({
      color: 0xffffff,
      emissive: 0xff5a1f,
      emissiveIntensity: 0.06,
      roughness: 0.16,
      metalness: 0.06,
      clearcoat: 0.95,
      clearcoatRoughness: 0.12,
      transparent: true,
      opacity: 0.44,
      flatShading: true
    });
    var icoGlass = new THREE.Mesh(icoGlassGeo, icoGlassMat);
    aggGroup.add(icoGlass);

    // Luminous #FF5A1F core sphere
    var coreGeo = new THREE.SphereGeometry(0.46, 32, 32);
    var coreMat = new THREE.MeshStandardMaterial({
      color: 0xff5a1f,
      emissive: 0xff5a1f,
      emissiveIntensity: 0.62,
      roughness: 0.22,
      metalness: 0.12
    });
    var coreMesh = new THREE.Mesh(coreGeo, coreMat);
    aggGroup.add(coreMesh);

    // Soft radial aura sprite behind core
    var glowTex = makeGlowTexture(
      THREE,
      "rgba(255, 90, 31, 0.72)",
      "rgba(255, 118, 56, 0.26)",
      "rgba(255, 150, 96, 0.06)"
    );
    var coreGlowMat = new THREE.SpriteMaterial({
      map: glowTex,
      transparent: true,
      opacity: 0.78,
      depthWrite: false
    });
    var coreGlow = new THREE.Sprite(coreGlowMat);
    coreGlow.scale.set(2.35, 2.35, 1);
    aggGroup.add(coreGlow);

    // 2 tilted counter-rotating orbital privacy rings (TorusGeometry)
    var ringOrangeGeo = new THREE.TorusGeometry(1.62, 0.019, 16, 120);
    var ringOrangeMat = new THREE.MeshStandardMaterial({
      color: 0xff5a1f,
      emissive: 0xff5a1f,
      emissiveIntensity: 0.35,
      roughness: 0.28,
      metalness: 0.22,
      transparent: true,
      opacity: 0.86
    });
    var ringOrange = new THREE.Mesh(ringOrangeGeo, ringOrangeMat);
    ringOrange.rotation.set(Math.PI * 0.38, Math.PI * 0.14, 0.15);
    root.add(ringOrange);

    var ringSlateGeo = new THREE.TorusGeometry(2.02, 0.015, 16, 128);
    var ringSlateMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      roughness: 0.36,
      metalness: 0.28,
      transparent: true,
      opacity: 0.62
    });
    var ringSlate = new THREE.Mesh(ringSlateGeo, ringSlateMat);
    ringSlate.rotation.set(-Math.PI * 0.32, -Math.PI * 0.22, 0.42);
    root.add(ringSlate);

    // Broadcast shockwave shell (expands outward on FedAvg wave)
    var waveGeo = new THREE.SphereGeometry(1, 36, 24);
    var waveMat = new THREE.MeshBasicMaterial({
      color: 0xff5a1f,
      transparent: true,
      opacity: 0,
      wireframe: true,
      depthWrite: false
    });
    var waveShell = new THREE.Mesh(waveGeo, waveMat);
    waveShell.visible = false;
    root.add(waveShell);

    var waveRingGeo = new THREE.TorusGeometry(1, 0.018, 12, 96);
    var waveRingMat = new THREE.MeshBasicMaterial({
      color: 0xff5a1f,
      transparent: true,
      opacity: 0,
      depthWrite: false
    });
    var waveRing = new THREE.Mesh(waveRingGeo, waveRingMat);
    waveRing.rotation.x = Math.PI * 0.5;
    waveRing.visible = false;
    root.add(waveRing);

    // -----------------------------------------------------------------------
    // 2. 84 Fibonacci-Distributed 3D Employer Nodes & Delicate Filaments
    // -----------------------------------------------------------------------
    var nodeGeo = new THREE.SphereGeometry(1, 16, 14);
    var nodeMeshes = [];

    var colActive = new THREE.Color(0xff5a1f);
    var colSynced = new THREE.Color(0x0f172a);
    var colIdle = new THREE.Color(0x94a3b8);

    var linePos = [];
    var lineCol = [];
    var cLineOrange = new THREE.Color(0xff5a1f);
    var cLineSlate = new THREE.Color(0x94a3b8);
    var cLineSoft = new THREE.Color(0xcbd5e1);

    for (var n = 0; n < nodesData.length; n++) {
      var nd = nodesData[n];
      var baseColor =
        nd.role === "active" ? colActive :
        nd.role === "synced" ? colSynced : colIdle;
      var baseScale =
        nd.role === "active" ? 0.088 :
        nd.role === "synced" ? 0.068 : 0.056;

      var mat = new THREE.MeshStandardMaterial({
        color: baseColor.clone(),
        emissive: nd.role === "active" ? colActive.clone() : new THREE.Color(0x000000),
        emissiveIntensity: nd.role === "active" ? 0.38 : 0.0,
        roughness: nd.role === "active" ? 0.24 : 0.42,
        metalness: 0.14
      });

      var mesh = new THREE.Mesh(nodeGeo, mat);
      mesh.position.set(nd.x, nd.y, nd.z);
      mesh.scale.setScalar(baseScale);
      mesh.userData = { baseScale: baseScale, baseEmissive: nd.role === "active" ? 0.38 : 0.0 };
      root.add(mesh);
      nodeMeshes.push(mesh);

      // Radial filament from inner aggregator boundary to employer node
      var invD = 1.18 / Math.max(0.001, nd.dist);
      linePos.push(nd.x * invD, nd.y * invD, nd.z * invD);
      linePos.push(nd.x, nd.y, nd.z);

      var lcInner = nd.role === "active" ? cLineOrange : cLineSlate;
      var lcOuter = nd.role === "active" ? cLineOrange : cLineSoft;
      lineCol.push(lcInner.r, lcInner.g, lcInner.b);
      lineCol.push(lcOuter.r, lcOuter.g, lcOuter.b);
    }

    var filamentGeo = new THREE.BufferGeometry();
    filamentGeo.setAttribute("position", new THREE.Float32BufferAttribute(linePos, 3));
    filamentGeo.setAttribute("color", new THREE.Float32BufferAttribute(lineCol, 3));
    var filamentMat = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.24,
      depthWrite: false
    });
    var filaments = new THREE.LineSegments(filamentGeo, filamentMat);
    root.add(filaments);

    // Subtle peer lattice chords (connect nearest neighbor for architectural depth)
    var chordPos = [];
    for (var a = 0; a < nodesData.length; a += 2) {
      var na = nodesData[a];
      var bestJ = -1;
      var bestD = 999;
      for (var b = 0; b < nodesData.length; b++) {
        if (a === b) continue;
        var nb = nodesData[b];
        var ddx = na.x - nb.x, ddy = na.y - nb.y, ddz = na.z - nb.z;
        var dd = ddx * ddx + ddy * ddy + ddz * ddz;
        if (dd < bestD) { bestD = dd; bestJ = b; }
      }
      if (bestJ >= 0 && bestD < 2.2) {
        chordPos.push(na.x, na.y, na.z, nodesData[bestJ].x, nodesData[bestJ].y, nodesData[bestJ].z);
      }
    }
    var chordGeo = new THREE.BufferGeometry();
    chordGeo.setAttribute("position", new THREE.Float32BufferAttribute(chordPos, 3));
    var chordMat = new THREE.LineBasicMaterial({
      color: 0x94a3b8,
      transparent: true,
      opacity: 0.11,
      depthWrite: false
    });
    root.add(new THREE.LineSegments(chordGeo, chordMat));

    // -----------------------------------------------------------------------
    // 3. Animated Gradient-Packet Pulses (Inward & Outward Broadcasts)
    // -----------------------------------------------------------------------
    var packetGeo = new THREE.SphereGeometry(0.052, 12, 10);
    var packets = [];
    var PACKET_COUNT = 34;

    for (var p = 0; p < PACKET_COUNT; p++) {
      var pMat = new THREE.MeshBasicMaterial({
        color: 0xff5a1f,
        transparent: true,
        opacity: 0.95
      });
      var pMesh = new THREE.Mesh(packetGeo, pMat);

      var haloMat = new THREE.SpriteMaterial({
        map: glowTex,
        transparent: true,
        opacity: 0.65,
        depthWrite: false
      });
      var halo = new THREE.Sprite(haloMat);
      halo.scale.set(0.32, 0.32, 1);
      pMesh.add(halo);
      root.add(pMesh);

      var isOutward = p % 4 === 0;
      var nodeIdx = isOutward
        ? (p * 5) % nodesData.length
        : activeIndices[p % activeIndices.length];

      packets.push({
        mesh: pMesh,
        mat: pMat,
        halo: halo,
        nodeIdx: nodeIdx,
        direction: isOutward ? 1 : -1, // -1 inward (gradient upload), +1 outward (global weights)
        t: (p / PACKET_COUNT),
        speed: 0.24 + (p % 7) * 0.036,
        burst: false
      });
    }

    function triggerFedAvgRound(isManual) {
      state.round += 1;
      roundPill.textContent = formatRound(state.round);
      state.waveActive = true;
      state.waveProgress = 0;
      state.coreFlare = 1.0;

      // Launch rapid synchronized inward gradient burst followed by outward broadcast
      for (var k = 0; k < packets.length; k++) {
        var pk = packets[k];
        if (k < 18) {
          pk.direction = -1;
          pk.nodeIdx = activeIndices[k % activeIndices.length];
          pk.t = (k % 6) * 0.06;
          pk.speed = 0.62 + (k % 4) * 0.08;
          pk.burst = true;
        } else {
          pk.direction = 1;
          pk.nodeIdx = (k * 3 + state.round * 7) % nodesData.length;
          pk.t = 0.0;
          pk.speed = 0.48 + (k % 5) * 0.06;
          pk.burst = true;
        }
      }
      if (isManual) {
        state.velYaw += 0.022;
      }
    }

    bindInteractions(stage, triggerFedAvgRound);

    // Resize observer
    function handleResize() {
      var w = Math.max(1, host.clientWidth || stage.clientWidth);
      var h = Math.max(1, host.clientHeight || stage.clientHeight);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
    }
    window.addEventListener("resize", handleResize);
    if (typeof ResizeObserver !== "undefined") {
      try { new ResizeObserver(handleResize).observe(stage); } catch (_) {}
    }

    // Main animation loop
    var lastTime = performance.now();
    var elapsed = 0;

    function renderFrame(now) {
      requestAnimationFrame(renderFrame);
      var dt = Math.min(0.05, Math.max(0.001, (now - lastTime) / 1000));
      lastTime = now;

      // Smooth pointer parallax & drag inertia (always responsive even when paused)
      state.smoothPX += (state.pointerX - state.smoothPX) * Math.min(1, dt * 6.5);
      state.smoothPY += (state.pointerY - state.smoothPY) * Math.min(1, dt * 6.5);

      if (!state.dragging) {
        state.velYaw *= Math.pow(0.08, dt);
        state.velPitch *= Math.pow(0.08, dt);
        state.orbitYaw += state.velYaw;
        state.orbitPitch = Math.max(-1.05, Math.min(1.05, state.orbitPitch + state.velPitch));
      }

      if (!state.paused) {
        elapsed += dt;
        state.orbitYaw += dt * 0.14;

        // Periodic gentle FedAvg wave every ~9 seconds
        state.autoWaveTimer += dt;
        if (state.autoWaveTimer > 9.0) {
          state.autoWaveTimer = 0;
          triggerFedAvgRound(false);
        }

        // Counter-rotating orbital privacy rings & aggregator facets
        icoWire.rotation.y += dt * 0.24;
        icoWire.rotation.x += dt * 0.09;
        icoGlass.rotation.y = icoWire.rotation.y;
        icoGlass.rotation.x = icoWire.rotation.x;
        icoAccent.rotation.y -= dt * 0.32;
        icoAccent.rotation.z += dt * 0.16;

        ringOrange.rotation.z += dt * 0.42;
        ringOrange.rotation.y += dt * 0.12;
        ringSlate.rotation.z -= dt * 0.28;
        ringSlate.rotation.x += dt * 0.08;

        // Core breathing + wave flare
        state.coreFlare = Math.max(0, state.coreFlare - dt * 1.15);
        var breath = 1 + Math.sin(elapsed * 2.4) * 0.055 + state.coreFlare * 0.24;
        coreMesh.scale.setScalar(breath);
        coreMat.emissiveIntensity = 0.62 + state.coreFlare * 0.95;
        icoGlassMat.emissiveIntensity = 0.06 + state.coreFlare * 0.34;
        coreGlow.scale.setScalar(2.35 + state.coreFlare * 1.15 + Math.sin(elapsed * 2.4) * 0.14);
        coreGlowMat.opacity = 0.72 + state.coreFlare * 0.25;
        coreLight.intensity = 1.35 + state.coreFlare * 1.5;

        // Expanding FedAvg broadcast wave
        if (state.waveActive) {
          state.waveProgress += dt * 0.72;
          if (state.waveProgress >= 1.0) {
            state.waveActive = false;
            waveShell.visible = false;
            waveRing.visible = false;
          } else {
            var easeOut = 1 - Math.pow(1 - state.waveProgress, 3);
            var waveRadius = 0.7 + easeOut * 4.35;
            var fade = Math.sin(state.waveProgress * Math.PI);

            waveShell.visible = true;
            waveShell.scale.setScalar(waveRadius);
            waveMat.opacity = fade * 0.17;

            waveRing.visible = true;
            waveRing.scale.setScalar(waveRadius * 1.03);
            waveRingMat.opacity = fade * 0.55;

            // Illuminate nodes as the broadcast wave sweeps past their radius
            for (var j = 0; j < nodesData.length; j++) {
              var nd = nodesData[j];
              if (Math.abs(nd.dist - waveRadius) < 0.42) {
                nd.flash = Math.max(nd.flash, 1.0);
              }
            }
          }
        }

        // Update node micro-pulses & wave flash decay
        for (var m = 0; m < nodesData.length; m++) {
          var nodeD = nodesData[m];
          var meshM = nodeMeshes[m];
          if (nodeD.flash > 0.001) {
            nodeD.flash = Math.max(0, nodeD.flash - dt * 1.65);
          }
          var idleBob = nodeD.role === "active"
            ? 1 + Math.sin(elapsed * 3.1 + nodeD.phase) * 0.11
            : 1.0;
          var flashBoost = 1 + nodeD.flash * 0.55;
          meshM.scale.setScalar(meshM.userData.baseScale * idleBob * flashBoost);

          if (nodeD.flash > 0.01) {
            meshM.material.emissive.setHex(0xff5a1f);
            meshM.material.emissiveIntensity = meshM.userData.baseEmissive + nodeD.flash * 0.95;
          } else {
            meshM.material.emissiveIntensity = meshM.userData.baseEmissive;
          }
        }

        // Animate gradient packets along radial filaments
        for (var q = 0; q < packets.length; q++) {
          var pkt = packets[q];
          pkt.t += dt * pkt.speed;
          if (pkt.t >= 1.0) {
            pkt.t -= 1.0;
            if (pkt.burst) {
              pkt.burst = false;
              pkt.speed = 0.24 + (q % 7) * 0.036;
            }
            if (pkt.direction === -1) {
              // Gradient arrived at Global Aggregator: slight core shimmer
              state.coreFlare = Math.min(1.0, state.coreFlare + 0.08);
              pkt.nodeIdx = activeIndices[(pkt.nodeIdx + 7) % activeIndices.length];
            } else {
              // Global model reached employer node: brief sync glow
              nodesData[pkt.nodeIdx].flash = Math.max(nodesData[pkt.nodeIdx].flash, 0.75);
              pkt.nodeIdx = (pkt.nodeIdx + 11) % nodesData.length;
            }
          }

          var target = nodesData[pkt.nodeIdx];
          var u = pkt.direction === -1 ? (1 - pkt.t) : pkt.t;
          // Keep travel cleanly between core shell (0.14) and node (1.0)
          var frac = 0.14 + u * 0.86;
          pkt.mesh.position.set(target.x * frac, target.y * frac, target.z * frac);

          var edgeFade = Math.sin(pkt.t * Math.PI);
          pkt.mat.opacity = 0.25 + edgeFade * 0.75;
          var sc = (pkt.burst ? 1.28 : 0.92) * (0.65 + edgeFade * 0.48);
          pkt.mesh.scale.setScalar(sc);
          pkt.halo.material.opacity = edgeFade * (pkt.burst ? 0.85 : 0.58);
        }
      }

      // Apply orbit + smooth parallax tilt to root & camera
      root.rotation.y = state.orbitYaw + state.smoothPX * 0.24;
      root.rotation.x = state.orbitPitch + state.smoothPY * 0.16;
      camera.position.x = state.smoothPX * 0.32;
      camera.position.y = 0.35 - state.smoothPY * 0.22;
      camera.lookAt(0, 0, 0);

      renderer.render(scene, camera);
    }

    requestAnimationFrame(renderFrame);
    return true;
  }

  // =========================================================================
  // GRACEFUL 2D CANVAS FALLBACK (IF WEBGL UNAVAILABLE)
  // =========================================================================
  function initCanvas2DFallback() {
    modeLabel.textContent = "2D CANVAS · FEDERATED TOPOLOGY";

    var canvas = document.createElement("canvas");
    host.appendChild(canvas);
    var ctx = canvas.getContext("2d");

    function resize2D() {
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      var w = Math.max(1, host.clientWidth || stage.clientWidth || 640);
      var h = Math.max(1, host.clientHeight || stage.clientHeight || __HEIGHT__);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize2D();
    window.addEventListener("resize", resize2D);

    var packets2D = [];
    for (var p = 0; p < 24; p++) {
      packets2D.push({
        nodeIdx: activeIndices[p % activeIndices.length],
        dir: p % 4 === 0 ? 1 : -1,
        t: p / 24,
        speed: 0.28 + (p % 5) * 0.04
      });
    }

    function triggerPulse2D() {
      state.round += 1;
      roundPill.textContent = formatRound(state.round);
      state.waveActive = true;
      state.waveProgress = 0;
      state.coreFlare = 1.0;
    }

    bindInteractions(stage, triggerPulse2D);

    function project(x, y, z, w, h, yaw, pitch) {
      var cy = Math.cos(yaw), sy = Math.sin(yaw);
      var cx = Math.cos(pitch), sx = Math.sin(pitch);
      var x1 = x * cy - z * sy;
      var z1 = x * sy + z * cy;
      var y2 = y * cx - z1 * sx;
      var z2 = y * sx + z1 * cx;
      var fov = Math.min(w, h) * 0.72;
      var scale = fov / (9.2 - z2);
      return { sx: w * 0.5 + x1 * scale, sy: h * 0.5 - y2 * scale, z: z2, s: scale };
    }

    var lastTime = performance.now();
    function tick2D(now) {
      requestAnimationFrame(tick2D);
      var dt = Math.min(0.05, (now - lastTime) / 1000);
      lastTime = now;

      var w = host.clientWidth || stage.clientWidth || 640;
      var h = host.clientHeight || stage.clientHeight || __HEIGHT__;
      ctx.clearRect(0, 0, w, h);

      state.smoothPX += (state.pointerX - state.smoothPX) * Math.min(1, dt * 6);
      state.smoothPY += (state.pointerY - state.smoothPY) * Math.min(1, dt * 6);
      if (!state.paused) {
        state.orbitYaw += dt * 0.16;
        state.coreFlare = Math.max(0, state.coreFlare - dt * 1.1);
        if (state.waveActive) {
          state.waveProgress += dt * 0.75;
          if (state.waveProgress >= 1) state.waveActive = false;
        }
      }

      var yaw = state.orbitYaw + state.smoothPX * 0.25;
      var pitch = state.orbitPitch + state.smoothPY * 0.16;
      var center = project(0, 0, 0, w, h, yaw, pitch);

      // Draw filaments and nodes depth-sorted
      var projected = [];
      for (var i = 0; i < nodesData.length; i++) {
        var nd = nodesData[i];
        var pr = project(nd.x, nd.y, nd.z, w, h, yaw, pitch);
        projected.push({ nd: nd, pr: pr });
      }
      projected.sort(function (a, b) { return a.pr.z - b.pr.z; });

      for (var k = 0; k < projected.length; k++) {
        var item = projected[k];
        ctx.beginPath();
        ctx.moveTo(center.sx, center.sy);
        ctx.lineTo(item.pr.sx, item.pr.sy);
        ctx.strokeStyle = item.nd.role === "active"
          ? "rgba(255, 90, 31, 0.22)"
          : "rgba(148, 163, 184, 0.20)";
        ctx.lineWidth = 0.8;
        ctx.stroke();

        var r = (item.nd.role === "active" ? 3.8 : item.nd.role === "synced" ? 3.0 : 2.3) *
          (0.65 + (item.pr.z + 4) / 10);
        ctx.beginPath();
        ctx.arc(item.pr.sx, item.pr.sy, Math.max(1.5, r), 0, Math.PI * 2);
        ctx.fillStyle = item.nd.role === "active"
          ? "#FF5A1F" : item.nd.role === "synced" ? "#0F172A" : "#94A3B8";
        ctx.fill();
      }

      // Central aggregator
      var coreR = 19 + state.coreFlare * 6;
      var grd = ctx.createRadialGradient(center.sx, center.sy, 2, center.sx, center.sy, coreR * 2.4);
      grd.addColorStop(0, "rgba(255, 90, 31, 0.55)");
      grd.addColorStop(1, "rgba(255, 90, 31, 0)");
      ctx.fillStyle = grd;
      ctx.beginPath();
      ctx.arc(center.sx, center.sy, coreR * 2.4, 0, Math.PI * 2);
      ctx.fill();

      ctx.beginPath();
      ctx.arc(center.sx, center.sy, coreR, 0, Math.PI * 2);
      ctx.fillStyle = "#FF5A1F";
      ctx.fill();
      ctx.strokeStyle = "rgba(15, 23, 42, 0.42)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(center.sx, center.sy, coreR + 12, 0, Math.PI * 2);
      ctx.stroke();

      if (state.waveActive) {
        ctx.beginPath();
        ctx.arc(center.sx, center.sy, 24 + state.waveProgress * Math.min(w, h) * 0.44, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255, 90, 31, " + (Math.sin(state.waveProgress * Math.PI) * 0.55).toFixed(3) + ")";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      for (var q = 0; q < packets2D.length; q++) {
        var pk = packets2D[q];
        if (!state.paused) {
          pk.t += dt * pk.speed;
          if (pk.t >= 1) pk.t -= 1;
        }
        var tgt = nodesData[pk.nodeIdx];
        var frac = pk.dir === -1 ? (1 - pk.t) : pk.t;
        var pp = project(tgt.x * frac, tgt.y * frac, tgt.z * frac, w, h, yaw, pitch);
        ctx.beginPath();
        ctx.arc(pp.sx, pp.sy, 3.0, 0, Math.PI * 2);
        ctx.fillStyle = "#FF5A1F";
        ctx.fill();
      }
    }
    requestAnimationFrame(tick2D);
  }

  if (!initWebGL()) {
    initCanvas2DFallback();
  }
})();
</script>
</body>
</html>
"""
    return (
        html.replace("__HEIGHT__", str(h))
        .replace("__CLIENTS__", clients_label)
        .replace("__THREE_JS__", three_src)
    )


def render_fl_three_hero(height: int = 360, n_clients: int = 9116) -> None:
    """Render the interactive Three.js 3D Federated Learning Network Hero."""
    components.html(
        fl_three_hero_html(height=height, n_clients=n_clients),
        height=height,
        scrolling=False,
    )
