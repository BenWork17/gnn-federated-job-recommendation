import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

export interface WarmSilkAuroraProps {
  className?: string;
}

const VERTEX_SHADER = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  precision mediump float;

  uniform float uTime;
  uniform vec2 uResolution;
  uniform vec2 uPointer;

  varying vec2 vUv;

  // Compact 2D Simplex Noise (Ashima / Gustavson)
  vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec3 permute(vec3 x) { return mod289(((x * 34.0) + 1.0) * x); }

  float snoise(vec2 v) {
    const vec4 C = vec4(
      0.211324865405187,
      0.366025403784439,
      -0.577350269189626,
      0.024390243902439
    );
    vec2 i  = floor(v + dot(v, C.yy));
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod289(i);
    vec3 p = permute(
      permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0)
    );
    vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
    m = m * m;
    m = m * m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
    vec3 g;
    g.x  = a0.x * x0.x + h.x * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
  }

  float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    mat2 rot = mat2(0.80, 0.60, -0.60, 0.80);
    for (int i = 0; i < 4; i++) {
      v += a * snoise(p);
      p = rot * p * 1.92 + vec2(1.7, 9.2);
      a *= 0.5;
    }
    return v;
  }

  void main() {
    vec2 uv = vUv;
    float aspect = uResolution.x / max(uResolution.y, 1.0);
    vec2 p = vec2((uv.x - 0.5) * aspect, uv.y - 0.5);

    // Subtle organic pointer drift
    vec2 ptr = (uPointer - 0.5) * vec2(aspect, 1.0) * 0.22;
    float t = uTime * 0.085;

    // Domain-warped silk flow (ThreeUI GradientOrb / AtTheHorizon inspired)
    vec2 q = vec2(
      fbm(p * 1.15 + vec2(t * 0.9, -t * 0.6)),
      fbm(p * 1.15 + vec2(-t * 0.7, t * 0.8) + vec2(3.4, 1.8))
    );

    float silkA = fbm(p * 1.35 + q * 0.72 - ptr * 0.45 + vec2(t * 0.55, t * 0.25));
    float silkB = fbm(p * 1.85 - q * 0.62 + ptr * 0.35 + vec2(-t * 0.4, t * 0.65));

    // Soft breathing envelopes
    float breath = 0.92 + 0.08 * sin(uTime * 0.45);
    float bandOrange = smoothstep(-0.12, 0.68, silkA) * breath;
    float bandApricot = smoothstep(-0.22, 0.62, silkB);

    // Architectural warm anchor near upper-right & gentle pointer glow
    float topRightAnchor = exp(-length(p - vec2(0.46 * aspect * 0.55, 0.28) - ptr * 0.35) * 1.65);
    float lowerLeftMist = exp(-length(p - vec2(-0.42 * aspect * 0.55, -0.34)) * 1.9);

    // Base warm paper (#F8FAFC)
    vec3 basePaper = vec3(0.9725, 0.9804, 0.9882);
    vec3 signalOrange = vec3(1.0, 0.3529, 0.1216);  // #FF5A1F
    vec3 warmApricot  = vec3(0.9843, 0.5725, 0.2353); // #FB923C
    vec3 softWarmTint = vec3(1.0, 0.9686, 0.9294);    // #FFF7ED

    // Blend gently: Signal Orange 7-11% alpha, Apricot 5-8% alpha
    float orangeAlpha = clamp(bandOrange * 0.082 + topRightAnchor * 0.048, 0.0, 0.115);
    float apricotAlpha = clamp(bandApricot * 0.068 + lowerLeftMist * 0.032, 0.0, 0.085);

    vec3 col = mix(basePaper, softWarmTint, clamp(bandOrange * 0.35 + topRightAnchor * 0.25, 0.0, 0.45));
    col = mix(col, warmApricot, apricotAlpha);
    col = mix(col, signalOrange, orangeAlpha);

    // Crisp subtle horizontal horizon sheen
    float horizonGlow = exp(-abs(uv.y - 0.74 - silkA * 0.08) * 5.2) * 0.035;
    col = mix(col, signalOrange, horizonGlow);

    gl_FragColor = vec4(col, 1.0);
  }
`;

export const WarmSilkAurora: React.FC<WarmSilkAuroraProps> = ({ className = '' }) => {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    const container = hostRef.current;
    if (!container) return;

    const reducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: false,
        antialias: false,
        powerPreference: 'low-power',
        depth: false,
        stencil: false,
      });
    } catch {
      setFallback(true);
      return;
    }

    if (!renderer.getContext()) {
      renderer.dispose();
      setFallback(true);
      return;
    }

    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    renderer.setPixelRatio(dpr);
    renderer.setSize(window.innerWidth, window.innerHeight, false);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.display = 'block';
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    const uniforms = {
      uTime: { value: 0 },
      uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
      uPointer: { value: new THREE.Vector2(0.55, 0.45) },
    };

    const geometry = new THREE.PlaneGeometry(2, 2);
    const material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms,
      depthWrite: false,
      depthTest: false,
    });

    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    const targetPointer = new THREE.Vector2(0.55, 0.45);
    const smoothPointer = new THREE.Vector2(0.55, 0.45);

    const onPointerMove = (e: PointerEvent) => {
      const w = Math.max(window.innerWidth, 1);
      const h = Math.max(window.innerHeight, 1);
      targetPointer.set(e.clientX / w, 1 - e.clientY / h);
    };

    const onResize = () => {
      const w = Math.max(window.innerWidth, 1);
      const h = Math.max(window.innerHeight, 1);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      renderer.setSize(w, h, false);
      uniforms.uResolution.value.set(w, h);
      if (reducedMotion) {
        renderer.render(scene, camera);
      }
    };

    let rafId = 0;
    let lastNow = performance.now();
    let elapsed = 1.8;
    let disposed = false;

    const tick = (now: number) => {
      if (disposed) return;
      if (document.hidden) {
        rafId = 0;
        return;
      }
      rafId = requestAnimationFrame(tick);
      const dt = Math.min(0.05, Math.max(0.001, (now - lastNow) / 1000));
      lastNow = now;
      elapsed += dt;

      smoothPointer.lerp(targetPointer, Math.min(1, dt * 2.4));
      uniforms.uTime.value = elapsed;
      uniforms.uPointer.value.copy(smoothPointer);
      renderer.render(scene, camera);
    };

    const onVisibilityChange = () => {
      if (disposed || reducedMotion) return;
      if (document.hidden) {
        if (rafId) {
          cancelAnimationFrame(rafId);
          rafId = 0;
        }
      } else if (!rafId) {
        lastNow = performance.now();
        rafId = requestAnimationFrame(tick);
      }
    };

    window.addEventListener('pointermove', onPointerMove, { passive: true });
    window.addEventListener('resize', onResize, { passive: true });
    document.addEventListener('visibilitychange', onVisibilityChange);

    // Always render initial frame cleanly
    uniforms.uTime.value = elapsed;
    renderer.render(scene, camera);

    if (!reducedMotion && !document.hidden) {
      rafId = requestAnimationFrame(tick);
    }

    return () => {
      disposed = true;
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('resize', onResize);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      ref={hostRef}
      aria-hidden="true"
      className={`fixed inset-0 z-0 pointer-events-none select-none ${className}`}
      style={
        fallback
          ? {
              background:
                'radial-gradient(ellipse 68% 58% at 78% 18%, rgba(255,90,31,0.10), transparent 62%), radial-gradient(ellipse 60% 52% at 22% 82%, rgba(251,146,60,0.08), transparent 60%), #F8FAFC',
            }
          : undefined
      }
    />
  );
};

export default WarmSilkAurora;
