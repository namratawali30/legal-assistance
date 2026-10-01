import { useEffect, useRef } from "react";
import * as THREE from "three";

export default function ParticleVolumeFooter({ className = "" }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || 200;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100);
    camera.position.z = 5;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);

    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    container.appendChild(renderer.domElement);

    // Custom Volumetric Particle GLSL Shaders
    const particleCount = 200;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const scales = new Float32Array(particleCount);
    const opacities = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 12;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 4;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 6;
      scales[i] = Math.random() * 8 + 4;
      opacities[i] = Math.random() * 0.6 + 0.2;
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("aScale", new THREE.BufferAttribute(scales, 1));
    geometry.setAttribute("aOpacity", new THREE.BufferAttribute(opacities, 1));

    const vertexShader = `
      attribute float aScale;
      attribute float aOpacity;
      varying float vOpacity;
      uniform float uTime;

      void main() {
        vOpacity = aOpacity;
        vec3 pos = position;
        pos.y += sin(uTime * 0.5 + pos.x * 0.5) * 0.2;
        pos.x += cos(uTime * 0.3 + pos.y * 0.5) * 0.1;

        vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
        gl_PointSize = aScale * (10.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
      }
    `;

    const fragmentShader = `
      varying float vOpacity;

      void main() {
        float dist = length(gl_PointCoord - vec2(0.5));
        if (dist > 0.5) discard;
        float strength = pow(1.0 - (dist * 2.0), 2.0);

        // Gold & Warm bronze legal glow
        vec3 color = mix(vec3(0.96, 0.62, 0.04), vec3(0.38, 0.40, 0.94), dist * 1.5);
        gl_FragColor = vec4(color, strength * vOpacity * 0.8);
      }
    `;

    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        uTime: { value: 0 },
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

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

      const elapsed = clock.getElapsedTime();
      if (!prefersReducedMotion) {
        material.uniforms.uTime.value = elapsed;
        particles.rotation.y = elapsed * 0.03;
      }
      renderer.render(scene, camera);
    };

    renderLoop();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight || 200;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
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
      className={`relative w-full h-32 overflow-hidden pointer-events-none ${className}`}
      aria-hidden="true"
    />
  );
}
