import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { Pause, Play, Radio, Turtle, WifiOff, Wifi, Filter } from 'lucide-react';

export interface LiveFlNodeSample {
  clientId: number;
  name: string;
  nApps: number;
  weightSharePct: number; // p_k = n_k / N (%)
  drift: number; // ||ΔW_k - ΔW_global|| (0..1)
  latencyMs: number | null;
  bytesUp: number;
  lastRound: number;
  isStraggler?: boolean;
  isDropped?: boolean;
}

export interface LiveFlTopology3DProps {
  nodes: LiveFlNodeSample[];
  running: boolean;
  activeStep: number;
  currentRound: number;
  totalRounds: number;
  algorithm: 'fedavg' | 'fedprox';
  selectedClientId: number | null;
  onSelectClient: (clientId: number) => void;
  onToggleStraggler?: (clientId: number) => void;
  onToggleDropout?: (clientId: number) => void;
  className?: string;
}

const STEP_SPECS = [
  {
    id: 0,
    short: '1. Broadcast W',
    desc: 'Máy chủ phát trọng số mô hình toàn cục W xuống các client trực tuyến.',
    color: '#0F172A',
  },
  {
    id: 1,
    short: '2. Local GNN',
    desc: 'Mỗi nhà tuyển dụng tự học LightGCN trên hồ sơ ứng viên riêng (0 B rời máy).',
    color: '#EF4444',
  },
  {
    id: 2,
    short: '3. Upload ΔW',
    desc: 'Chỉ tải vector cập nhật ΔW (đã áp dụng cấu hình nén) lên Máy chủ.',
    color: '#FF5A1F',
  },
  {
    id: 3,
    short: '4. Aggregate',
    desc: 'Tổng hợp có trọng số p_k = n_k/N (FedProx thêm số hạng μ giữ giảm drift).',
    color: '#10B981',
  },
  {
    id: 4,
    short: '5. Eval & p95',
    desc: 'Đo Recall@20, p50/p95 và độ lệch Client Drift trên toàn mạng.',
    color: '#0EA5E9',
  },
];

const SERVER_POS = new THREE.Vector3(0, 1.55, 0);

function colorForLatency(nd: LiveFlNodeSample | undefined, dimmed: boolean): number {
  if (!nd || nd.isDropped) return dimmed ? 0xe2e8f0 : 0x94a3b8;
  if (dimmed) return 0xe2e8f0;
  if (nd.latencyMs === null) return 0xcbd5e1;
  if (nd.latencyMs < 35) return 0x10b981;
  if (nd.latencyMs < 65) return 0xf59e0b;
  return 0xef4444;
}

function colorForDrift(nd: LiveFlNodeSample | undefined, dimmed: boolean): number {
  if (!nd || nd.isDropped) return dimmed ? 0xe2e8f0 : 0x94a3b8;
  if (dimmed) return 0xe2e8f0;
  if (nd.drift < 0.28) return 0x10b981;
  if (nd.drift < 0.55) return 0xf59e0b;
  return 0xef4444;
}

function pillarHeight(
  nd: LiveFlNodeSample | undefined,
  lens: 'latency' | 'noniid',
  maxLogApps: number,
): number {
  if (!nd || nd.isDropped) return 0.08;
  if (lens === 'noniid') {
    const logVal = Math.log1p(Math.max(1, nd.nApps));
    const norm = Math.min(1, logVal / Math.max(1, maxLogApps));
    return 0.12 + norm * 0.96;
  }
  if (nd.latencyMs === null) return 0.09;
  return 0.12 + Math.min(1, nd.latencyMs / 150) * 0.94;
}

function createGlowTexture(hex: 'orange' | 'slate'): THREE.CanvasTexture {
  const size = 64;
  const c = document.createElement('canvas');
  c.width = size;
  c.height = size;
  const ctx = c.getContext('2d')!;
  const grad = ctx.createRadialGradient(size / 2, size / 2, 1, size / 2, size / 2, size / 2);
  if (hex === 'slate') {
    grad.addColorStop(0, 'rgba(15, 23, 42, 0.88)');
    grad.addColorStop(0.4, 'rgba(15, 23, 42, 0.22)');
    grad.addColorStop(1, 'rgba(15, 23, 42, 0)');
  } else {
    grad.addColorStop(0, 'rgba(255, 90, 31, 0.96)');
    grad.addColorStop(0.38, 'rgba(255, 90, 31, 0.34)');
    grad.addColorStop(1, 'rgba(255, 90, 31, 0)');
  }
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

function computeClientPositions(count: number): THREE.Vector3[] {
  const pts: THREE.Vector3[] = [];
  if (count <= 0) return pts;

  const ringCount = count <= 50 ? 2 : count <= 120 ? 3 : 4;
  const radii =
    ringCount === 2
      ? [1.75, 2.8]
      : ringCount === 3
        ? [1.5, 2.3, 3.1]
        : [1.35, 2.0, 2.65, 3.3];
  const baseY = -1.25;

  const totalRadius = radii.reduce((a, b) => a + b, 0);
  const perRing: number[] = [];
  let assigned = 0;
  for (let r = 0; r < ringCount; r++) {
    const share =
      r === ringCount - 1 ? count - assigned : Math.round((radii[r] / totalRadius) * count);
    perRing.push(Math.max(1, share));
    assigned += share;
  }
  const sum = perRing.reduce((a, b) => a + b, 0);
  perRing[ringCount - 1] += count - sum;

  for (let r = 0; r < ringCount; r++) {
    const nInRing = perRing[r];
    const rad = radii[r];
    const phaseShift = r * 0.45;
    for (let j = 0; j < nInRing; j++) {
      const ang = (j / nInRing) * Math.PI * 2 + phaseShift;
      pts.push(new THREE.Vector3(Math.cos(ang) * rad, baseY, Math.sin(ang) * rad));
    }
  }
  return pts;
}

export const LiveFlTopology3D: React.FC<LiveFlTopology3DProps> = ({
  nodes,
  running,
  activeStep,
  currentRound,
  totalRounds,
  algorithm,
  selectedClientId,
  onSelectClient,
  onToggleStraggler,
  onToggleDropout,
  className = '',
}) => {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const hostRef = useRef<HTMLDivElement | null>(null);

  const [paused, setPaused] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<LiveFlNodeSample | null>(null);
  const [webglError, setWebglError] = useState(false);
  const [previewStep, setPreviewStep] = useState<number>(2);
  const [lens, setLens] = useState<'latency' | 'noniid'>('noniid');
  const [filterMode, setFilterMode] = useState<'all' | 'highlight' | 'dropped'>('all');

  const selectedNode = useMemo(
    () => nodes.find((n) => n.clientId === selectedClientId) ?? nodes[0] ?? null,
    [nodes, selectedClientId],
  );

  const maxLogApps = useMemo(() => {
    let m = 1;
    for (const n of nodes) {
      const v = Math.log1p(Math.max(1, n.nApps));
      if (v > m) m = v;
    }
    return m;
  }, [nodes]);

  const effectiveStep = running && activeStep >= 0 ? activeStep : previewStep;

  const nodesRef = useRef<LiveFlNodeSample[]>(nodes);
  const runningRef = useRef(running);
  const stepRef = useRef(effectiveStep);
  const lensRef = useRef(lens);
  const maxLogRef = useRef(maxLogApps);
  const selectedIdRef = useRef<number | null>(selectedNode?.clientId ?? null);
  const pausedRef = useRef(paused);
  const filterRef = useRef(filterMode);
  const onSelectRef = useRef(onSelectClient);

  nodesRef.current = nodes;
  runningRef.current = running;
  stepRef.current = effectiveStep;
  lensRef.current = lens;
  maxLogRef.current = maxLogApps;
  selectedIdRef.current = selectedNode?.clientId ?? null;
  pausedRef.current = paused;
  filterRef.current = filterMode;
  onSelectRef.current = onSelectClient;

  const nodeCount = nodes.length;

  useEffect(() => {
    const stage = stageRef.current;
    const host = hostRef.current;
    if (!stage || !host || nodeCount === 0) return;

    const reducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let disposed = false;
    let rafId = 0;

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
      setWebglError(true);
      return;
    }

    const gl = renderer;
    gl.setClearColor(0x000000, 0);
    gl.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    gl.outputColorSpace = THREE.SRGBColorSpace;
    gl.toneMapping = THREE.ACESFilmicToneMapping;
    gl.toneMappingExposure = 1.05;

    const initW = Math.max(1, host.clientWidth || stage.clientWidth || 640);
    const initH = Math.max(1, host.clientHeight || stage.clientHeight || 300);
    gl.setSize(initW, initH, false);
    gl.domElement.style.width = '100%';
    gl.domElement.style.height = '100%';
    gl.domElement.style.display = 'block';
    host.innerHTML = '';
    host.appendChild(gl.domElement);

    const disposables: Array<{ dispose: () => void }> = [];
    const track = <T extends { dispose: () => void }>(x: T): T => {
      disposables.push(x);
      return x;
    };

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, initW / initH, 0.1, 100);
    camera.position.set(0, 2.55, 9.4);
    camera.lookAt(0, -0.05, 0);

    scene.add(new THREE.AmbientLight(0xffffff, 1.38));
    const keyLight = new THREE.DirectionalLight(0xfff7ed, 1.55);
    keyLight.position.set(5, 7, 5);
    scene.add(keyLight);
    const rimLight = new THREE.DirectionalLight(0xff5a1f, 0.85);
    rimLight.position.set(-5, 2, -4);
    scene.add(rimLight);

    const root = new THREE.Group();
    scene.add(root);

    const orangeGlow = track(createGlowTexture('orange'));
    const slateGlow = track(createGlowTexture('slate'));

    // 1. Zero-Flicker Central Aggregator Server
    const serverGroup = new THREE.Group();
    serverGroup.position.copy(SERVER_POS);
    root.add(serverGroup);

    const coreMat = track(
      new THREE.MeshStandardMaterial({
        color: 0xff5a1f,
        emissive: 0xff5a1f,
        emissiveIntensity: 0.48,
        roughness: 0.28,
        metalness: 0.12,
      }),
    );
    const coreMesh = new THREE.Mesh(track(new THREE.IcosahedronGeometry(0.4, 1)), coreMat);
    coreMesh.renderOrder = 1;
    serverGroup.add(coreMesh);

    const coreWire = new THREE.LineSegments(
      track(new THREE.EdgesGeometry(track(new THREE.IcosahedronGeometry(0.54, 1)))),
      track(new THREE.LineBasicMaterial({ color: 0x0f172a, transparent: true, opacity: 0.3, depthWrite: false })),
    );
    coreWire.renderOrder = 2;
    serverGroup.add(coreWire);

    const serverGlass = new THREE.Mesh(
      track(new THREE.SphereGeometry(0.68, 32, 32)),
      track(
        new THREE.MeshPhysicalMaterial({
          color: 0xffedd5,
          transparent: true,
          opacity: 0.24,
          depthWrite: false,
          roughness: 0.12,
          metalness: 0.04,
          clearcoat: 1,
          clearcoatRoughness: 0.08,
        }),
      ),
    );
    serverGlass.renderOrder = 3;
    serverGroup.add(serverGlass);

    const serverRing = new THREE.Mesh(
      track(new THREE.TorusGeometry(0.92, 0.015, 12, 96)),
      track(new THREE.MeshBasicMaterial({ color: 0xff5a1f, transparent: true, opacity: 0.58, depthWrite: false })),
    );
    serverRing.rotation.x = Math.PI * 0.44;
    serverRing.renderOrder = 2;
    serverGroup.add(serverRing);

    const waveMat = track(
      new THREE.MeshBasicMaterial({
        color: 0x10b981,
        transparent: true,
        opacity: 0,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    const waveMesh = new THREE.Mesh(track(new THREE.RingGeometry(0.68, 0.8, 64)), waveMat);
    waveMesh.rotation.x = Math.PI * 0.5;
    waveMesh.renderOrder = 2;
    serverGroup.add(waveMesh);

    // 2. Client Pillars + Head Spheres
    const positions = computeClientPositions(nodeCount);
    const sphereRadius = nodeCount <= 60 ? 0.125 : nodeCount <= 120 ? 0.095 : 0.075;

    const pillarGeo = track(new THREE.CylinderGeometry(sphereRadius * 0.52, sphereRadius * 0.62, 1, 10));
    const pillarMat = track(
      new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.36, metalness: 0.06 }),
    );
    const instancedPillars = new THREE.InstancedMesh(pillarGeo, pillarMat, nodeCount);
    instancedPillars.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    root.add(instancedPillars);

    const nodeGeo = track(new THREE.SphereGeometry(sphereRadius, 14, 14));
    const nodeMat = track(
      new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.28, metalness: 0.08 }),
    );
    const instancedNodes = new THREE.InstancedMesh(nodeGeo, nodeMat, nodeCount);
    instancedNodes.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    root.add(instancedNodes);

    const guideRadii =
      nodeCount <= 50 ? [1.75, 2.8] : nodeCount <= 120 ? [1.5, 2.3, 3.1] : [1.35, 2.0, 2.65, 3.3];
    const guideMat = track(
      new THREE.LineBasicMaterial({ color: 0xcbd5e1, transparent: true, opacity: 0.52 }),
    );
    guideRadii.forEach((rad) => {
      const ringPts: THREE.Vector3[] = [];
      for (let s = 0; s <= 96; s++) {
        const a = (s / 96) * Math.PI * 2;
        ringPts.push(new THREE.Vector3(Math.cos(a) * rad, -1.25, Math.sin(a) * rad));
      }
      root.add(new THREE.Line(track(new THREE.BufferGeometry().setFromPoints(ringPts)), guideMat));
    });

    const filamentStride = Math.max(1, Math.floor(nodeCount / 24));
    const filamentCurves: THREE.CatmullRomCurve3[] = [];
    const filamentPositions: number[] = [];
    for (let i = 0; i < nodeCount; i += filamentStride) {
      const p = positions[i];
      const startV = new THREE.Vector3(p.x, p.y + 0.35, p.z);
      const endV = new THREE.Vector3(SERVER_POS.x, SERVER_POS.y - 0.62, SERVER_POS.z);
      const midV = startV
        .clone()
        .lerp(endV, 0.5)
        .add(new THREE.Vector3(p.x * 0.16, 0.52, p.z * 0.16));
      const c = new THREE.CatmullRomCurve3([startV, midV, endV]);
      filamentCurves.push(c);
      const sampled = c.getPoints(16);
      for (let k = 0; k < sampled.length - 1; k++) {
        filamentPositions.push(
          sampled[k].x,
          sampled[k].y,
          sampled[k].z,
          sampled[k + 1].x,
          sampled[k + 1].y,
          sampled[k + 1].z,
        );
      }
    }
    const filamentGeo = track(new THREE.BufferGeometry());
    filamentGeo.setAttribute('position', new THREE.Float32BufferAttribute(filamentPositions, 3));
    const filamentMat = track(
      new THREE.LineBasicMaterial({ color: 0xff5a1f, transparent: true, opacity: 0.16 }),
    );
    root.add(new THREE.LineSegments(filamentGeo, filamentMat));

    // 3. Selected Node Ring + Beam
    const selRing = new THREE.Mesh(
      track(new THREE.TorusGeometry(sphereRadius * 2.1, 0.024, 10, 48)),
      track(new THREE.MeshBasicMaterial({ color: 0xff5a1f, transparent: true, opacity: 0.95 })),
    );
    selRing.rotation.x = Math.PI * 0.5;
    selRing.visible = false;
    root.add(selRing);

    const selBeamGeo = track(new THREE.BufferGeometry());
    selBeamGeo.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(25 * 3), 3));
    const selBeam = new THREE.Line(
      selBeamGeo,
      track(new THREE.LineBasicMaterial({ color: 0xff5a1f, transparent: true, opacity: 0.92 })),
    );
    selBeam.visible = false;
    root.add(selBeam);

    // 4. Step-synced W / ΔW packets
    const PACKET_COUNT = Math.min(28, Math.max(12, filamentCurves.length));
    const packetGeo = track(new THREE.SphereGeometry(0.052, 8, 8));
    interface LivePacket {
      curveIdx: number;
      mesh: THREE.Mesh;
      mat: THREE.MeshBasicMaterial;
      haloMat: THREE.SpriteMaterial;
      t: number;
      speed: number;
    }
    const packets: LivePacket[] = [];
    for (let i = 0; i < PACKET_COUNT; i++) {
      const pMat = track(
        new THREE.MeshBasicMaterial({ color: 0xff5a1f, transparent: true, opacity: 0 }),
      );
      const mesh = new THREE.Mesh(packetGeo, pMat);
      const hMat = track(
        new THREE.SpriteMaterial({
          map: orangeGlow,
          transparent: true,
          opacity: 0,
          depthWrite: false,
        }),
      );
      const halo = new THREE.Sprite(hMat);
      halo.scale.set(0.28, 0.28, 1);
      mesh.add(halo);
      root.add(mesh);
      packets.push({
        curveIdx: i % Math.max(1, filamentCurves.length),
        mesh,
        mat: pMat,
        haloMat: hMat,
        t: i / PACKET_COUNT,
        speed: 0.48 + (i % 5) * 0.07,
      });
    }

    // 5. Orbit + Raycasting
    const orbit = {
      yaw: 0.28,
      pitch: 0.08,
      velYaw: 0,
      velPitch: 0,
      dragging: false,
      movedPx: 0,
      lastX: 0,
      lastY: 0,
      ndcX: -99,
      ndcY: -99,
    };
    const raycaster = new THREE.Raycaster();
    const pointerVec = new THREE.Vector2();

    const updateNdc = (e: PointerEvent) => {
      const rect = stage.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;
      orbit.ndcX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      orbit.ndcY = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    };

    const pickNode = (): LiveFlNodeSample | null => {
      pointerVec.set(orbit.ndcX, orbit.ndcY);
      raycaster.setFromCamera(pointerVec, camera);
      const hits = raycaster.intersectObjects([instancedNodes, instancedPillars], false);
      if (hits.length > 0 && hits[0].instanceId !== undefined) {
        return nodesRef.current[hits[0].instanceId] ?? null;
      }
      return null;
    };

    const onPointerDown = (e: PointerEvent) => {
      if ((e.target as HTMLElement)?.closest('button')) return;
      orbit.dragging = true;
      orbit.movedPx = 0;
      orbit.lastX = e.clientX;
      orbit.lastY = e.clientY;
      orbit.velYaw = 0;
      orbit.velPitch = 0;
      setDragging(true);
      try {
        stage.setPointerCapture(e.pointerId);
      } catch {
        // ignore
      }
    };

    const onPointerMove = (e: PointerEvent) => {
      updateNdc(e);
      if (orbit.dragging) {
        const dx = e.clientX - orbit.lastX;
        const dy = e.clientY - orbit.lastY;
        orbit.movedPx += Math.abs(dx) + Math.abs(dy);
        orbit.lastX = e.clientX;
        orbit.lastY = e.clientY;
        orbit.velYaw = dx * 0.0055;
        orbit.velPitch = dy * 0.004;
        orbit.yaw += orbit.velYaw;
        orbit.pitch = Math.max(-0.32, Math.min(0.62, orbit.pitch + orbit.velPitch));
        return;
      }
      const found = pickNode();
      stage.style.cursor = found ? 'pointer' : 'grab';
      setHoveredNode(found);
    };

    const onPointerUp = (e: PointerEvent) => {
      if (!orbit.dragging) return;
      orbit.dragging = false;
      setDragging(false);
      try {
        if (stage.hasPointerCapture(e.pointerId)) stage.releasePointerCapture(e.pointerId);
      } catch {
        // ignore
      }
      if (orbit.movedPx < 6) {
        updateNdc(e);
        const found = pickNode();
        if (found) onSelectRef.current(found.clientId);
      }
    };

    const onPointerLeave = () => {
      orbit.ndcX = -99;
      orbit.ndcY = -99;
      setHoveredNode(null);
    };

    stage.addEventListener('pointerdown', onPointerDown);
    stage.addEventListener('pointermove', onPointerMove);
    stage.addEventListener('pointerup', onPointerUp);
    stage.addEventListener('pointercancel', onPointerUp);
    stage.addEventListener('pointerleave', onPointerLeave);

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

    const dummy = new THREE.Object3D();
    const tmpColor = new THREE.Color();
    const currentHeights = new Float32Array(nodeCount).fill(0.1);
    let lastNow = performance.now();
    let waveProg = 0;

    const animate = (now: number) => {
      if (disposed) return;
      if (document.hidden) {
        rafId = 0;
        return;
      }
      rafId = requestAnimationFrame(animate);
      const dt = Math.min(0.05, Math.max(0.001, (now - lastNow) / 1000));
      lastNow = now;

      const isRun = runningRef.current;
      const step = stepRef.current;
      const liveNodes = nodesRef.current;
      const selId = selectedIdRef.current;
      const fMode = filterRef.current;
      const curLens = lensRef.current;
      const maxLog = maxLogRef.current;

      if (!orbit.dragging) {
        orbit.velYaw *= Math.pow(0.08, dt);
        orbit.velPitch *= Math.pow(0.08, dt);
        orbit.yaw += orbit.velYaw;
        orbit.pitch = Math.max(-0.32, Math.min(0.62, orbit.pitch + orbit.velPitch));
        if (!pausedRef.current && !reducedMotion) {
          orbit.yaw += dt * (isRun ? 0.22 : 0.08);
        }
      }
      root.rotation.y = orbit.yaw;
      root.rotation.x = orbit.pitch;

      coreMesh.rotation.y += dt * (isRun ? 1.3 : 0.45);
      coreWire.rotation.y -= dt * 0.32;
      serverRing.rotation.z += dt * (isRun ? 0.8 : 0.3);

      const isBroadcast = step === 0;
      const isLocalTrain = step === 1;
      const isUpload = step === 2;
      const isAggregate = step === 3 || step === 4;

      coreMat.emissiveIntensity = isAggregate ? 0.92 : isUpload ? 0.72 : 0.48;

      if (isAggregate) {
        waveProg = (waveProg + dt * (isRun ? 1.15 : 0.65)) % 1;
        waveMesh.scale.setScalar(1 + waveProg * 2.6);
        waveMat.opacity = (1 - waveProg) * 0.62;
      } else {
        waveProg = 0;
        waveMat.opacity = 0;
      }

      let selectedIdx = -1;
      let selTopY = -1.1;
      const lerpAlpha = Math.min(1, dt * 8);

      for (let i = 0; i < nodeCount; i++) {
        const nd = liveNodes[i];
        const basePos = positions[i];
        const isSel = nd && selId === nd.clientId;
        if (isSel) selectedIdx = i;

        const targetH = pillarHeight(nd, curLens, maxLog);
        currentHeights[i] += (targetH - currentHeights[i]) * lerpAlpha;
        const h = currentHeights[i];

        const isAlert =
          curLens === 'noniid'
            ? (nd?.drift ?? 0) >= 0.55 && !nd?.isDropped
            : (nd?.latencyMs ?? 0) >= 65 && !nd?.isDropped;

        const matchesFilter =
          fMode === 'all' ||
          (fMode === 'highlight' && isAlert) ||
          (fMode === 'dropped' && Boolean(nd?.isDropped));
        const dimmed = !matchesFilter && !isSel;

        dummy.position.set(basePos.x, basePos.y + h * 0.5, basePos.z);
        dummy.scale.set(isSel ? 1.35 : 1.0, h, isSel ? 1.35 : 1.0);
        dummy.updateMatrix();
        instancedPillars.setMatrixAt(i, dummy.matrix);

        const pulseLift =
          isLocalTrain && !nd?.isDropped ? Math.sin(now * 0.009 + i * 0.4) * 0.04 : 0;
        const headY = basePos.y + h + sphereRadius * 0.75 + pulseLift;
        if (isSel) selTopY = headY;

        dummy.position.set(basePos.x, headY, basePos.z);
        const headScale = isSel ? 1.45 : nd?.isDropped ? 0.75 : 1.0;
        dummy.scale.setScalar(headScale);
        dummy.updateMatrix();
        instancedNodes.setMatrixAt(i, dummy.matrix);

        tmpColor.setHex(
          curLens === 'noniid' ? colorForDrift(nd, dimmed) : colorForLatency(nd, dimmed),
        );
        instancedPillars.setColorAt(i, tmpColor);
        instancedNodes.setColorAt(i, tmpColor);
      }

      instancedPillars.instanceMatrix.needsUpdate = true;
      instancedNodes.instanceMatrix.needsUpdate = true;
      if (instancedPillars.instanceColor) instancedPillars.instanceColor.needsUpdate = true;
      if (instancedNodes.instanceColor) instancedNodes.instanceColor.needsUpdate = true;

      if (selectedIdx >= 0) {
        const sp = positions[selectedIdx];
        const selNode = liveNodes[selectedIdx];
        selRing.visible = true;
        selRing.position.set(sp.x, selTopY, sp.z);
        selRing.scale.setScalar(1 + Math.sin(now * 0.006) * 0.12);

        if (!selNode?.isDropped) {
          selBeam.visible = true;
          const startV = new THREE.Vector3(sp.x, selTopY + sphereRadius, sp.z);
          const endV = new THREE.Vector3(SERVER_POS.x, SERVER_POS.y - 0.62, SERVER_POS.z);
          const midV = startV
            .clone()
            .lerp(endV, 0.5)
            .add(new THREE.Vector3(sp.x * 0.18, 0.6, sp.z * 0.18));
          const bCurve = new THREE.CatmullRomCurve3([startV, midV, endV]);
          const bPts = bCurve.getPoints(24);
          const arr = selBeamGeo.attributes.position.array as Float32Array;
          for (let k = 0; k < bPts.length; k++) {
            arr[k * 3] = bPts[k].x;
            arr[k * 3 + 1] = bPts[k].y;
            arr[k * 3 + 2] = bPts[k].z;
          }
          selBeamGeo.attributes.position.needsUpdate = true;
        } else {
          selBeam.visible = false;
        }
      } else {
        selRing.visible = false;
        selBeam.visible = false;
      }

      filamentMat.color.setHex(isBroadcast ? 0x0f172a : 0xff5a1f);
      filamentMat.opacity = isUpload ? 0.34 : isBroadcast ? 0.26 : 0.14;

      const showPackets = !reducedMotion && (isBroadcast || isUpload);
      for (let i = 0; i < packets.length; i++) {
        const pk = packets[i];
        const curve = filamentCurves[pk.curveIdx];
        if (!curve || !showPackets) {
          pk.mat.opacity = 0;
          pk.haloMat.opacity = 0;
          continue;
        }
        pk.t = (pk.t + dt * pk.speed * (isRun ? 1.45 : 0.85)) % 1;
        const curveT = isBroadcast ? 1 - pk.t : pk.t;
        curve.getPointAt(curveT, pk.mesh.position);
        const fade = Math.sin(pk.t * Math.PI);
        pk.mat.color.setHex(isBroadcast ? 0x0f172a : 0xff5a1f);
        pk.mat.opacity = 0.9 * fade;
        pk.haloMat.map = isBroadcast ? slateGlow : orangeGlow;
        pk.haloMat.opacity = 0.7 * fade;
      }

      gl.render(scene, camera);
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
      if (rafId) cancelAnimationFrame(rafId);
      ro.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
      stage.removeEventListener('pointerdown', onPointerDown);
      stage.removeEventListener('pointermove', onPointerMove);
      stage.removeEventListener('pointerup', onPointerUp);
      stage.removeEventListener('pointercancel', onPointerUp);
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
  }, [nodeCount]);

  const stepSpec = STEP_SPECS[Math.max(0, Math.min(4, effectiveStep))] ?? STEP_SPECS[2];
  const alertCount =
    lens === 'noniid'
      ? nodes.filter((n) => n.drift >= 0.55 && !n.isDropped).length
      : nodes.filter((n) => (n.latencyMs ?? 0) >= 65 && !n.isDropped).length;
  const droppedCount = nodes.filter((n) => n.isDropped).length;

  return (
    <div
      className={`relative flex flex-col w-full overflow-hidden rounded-xl border border-slate-200/90 select-none ${className}`}
      style={{
        background:
          'radial-gradient(ellipse 68% 60% at 50% 42%, rgba(255,90,31,0.09) 0%, rgba(255,138,91,0.03) 46%, rgba(255,255,255,0) 74%), radial-gradient(rgba(15,23,42,0.07) 1px, transparent 1px), rgba(255,255,255,0.84)',
        backgroundSize: '100% 100%, 18px 18px, 100% 100%',
      }}
    >
      {/* 1. Research Lens Switch + 5-Step FL Scrubber */}
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/75 bg-white/88 px-3 py-2 backdrop-blur-md">
        {/* Dual Research Lens */}
        <div className="inline-flex items-center rounded-lg border border-slate-200/90 bg-slate-100/80 p-0.5">
          <button
            type="button"
            onClick={() => {
              setLens('noniid');
              setFilterMode('all');
            }}
            className={`cursor-pointer rounded-md px-2.5 py-1 font-mono text-[10.5px] font-semibold transition-all ${
              lens === 'noniid'
                ? 'bg-white text-[#C2410C] shadow-xs ring-1 ring-orange-200/80'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Non-IID &amp; Drift
          </button>
          <button
            type="button"
            onClick={() => {
              setLens('latency');
              setFilterMode('all');
            }}
            className={`cursor-pointer rounded-md px-2.5 py-1 font-mono text-[10.5px] font-semibold transition-all ${
              lens === 'latency'
                ? 'bg-white text-[#C2410C] shadow-xs ring-1 ring-orange-200/80'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Hiệu năng (Latency)
          </button>
        </div>

        {/* 5-step interactive scrubber */}
        <div className="flex flex-wrap items-center gap-1">
          {STEP_SPECS.map((s) => {
            const active = effectiveStep === s.id;
            return (
              <button
                key={s.id}
                type="button"
                disabled={running}
                onClick={() => setPreviewStep(s.id)}
                className={`rounded-md px-1.5 py-0.5 font-mono text-[10px] font-semibold transition-all ${
                  active
                    ? 'bg-[#FFF7ED] text-[#C2410C] ring-1 ring-[#FDBA74]'
                    : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
                } ${running ? 'cursor-default' : 'cursor-pointer'}`}
              >
                {s.short}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() =>
              setFilterMode((m) => (m === 'all' ? 'highlight' : m === 'highlight' ? 'dropped' : 'all'))
            }
            className={`inline-flex cursor-pointer items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold transition-colors ${
              filterMode !== 'all'
                ? 'border-orange-300 bg-[#FFF7ED] text-[#C2410C]'
                : 'border-slate-200 bg-white text-slate-600 hover:border-orange-200'
            }`}
          >
            <Filter size={10} />
            <span>
              {filterMode === 'all'
                ? 'Lọc: Tất cả'
                : filterMode === 'highlight'
                  ? lens === 'noniid'
                    ? `Drift cao (${alertCount})`
                    : `Straggler (${alertCount})`
                  : `Offline (${droppedCount})`}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setPaused((p) => !p)}
            className="inline-flex cursor-pointer items-center gap-1 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10.5px] font-semibold text-slate-700 hover:border-orange-300 hover:text-[#C2410C]"
          >
            {paused ? <Play size={10} /> : <Pause size={10} />}
            <span>{paused ? 'Xoay' : 'Dừng'}</span>
          </button>
        </div>
      </div>

      {/* 2. Unobstructed 3D Research Stage */}
      <div
        ref={stageRef}
        className={`relative h-[305px] w-full overflow-hidden ${
          dragging ? 'cursor-grabbing' : 'cursor-grab'
        }`}
      >
        <div ref={hostRef} className="absolute inset-0 h-full w-full" />

        {/* Top-left Lens Meaning Badge */}
        <div className="pointer-events-none absolute top-2.5 left-2.5 z-10 rounded-lg border border-orange-200/80 bg-white/90 px-2.5 py-1.5 shadow-xs backdrop-blur-md">
          <div className="flex items-center gap-1.5 font-mono text-[9.5px] font-bold text-[#C2410C]">
            <Radio size={10} className={running ? 'text-[#FF5A1F] animate-pulse' : 'text-[#FF5A1F]'} />
            {algorithm.toUpperCase()} · VÒNG {currentRound}/{totalRounds}
          </div>
          <div className="text-[10px] text-slate-600 mt-0.5">
            {lens === 'noniid'
              ? 'Chiều cao = Trọng số dữ liệu p_k (log) · Màu = Client Drift'
              : 'Chiều cao = Độ trễ cục bộ (ms) · Màu = Ngưỡng Straggler'}
          </div>
        </div>

        {/* Bottom-left Compact Scale Legend */}
        <div className="pointer-events-none absolute bottom-2.5 left-2.5 z-10 flex items-center gap-2.5 rounded-full border border-slate-200/90 bg-white/88 px-2.5 py-1 font-mono text-[9.5px] text-slate-600 backdrop-blur-md">
          {lens === 'noniid' ? (
            <>
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#10B981]" /> Drift thấp (&lt;0.28)
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#F59E0B]" /> Trung bình
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#EF4444]" /> Drift cao (≥0.55)
              </span>
            </>
          ) : (
            <>
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#10B981]" /> &lt;35ms
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#F59E0B]" /> 35–65ms
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-[#EF4444]" /> ≥65ms
              </span>
            </>
          )}
        </div>

        {/* Top-right Live Hover Pill */}
        {hoveredNode && (
          <div className="pointer-events-none absolute top-2.5 right-2.5 z-10 rounded-lg border border-slate-200 bg-white/95 px-2.5 py-1.5 shadow-sm backdrop-blur-md">
            <div className="font-mono text-[10px] font-bold text-slate-900">{hoveredNode.name}</div>
            <div className="font-mono text-[10px] text-slate-600">
              p_k={hoveredNode.weightSharePct.toFixed(2)}% · drift={hoveredNode.drift.toFixed(2)} ·{' '}
              {hoveredNode.isDropped
                ? 'OFFLINE'
                : hoveredNode.latencyMs !== null
                  ? `${hoveredNode.latencyMs.toFixed(1)} ms`
                  : 'chờ'}
            </div>
          </div>
        )}

        {webglError && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/90 text-xs text-slate-600">
            Trình duyệt không hỗ trợ WebGL — chuyển sang tab Lưới ô 2D.
          </div>
        )}
      </div>

      {/* 3. Research Fault-Injection Bar (Affects Live Simulation / p95 / Aggregation) */}
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200/75 bg-slate-50/90 px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="inline-flex shrink-0 items-center rounded px-1.5 py-0.5 font-mono text-[9.5px] font-bold text-white"
            style={{ backgroundColor: stepSpec.color }}
          >
            {stepSpec.short}
          </span>
          <span className="text-[11px] font-medium text-slate-700 truncate">{stepSpec.desc}</span>
        </div>

        {selectedNode && (
          <div className="flex flex-wrap items-center gap-1.5 shrink-0">
            <span className="font-mono text-[10px] font-bold text-slate-500">
              Node #{selectedNode.clientId}:
            </span>
            <button
              type="button"
              disabled={selectedNode.isDropped}
              onClick={() => onToggleStraggler?.(selectedNode.clientId)}
              className={`inline-flex cursor-pointer items-center gap-1 rounded-md border px-2 py-1 text-[10.5px] font-semibold transition-colors disabled:opacity-45 disabled:cursor-not-allowed ${
                selectedNode.isStraggler
                  ? 'border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-amber-300 hover:text-amber-700'
              }`}
              title="Tiêm trễ mạng +120ms (tác động trực tiếp lên p95 của vòng chạy)"
            >
              <Turtle size={11} />
              <span>{selectedNode.isStraggler ? 'Bỏ trễ (+120ms)' : 'Tiêm trễ Straggler'}</span>
            </button>

            <button
              type="button"
              onClick={() => onToggleDropout?.(selectedNode.clientId)}
              className={`inline-flex cursor-pointer items-center gap-1 rounded-md border px-2 py-1 text-[10.5px] font-semibold transition-colors ${
                selectedNode.isDropped
                  ? 'border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-rose-300 hover:text-rose-700'
              }`}
              title="Loại client khỏi vòng tổng hợp để kiểm chứng khả năng chịu dropout"
            >
              {selectedNode.isDropped ? <Wifi size={11} /> : <WifiOff size={11} />}
              <span>{selectedNode.isDropped ? 'Kết nối lại' : 'Ngắt node (Dropout)'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default LiveFlTopology3D;
