import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Play, Pause, Radio, ShieldCheck } from 'lucide-react';
import type { FederatedHero3DProps } from './types';

type FlPhase = 0 | 1 | 2 | 3;

const PHASE_INFO: Record<
  FlPhase,
  { step: string; title: string; detail: string; accent: string }
> = {
  0: {
    step: 'BƯỚC 1/4',
    title: 'Phát trọng số W từ Máy chủ',
    detail: 'Máy chủ gửi mô hình GNN toàn cục xuống các nhà tuyển dụng.',
    accent: '#0F172A',
  },
  1: {
    step: 'BƯỚC 2/4',
    title: 'Huấn luyện cục bộ tại từng Client',
    detail: 'Hồ sơ ứng viên & 711.820 cạnh riêng tư nằm khóa kín trong máy client.',
    accent: '#EF4444',
  },
  2: {
    step: 'BƯỚC 3/4',
    title: 'Chỉ gửi vector cập nhật ΔW',
    detail: 'Gói tham số ΔW bay về máy chủ · 0 byte dữ liệu thô rời khỏi máy.',
    accent: '#FF5A1F',
  },
  3: {
    step: 'BƯỚC 4/4',
    title: 'Tổng hợp FedAvg trên đồ thị công khai',
    detail: 'Cập nhật trọng số mới → Recall@20 tiệm cận mốc tập trung.',
    accent: '#10B981',
  },
};

interface ClientDef {
  id: string;
  label: string;
  sub: string;
  pos: [number, number, number];
}

const CLIENTS: ClientDef[] = [
  { id: 'c1', label: 'Client 1 · IT & AI', sub: 'Dữ liệu ứng viên riêng', pos: [-2.45, -1.05, 1.15] },
  { id: 'c2', label: 'Client 2 · Tài chính', sub: 'Dữ liệu ứng viên riêng', pos: [2.45, -1.05, 1.15] },
  { id: 'c3', label: 'Client 3 · Thương mại', sub: 'Dữ liệu ứng viên riêng', pos: [-2.1, -0.85, -1.55] },
  { id: 'c4', label: 'Client 4 · Sản xuất', sub: 'Dữ liệu ứng viên riêng', pos: [2.1, -0.85, -1.55] },
];

const SERVER_POS = new THREE.Vector3(0, 1.25, 0);

interface ProjectedLabel {
  id: string;
  x: number;
  y: number;
  visible: boolean;
}

function createGlowTexture(colorHex: string): THREE.CanvasTexture {
  const size = 64;
  const c = document.createElement('canvas');
  c.width = size;
  c.height = size;
  const ctx = c.getContext('2d')!;
  const grad = ctx.createRadialGradient(size / 2, size / 2, 1, size / 2, size / 2, size / 2);
  if (colorHex === 'red') {
    grad.addColorStop(0, 'rgba(239, 68, 68, 0.92)');
    grad.addColorStop(0.4, 'rgba(239, 68, 68, 0.28)');
    grad.addColorStop(1, 'rgba(239, 68, 68, 0)');
  } else if (colorHex === 'slate') {
    grad.addColorStop(0, 'rgba(15, 23, 42, 0.85)');
    grad.addColorStop(0.4, 'rgba(15, 23, 42, 0.22)');
    grad.addColorStop(1, 'rgba(15, 23, 42, 0)');
  } else {
    grad.addColorStop(0, 'rgba(255, 90, 31, 0.98)');
    grad.addColorStop(0.38, 'rgba(255, 90, 31, 0.34)');
    grad.addColorStop(1, 'rgba(255, 90, 31, 0)');
  }
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

export const FederatedGlassConstellation: React.FC<FederatedHero3DProps> = ({
  className = '',
  nClients = 9116,
  recallScore,
}) => {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const hostRef = useRef<HTMLDivElement | null>(null);

  const [paused, setPaused] = useState(false);
  const [phase, setPhase] = useState<FlPhase>(2);
  const [roundNum, setRoundNum] = useState(1);
  const [dragging, setDragging] = useState(false);
  const [focusId, setFocusId] = useState<'server' | 'client' | null>(null);
  const [isFallback2D, setIsFallback2D] = useState(false);
  const [labels, setLabels] = useState<Record<string, ProjectedLabel>>({});

  const pausedRef = useRef(false);
  const triggerRoundRef = useRef<(() => void) | null>(null);
  const focusRef = useRef<'server' | 'client' | null>(null);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    focusRef.current = focusId;
  }, [focusId]);

  useEffect(() => {
    const stage = stageRef.current;
    const host = hostRef.current;
    if (!stage || !host) return;

    const reducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let disposed = false;
    let rafId = 0;

    // Shared orbital & phase state
    const state = {
      yaw: 0.12,
      pitch: 0.14,
      velYaw: 0,
      velPitch: 0,
      dragging: false,
      lastX: 0,
      lastY: 0,
      pointerX: 0,
      pointerY: 0,
      smoothPX: 0,
      smoothPY: 0,
      phaseTime: 0,
      phaseIdx: 0 as FlPhase,
      phaseDuration: 2.35, // seconds per step
      round: 1,
      serverFlash: 0,
    };

    const onPointerDown = (e: PointerEvent) => {
      if ((e.target as HTMLElement)?.closest('button')) return;
      state.dragging = true;
      state.lastX = e.clientX;
      state.lastY = e.clientY;
      state.velYaw = 0;
      state.velPitch = 0;
      setDragging(true);
      try {
        stage.setPointerCapture(e.pointerId);
      } catch {
        // ignore
      }
    };

    const onPointerMove = (e: PointerEvent) => {
      const rect = stage.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        state.pointerX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        state.pointerY = ((e.clientY - rect.top) / rect.height) * 2 - 1;
      }
      if (!state.dragging) return;
      const dx = e.clientX - state.lastX;
      const dy = e.clientY - state.lastY;
      state.lastX = e.clientX;
      state.lastY = e.clientY;
      state.velYaw = dx * 0.0055;
      state.velPitch = dy * 0.004;
      state.yaw += state.velYaw;
      state.pitch = Math.max(-0.42, Math.min(0.62, state.pitch + state.velPitch));
    };

    const endDrag = (e: PointerEvent) => {
      if (!state.dragging) return;
      state.dragging = false;
      setDragging(false);
      try {
        if (stage.hasPointerCapture(e.pointerId)) stage.releasePointerCapture(e.pointerId);
      } catch {
        // ignore
      }
    };

    const onPointerLeave = () => {
      state.pointerX = 0;
      state.pointerY = 0;
    };

    stage.addEventListener('pointerdown', onPointerDown);
    stage.addEventListener('pointermove', onPointerMove);
    stage.addEventListener('pointerup', endDrag);
    stage.addEventListener('pointercancel', endDrag);
    stage.addEventListener('pointerleave', onPointerLeave);

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        powerPreference: 'high-performance',
      });
    } catch {
      renderer = null;
    }

    if (!renderer) {
      setIsFallback2D(true);
      return () => {
        stage.removeEventListener('pointerdown', onPointerDown);
        stage.removeEventListener('pointermove', onPointerMove);
        stage.removeEventListener('pointerup', endDrag);
        stage.removeEventListener('pointercancel', endDrag);
        stage.removeEventListener('pointerleave', onPointerLeave);
      };
    }

    const gl = renderer;
    gl.setClearColor(0x000000, 0);
    gl.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    gl.outputColorSpace = THREE.SRGBColorSpace;
    gl.toneMapping = THREE.ACESFilmicToneMapping;
    gl.toneMappingExposure = 1.06;

    const initW = Math.max(1, host.clientWidth || stage.clientWidth || 640);
    const initH = Math.max(1, host.clientHeight || stage.clientHeight || 360);
    gl.setSize(initW, initH, false);
    gl.domElement.style.width = '100%';
    gl.domElement.style.height = '100%';
    gl.domElement.style.display = 'block';
    host.appendChild(gl.domElement);

    const disposables: Array<{ dispose: () => void }> = [];
    const track = <T extends { dispose: () => void }>(x: T): T => {
      disposables.push(x);
      return x;
    };

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, initW / initH, 0.1, 100);
    camera.position.set(0, 0.72, 9.6);
    camera.lookAt(0, -0.05, 0);

    // Studio warm-light illumination
    scene.add(new THREE.AmbientLight(0xffffff, 1.35));
    const keyLight = new THREE.DirectionalLight(0xfff7ed, 1.65);
    keyLight.position.set(4.5, 6.5, 5.5);
    scene.add(keyLight);
    const rimLight = new THREE.DirectionalLight(0xff5a1f, 0.95);
    rimLight.position.set(-5, 2, -4);
    scene.add(rimLight);

    const root = new THREE.Group();
    scene.add(root);

    const orangeGlowTex = track(createGlowTexture('orange'));
    const redGlowTex = track(createGlowTexture('red'));
    const slateGlowTex = track(createGlowTexture('slate'));

    // =========================================================================
    // 1. CENTRAL GLOBAL AGGREGATOR (Public Graph + FedAvg Server)
    // =========================================================================
    const serverGroup = new THREE.Group();
    serverGroup.position.copy(SERVER_POS);
    root.add(serverGroup);

    const serverGlassGeo = track(new THREE.SphereGeometry(0.74, 36, 36));
    const serverGlassMat = track(
      new THREE.MeshPhysicalMaterial({
        color: 0xffedd5,
        opacity: 0.24,
        transparent: true,
        depthWrite: false,
        roughness: 0.12,
        metalness: 0.05,
        clearcoat: 1,
        clearcoatRoughness: 0.08,
      }),
    );
    const serverGlassMesh = new THREE.Mesh(serverGlassGeo, serverGlassMat);
    serverGlassMesh.renderOrder = 3;
    serverGroup.add(serverGlassMesh);

    // Inner FedAvg icosahedron core (opaque depthWrite=true, zero z-fighting)
    const coreGeo = track(new THREE.IcosahedronGeometry(0.42, 1));
    const coreMat = track(
      new THREE.MeshStandardMaterial({
        color: 0xff5a1f,
        emissive: 0xff5a1f,
        emissiveIntensity: 0.48,
        roughness: 0.28,
        metalness: 0.12,
      }),
    );
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    coreMesh.renderOrder = 1;
    serverGroup.add(coreMesh);

    const coreWireGeo = track(new THREE.EdgesGeometry(track(new THREE.IcosahedronGeometry(0.56, 1))));
    const coreWireMat = track(
      new THREE.LineBasicMaterial({ color: 0x0f172a, transparent: true, opacity: 0.3, depthWrite: false }),
    );
    const coreWire = new THREE.LineSegments(coreWireGeo, coreWireMat);
    coreWire.renderOrder = 2;
    serverGroup.add(coreWire);

    // Public-graph ring around Server
    const serverRingGeo = track(new THREE.TorusGeometry(0.98, 0.015, 12, 96));
    const serverRingMat = track(
      new THREE.MeshBasicMaterial({ color: 0xff5a1f, transparent: true, opacity: 0.58, depthWrite: false }),
    );
    const serverRing = new THREE.Mesh(serverRingGeo, serverRingMat);
    serverRing.rotation.x = Math.PI * 0.42;
    serverRing.renderOrder = 2;
    serverGroup.add(serverRing);

    // Server aggregation wave ring (expands on Phase 3 / FedAvg merge)
    const waveGeo = track(new THREE.RingGeometry(0.72, 0.84, 64));
    const waveMat = track(
      new THREE.MeshBasicMaterial({
        color: 0x10b981,
        transparent: true,
        opacity: 0,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    const waveMesh = new THREE.Mesh(waveGeo, waveMat);
    waveMesh.rotation.x = Math.PI * 0.5;
    waveMesh.renderOrder = 2;
    serverGroup.add(waveMesh);

    const serverAura = new THREE.Sprite(
      track(
        new THREE.SpriteMaterial({
          map: orangeGlowTex,
          transparent: true,
          opacity: 0.28,
          depthWrite: false,
          depthTest: false,
        }),
      ),
    );
    serverAura.scale.set(2.3, 2.3, 1);
    serverAura.renderOrder = 0;
    serverGroup.add(serverAura);

    // =========================================================================
    // 2. FOUR CLIENT PRIVACY SILOS (Private User-Job Data Locked Inside)
    // =========================================================================
    interface ClientVisual {
      def: ClientDef;
      group: THREE.Group;
      shieldMat: THREE.MeshPhysicalMaterial;
      shieldRingMat: THREE.MeshBasicMaterial;
      innerCluster: THREE.Group;
      curve: THREE.CatmullRomCurve3;
      arcMat: THREE.LineBasicMaterial;
    }

    const clientVisuals: ClientVisual[] = [];
    const shieldGeo = track(new THREE.SphereGeometry(0.56, 28, 28));
    const shieldRingGeo = track(new THREE.TorusGeometry(0.64, 0.012, 10, 64));
    const miniNodeGeo = track(new THREE.SphereGeometry(0.055, 10, 10));
    const privateNodeMat = track(
      new THREE.MeshStandardMaterial({
        color: 0xef4444,
        emissive: 0xef4444,
        emissiveIntensity: 0.35,
        roughness: 0.3,
      }),
    );
    const skillNodeMat = track(
      new THREE.MeshStandardMaterial({
        color: 0x0ea5e9,
        roughness: 0.35,
      }),
    );

    // Base privacy floor ring tying the 4 client nodes visually
    const baseRingGeo = track(new THREE.TorusGeometry(2.68, 0.008, 8, 120));
    const baseRingMat = track(
      new THREE.MeshBasicMaterial({ color: 0xcbd5e1, transparent: true, opacity: 0.55 }),
    );
    const baseRing = new THREE.Mesh(baseRingGeo, baseRingMat);
    baseRing.position.set(0, -1.0, -0.15);
    baseRing.rotation.x = Math.PI * 0.5;
    root.add(baseRing);

    for (let i = 0; i < CLIENTS.length; i++) {
      const def = CLIENTS[i];
      const g = new THREE.Group();
      g.position.set(def.pos[0], def.pos[1], def.pos[2]);
      root.add(g);

      // Privacy glass dome (zero-flicker transparent clearcoat shell)
      const shieldMat = track(
        new THREE.MeshPhysicalMaterial({
          color: 0xfee2e2,
          transparent: true,
          opacity: 0.22,
          depthWrite: false,
          roughness: 0.14,
          metalness: 0.04,
          clearcoat: 0.9,
        }),
      );
      const shieldMesh = new THREE.Mesh(shieldGeo, shieldMat);
      shieldMesh.renderOrder = 3;
      g.add(shieldMesh);

      // Red privacy boundary halo ring (data stays inside!)
      const shieldRingMat = track(
        new THREE.MeshBasicMaterial({
          color: 0xef4444,
          transparent: true,
          opacity: 0.52,
        }),
      );
      const sRing = new THREE.Mesh(shieldRingGeo, shieldRingMat);
      sRing.rotation.x = Math.PI * 0.5;
      g.add(sRing);

      // Private local mini-graph locked INSIDE each client pod (never leaves!)
      const innerCluster = new THREE.Group();
      g.add(innerCluster);
      const localPts: THREE.Vector3[] = [];
      for (let m = 0; m < 7; m++) {
        const ang = (m / 7) * Math.PI * 2 + i * 0.6;
        const rad = 0.16 + (m % 2) * 0.12;
        const py = ((m % 3) - 1) * 0.13;
        const pt = new THREE.Vector3(Math.cos(ang) * rad, py, Math.sin(ang) * rad);
        localPts.push(pt);
        const dot = new THREE.Mesh(miniNodeGeo, m < 4 ? privateNodeMat : skillNodeMat);
        dot.position.copy(pt);
        innerCluster.add(dot);
      }
      // Private edges inside pod
      const localEdgePos: number[] = [];
      for (let m = 0; m < localPts.length; m++) {
        const next = localPts[(m + 1) % localPts.length];
        localEdgePos.push(localPts[m].x, localPts[m].y, localPts[m].z, next.x, next.y, next.z);
      }
      const localEdgeGeo = track(new THREE.BufferGeometry());
      localEdgeGeo.setAttribute('position', new THREE.Float32BufferAttribute(localEdgePos, 3));
      const localEdgeMat = track(
        new THREE.LineBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.65 }),
      );
      innerCluster.add(new THREE.LineSegments(localEdgeGeo, localEdgeMat));

      // Curved 3D fiber-optic communication arc between Client ↔ Server
      const startV = new THREE.Vector3(def.pos[0], def.pos[1] + 0.52, def.pos[2]);
      const endV = new THREE.Vector3(SERVER_POS.x, SERVER_POS.y - 0.66, SERVER_POS.z);
      const midV = startV
        .clone()
        .lerp(endV, 0.5)
        .add(new THREE.Vector3(def.pos[0] * 0.22, 0.55, def.pos[2] * 0.22));
      const curve = new THREE.CatmullRomCurve3([startV, midV, endV]);
      const arcPts = curve.getPoints(44);
      const arcGeo = track(new THREE.BufferGeometry().setFromPoints(arcPts));
      const arcMat = track(
        new THREE.LineBasicMaterial({
          color: 0xff5a1f,
          transparent: true,
          opacity: 0.34,
        }),
      );
      root.add(new THREE.Line(arcGeo, arcMat));

      clientVisuals.push({
        def,
        group: g,
        shieldMat,
        shieldRingMat,
        innerCluster,
        curve,
        arcMat,
      });
    }

    // =========================================================================
    // 3. ANIMATED GRADIENT / WEIGHT PACKETS (ONLY ΔW & W TRAVEL — NEVER RAW DATA)
    // =========================================================================
    interface Packet {
      clientIdx: number;
      mesh: THREE.Mesh;
      mat: THREE.MeshBasicMaterial;
      halo: THREE.Sprite;
      haloMat: THREE.SpriteMaterial;
      offset: number;
    }

    const packetGeo = track(new THREE.SphereGeometry(0.062, 10, 10));
    const packets: Packet[] = [];
    for (let ci = 0; ci < clientVisuals.length; ci++) {
      for (let k = 0; k < 3; k++) {
        const pMat = track(
          new THREE.MeshBasicMaterial({ color: 0xff5a1f, transparent: true, opacity: 0 }),
        );
        const mesh = new THREE.Mesh(packetGeo, pMat);
        const hMat = track(
          new THREE.SpriteMaterial({
            map: orangeGlowTex,
            transparent: true,
            opacity: 0,
            depthWrite: false,
          }),
        );
        const halo = new THREE.Sprite(hMat);
        halo.scale.set(0.36, 0.36, 1);
        mesh.add(halo);
        root.add(mesh);
        packets.push({
          clientIdx: ci,
          mesh,
          mat: pMat,
          halo,
          haloMat: hMat,
          offset: k * 0.28,
        });
      }
    }

    // Trigger manual FL round from Step 0
    triggerRoundRef.current = () => {
      state.phaseIdx = 0;
      state.phaseTime = 0;
      state.round += 1;
      setRoundNum(state.round);
      setPhase(0);
      state.velYaw += 0.018;
    };

    const handleResize = () => {
      const w = Math.max(1, host.clientWidth || stage.clientWidth);
      const h = Math.max(1, host.clientHeight || stage.clientHeight);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      gl.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      gl.setSize(w, h, false);
    };
    const ro = new ResizeObserver(handleResize);
    ro.observe(stage);

    const tmpVec = new THREE.Vector3();
    const projectPoint = (worldPos: THREE.Vector3, w: number, h: number): ProjectedLabel => {
      tmpVec.copy(worldPos);
      root.localToWorld(tmpVec);
      tmpVec.project(camera);
      return {
        id: '',
        x: (tmpVec.x * 0.5 + 0.5) * w,
        y: (-tmpVec.y * 0.5 + 0.5) * h,
        visible: tmpVec.z < 1 && tmpVec.z > -1,
      };
    };

    let lastNow = performance.now();
    let labelTick = 0;

    const animate = (now: number) => {
      if (disposed) return;
      if (document.hidden) {
        rafId = 0;
        return;
      }
      rafId = requestAnimationFrame(animate);
      const dt = Math.min(0.05, Math.max(0.001, (now - lastNow) / 1000));
      lastNow = now;

      // Smooth pointer parallax & inertia
      state.smoothPX += (state.pointerX - state.smoothPX) * Math.min(1, dt * 6);
      state.smoothPY += (state.pointerY - state.smoothPY) * Math.min(1, dt * 6);

      if (!state.dragging) {
        state.velYaw *= Math.pow(0.08, dt);
        state.velPitch *= Math.pow(0.08, dt);
        state.yaw += state.velYaw;
        state.pitch = Math.max(-0.42, Math.min(0.62, state.pitch + state.velPitch));
        if (!pausedRef.current && !reducedMotion) {
          state.yaw += dt * 0.14;
        }
      }

      root.rotation.y = state.yaw + state.smoothPX * 0.18;
      root.rotation.x = state.pitch + state.smoothPY * 0.08;

      // Advance 4-step FL story cycle automatically
      if (!pausedRef.current && !reducedMotion) {
        state.phaseTime += dt;
        if (state.phaseTime >= state.phaseDuration) {
          state.phaseTime = 0;
          const next = ((state.phaseIdx + 1) % 4) as FlPhase;
          state.phaseIdx = next;
          if (next === 0) {
            state.round += 1;
            setRoundNum(state.round);
          }
          setPhase(next);
        }
      }

      const progress = Math.min(1, state.phaseTime / state.phaseDuration);
      const pIdx = state.phaseIdx;

      // Core & ring idle spin
      coreMesh.rotation.y += dt * (pIdx === 3 ? 1.5 : 0.45);
      coreWire.rotation.y -= dt * 0.3;
      serverRing.rotation.z += dt * 0.4;

      // Phase-driven visual storytelling
      // Phase 0: Server broadcasts W down to Clients (slate/dark packets moving 1 -> 0)
      // Phase 1: Clients train locally inside red privacy shield (inner clusters spin & glow)
      // Phase 2: Clients upload ONLY ΔW to Server (bright signal-orange packets moving 0 -> 1)
      // Phase 3: Server aggregates FedAvg (emerald/orange pulse wave expands from Server)
      const isBroadcast = pIdx === 0;
      const isLocalTrain = pIdx === 1;
      const isUpload = pIdx === 2;
      const isAggregate = pIdx === 3;

      coreMat.emissiveIntensity = isAggregate
        ? 0.95 + Math.sin(progress * Math.PI) * 0.55
        : isBroadcast
          ? 0.72
          : 0.45;
      const coreScale = isAggregate ? 1 + Math.sin(progress * Math.PI) * 0.14 : 1;
      coreMesh.scale.setScalar(coreScale);

      // Server aggregation ring wave on Phase 3
      if (isAggregate) {
        const s = 1 + progress * 2.4;
        waveMesh.scale.setScalar(s);
        waveMat.opacity = (1 - progress) * 0.65;
      } else {
        waveMat.opacity = 0;
      }

      // Client pods
      for (let i = 0; i < clientVisuals.length; i++) {
        const cv = clientVisuals[i];
        cv.innerCluster.rotation.y += dt * (isLocalTrain ? 2.6 : 0.45);
        cv.innerCluster.rotation.x += dt * (isLocalTrain ? 1.1 : 0.2);

        const highlightClient = focusRef.current === 'client' || isLocalTrain;
        cv.shieldRingMat.opacity = highlightClient
          ? 0.72 + Math.sin(now * 0.008 + i) * 0.22
          : 0.36;

        cv.arcMat.color.setHex(isBroadcast ? 0x0f172a : 0xff5a1f);
        cv.arcMat.opacity = isUpload ? 0.68 : isBroadcast ? 0.48 : 0.22;
      }

      // Update packets along 3D curves
      for (let p = 0; p < packets.length; p++) {
        const pk = packets[p];
        const cv = clientVisuals[pk.clientIdx];

        if (isBroadcast || isUpload) {
          const rawT = (progress * 1.35 + pk.offset) % 1;
          const curveT = isUpload ? rawT : 1 - rawT;
          cv.curve.getPointAt(curveT, pk.mesh.position);
          const fade = Math.sin(rawT * Math.PI);
          pk.mat.color.setHex(isUpload ? 0xff5a1f : 0x0f172a);
          pk.mat.opacity = 0.92 * fade;
          pk.haloMat.map = isUpload ? orangeGlowTex : slateGlowTex;
          pk.haloMat.opacity = 0.75 * fade;
          pk.mesh.scale.setScalar(0.85 + fade * 0.4);
        } else {
          pk.mat.opacity = 0;
          pk.haloMat.opacity = 0;
        }
      }

      // Keep redGlowTex used subtly on server aura when focusing client privacy
      serverAura.material.map = focusRef.current === 'client' ? redGlowTex : orangeGlowTex;
      serverAura.material.opacity = isAggregate ? 0.65 : 0.38;

      gl.render(scene, camera);

      // Update projected 3D label for the central Server (anchored cleanly to the right of the sphere)
      labelTick += dt;
      if (labelTick >= 0.06) {
        labelTick = 0;
        const w = host.clientWidth || stage.clientWidth;
        const h = host.clientHeight || stage.clientHeight;
        const sv = projectPoint(new THREE.Vector3(0, SERVER_POS.y, 0), w, h);
        setLabels({ server: { ...sv, id: 'server' } });
      }
    };

    const onVisibility = () => {
      if (!document.hidden && !disposed && rafId === 0) {
        lastNow = performance.now();
        rafId = requestAnimationFrame(animate);
      }
    };
    document.addEventListener('visibilitychange', onVisibility);
    rafId = requestAnimationFrame(animate);

    return () => {
      disposed = true;
      triggerRoundRef.current = null;
      if (rafId) cancelAnimationFrame(rafId);
      ro.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
      stage.removeEventListener('pointerdown', onPointerDown);
      stage.removeEventListener('pointermove', onPointerMove);
      stage.removeEventListener('pointerup', endDrag);
      stage.removeEventListener('pointercancel', endDrag);
      stage.removeEventListener('pointerleave', onPointerLeave);
      disposables.forEach((d) => {
        try {
          d.dispose();
        } catch {
          // ignore
        }
      });
      gl.dispose();
      if (gl.domElement.parentNode === host) host.removeChild(gl.domElement);
    };
  }, []);

  const info = PHASE_INFO[phase];

  return (
    <div
      role="region"
      aria-label="Mô hình 3D kiến trúc Federated Graph Learning"
      className={`relative flex flex-col min-h-[380px] w-full overflow-hidden rounded-2xl border border-white/90 select-none backdrop-blur-xl shadow-[0_12px_32px_-12px_rgba(15,23,42,0.14),inset_0_1px_0_rgba(255,255,255,0.95)] ${className}`}
      style={{
        background:
          'radial-gradient(ellipse 68% 60% at 50% 44%, rgba(255,90,31,0.11) 0%, rgba(255,138,91,0.04) 44%, rgba(255,255,255,0) 74%), radial-gradient(rgba(15,23,42,0.075) 1px, transparent 1px), rgba(255,255,255,0.74)',
        backgroundSize: '100% 100%, 20px 20px, 100% 100%',
      }}
    >
      {/* 1. Dedicated Top Control Bar (zero overlap with 3D scene) */}
      <div className="relative z-[4] flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/70 bg-white/75 px-3.5 py-2.5 backdrop-blur-md">
        <div className="flex items-center gap-2 min-w-0">
          <span className="inline-flex items-center gap-1.5 font-mono text-[10.5px] font-bold tracking-wide text-slate-900 whitespace-nowrap">
            <ShieldCheck className="h-3.5 w-3.5 text-[#FF5A1F] shrink-0" />
            KIẾN TRÚC FEDERATED GNN · 3D
          </span>
          <span className="hidden sm:inline-flex items-center rounded-full border border-orange-200/80 bg-[#FFF7ED] px-2 py-0.5 font-mono text-[10px] font-bold text-[#C2410C] whitespace-nowrap">
            VÒNG {roundNum}
          </span>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={() => triggerRoundRef.current?.()}
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-[#C2410C]/40 bg-gradient-to-b from-[#FF5A1F] to-[#EA580C] px-2.5 py-1 text-[11px] font-semibold text-white shadow-[0_4px_12px_-4px_rgba(234,88,12,0.55)] transition-all duration-150 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]"
          >
            <Radio className="h-3 w-3 stroke-[2]" />
            <span>Chạy 1 vòng FL</span>
          </button>

          <button
            type="button"
            onClick={() => setPaused((p) => !p)}
            aria-pressed={paused}
            className="inline-flex cursor-pointer items-center gap-1 rounded-full border border-slate-200 bg-white/90 px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:border-orange-300 hover:text-[#C2410C]"
          >
            {paused ? <Play className="h-3 w-3" /> : <Pause className="h-3 w-3" />}
            <span>{paused ? 'Chạy' : 'Dừng'}</span>
          </button>
        </div>
      </div>

      {/* 2. Unobstructed 3D WebGL Stage */}
      <div
        ref={stageRef}
        className={`relative flex-1 min-h-[245px] w-full overflow-hidden ${
          dragging ? 'cursor-grabbing' : 'cursor-grab'
        }`}
      >
        <div ref={hostRef} className="absolute inset-0 z-[1] h-full w-full" />

        {/* Static, guaranteed non-overlapping architectural callout badges */}
        {!isFallback2D && (
          <>
            <div
              onMouseEnter={() => setFocusId('server')}
              onMouseLeave={() => setFocusId(null)}
              className="absolute top-3 left-3 z-[3] rounded-lg border border-orange-200/90 bg-white/88 px-2.5 py-1.5 shadow-xs backdrop-blur-md"
            >
              <div className="flex items-center gap-1.5 font-mono text-[10px] font-bold text-[#C2410C]">
                <span className="h-2 w-2 rounded-full bg-[#FF5A1F]" />
                MÁY CHỦ FEDAVG
              </div>
              <div className="text-[10.5px] text-slate-600 mt-0.5">
                52.544 cạnh công khai · chỉ nhận ΔW
              </div>
            </div>

            <div
              onMouseEnter={() => setFocusId('client')}
              onMouseLeave={() => setFocusId(null)}
              className="absolute bottom-3 right-3 z-[3] rounded-lg border border-rose-200/90 bg-white/88 px-2.5 py-1.5 shadow-xs backdrop-blur-md"
            >
              <div className="flex items-center gap-1.5 font-mono text-[10px] font-bold text-rose-700">
                <span className="h-2 w-2 rounded-full bg-[#EF4444]" />
                {nClients.toLocaleString('vi-VN')} CLIENT (NHÀ TUYỂN DỤNG)
              </div>
              <div className="text-[10.5px] text-slate-600 mt-0.5">
                Khóa kín 711.820 cạnh riêng tư · 0 B gửi đi
              </div>
            </div>
          </>
        )}

        {/* Keep subtle server pointer-anchor clean */}
        {labels.server?.visible && <span className="sr-only">{Math.round(labels.server.x)}</span>}
      </div>

      {/* 3. Dedicated Bottom 4-Step Live Narrative Strip (zero overlap) */}
      <div className="relative z-[4] flex flex-wrap items-center justify-between gap-2 border-t border-slate-200/70 bg-white/80 px-3.5 py-2.5 backdrop-blur-md">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span
              className="inline-flex shrink-0 items-center rounded px-1.5 py-0.5 font-mono text-[9.5px] font-bold text-white"
              style={{ backgroundColor: info.accent }}
            >
              {info.step}
            </span>
            <span className="text-xs font-bold text-slate-900 truncate">{info.title}</span>
          </div>
          <div className="mt-0.5 text-[11px] text-slate-600 truncate">{info.detail}</div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {([0, 1, 2, 3] as FlPhase[]).map((s) => (
            <span
              key={s}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                s === phase ? 'w-6 bg-[#FF5A1F]' : s < phase ? 'w-2.5 bg-slate-800' : 'w-2.5 bg-slate-200'
              }`}
            />
          ))}
        </div>
      </div>

      {typeof recallScore === 'number' && <span className="sr-only">{recallScore.toFixed(3)}</span>}
    </div>
  );
};

export default FederatedGlassConstellation;
