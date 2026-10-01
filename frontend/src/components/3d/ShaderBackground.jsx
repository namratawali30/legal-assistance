import { useEffect, useRef } from "react";
import * as THREE from "three";

export default function ShaderBackground({ className = "" }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10);
    camera.position.z = 1;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setSize(width, height);

    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    container.appendChild(renderer.domElement);

    const geometry = new THREE.PlaneGeometry(2, 2);

    const vertexShader = `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = vec4(position, 1.0);
      }
    `;

    const fragmentShader = `
      uniform float uTime;
      uniform vec2 uResolution;
      varying vec2 vUv;

      void main() {
        vec2 st = gl_FragCoord.xy / uResolution.xy;

        // Soft Courtroom Radial Light Shafts
        float dist = distance(st, vec2(0.3, 0.2));
        float light1 = smoothstep(0.8, 0.0, dist);

        float dist2 = distance(st, vec2(0.85, 0.8));
        float light2 = smoothstep(0.7, 0.0, dist2);

        // Chromatic & Gold subtle tone
        vec3 col1 = vec3(0.04, 0.06, 0.12); // Midnight
        vec3 col2 = vec3(0.31, 0.27, 0.64); // Indigo
        vec3 col3 = vec3(0.85, 0.55, 0.05); // Warm Gold

        vec3 color = mix(col1, col2, light1 * 0.4);
        color = mix(color, col3, light2 * 0.15);

        // Subtle moving gradient wave
        float wave = sin(st.x * 4.0 + uTime * 0.2) * cos(st.y * 4.0 + uTime * 0.2) * 0.02;
        color += wave;

        gl_FragColor = vec4(color, 0.45);
      }
    `;

    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uResolution: { value: new THREE.Vector2(width, height) },
      },
      transparent: true,
    });

    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    let frameId;
    const clock = new THREE.Clock();

    let isVisible = true;
    const observer = new IntersectionObserver(([entry]) => {
      isVisible = entry.isIntersecting;
    }, { threshold: 0.05 });
    observer.observe(container);

    const renderLoop = () => {
      frameId = requestAnimationFrame(renderLoop);
      if (!isVisible) return;

      if (!prefersReducedMotion) {
        material.uniforms.uTime.value = clock.getElapsedTime();
      }
      renderer.render(scene, camera);
    };

    renderLoop();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth || window.innerWidth;
      const h = container.clientHeight || window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      material.uniforms.uResolution.value.set(w, h);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      if (frameId) cancelAnimationFrame(frameId);
      window.removeEventListener("resize", handleResize);
      observer.disconnect();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div
      ref={mountRef}
      className={`fixed inset-0 pointer-events-none z-0 ${className}`}
      aria-hidden="true"
    />
  );
}
