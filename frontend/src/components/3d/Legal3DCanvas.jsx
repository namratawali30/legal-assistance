import { useEffect, useRef } from "react";
import * as THREE from "three";
import gsap from "gsap";

export default function Legal3DCanvas({ className = "", interactive = true }) {
  const containerRef = useRef(null);
  const animFrameId = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // 1. Scene Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x70b4e6); // Vibrant sky blue
    scene.fog = new THREE.FogExp2(0xb5d8f7, 0.025);

    // 2. Camera Setup
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;
    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100);
    camera.position.set(0, 1.6, 6.2);
    camera.lookAt(0, 1.5, 0);

    // 3. Renderer Setup
    const renderer = new THREE.WebGLRenderer({
      alpha: false,
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;

    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    container.appendChild(renderer.domElement);

    // 4. Realistic Outdoor Lighting
    const sunLight = new THREE.DirectionalLight(0xfff5e6, 3.2);
    sunLight.position.set(5, 8, 4);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.bias = -0.0001;
    scene.add(sunLight);

    const skyLight = new THREE.HemisphereLight(0x87ceeb, 0xd4c2a5, 1.4);
    scene.add(skyLight);

    const goldBounce = new THREE.PointLight(0xf59e0b, 2.0, 10);
    goldBounce.position.set(0, 2, 2);
    scene.add(goldBounce);

    // 5. Materials
    const stoneMaterial = new THREE.MeshStandardMaterial({
      color: 0xe3dac9, // Warm limestone
      roughness: 0.65,
      metalness: 0.1,
    });

    const bronzeStatueMaterial = new THREE.MeshStandardMaterial({
      color: 0x4a3424, // Warm bronze
      metalness: 0.88,
      roughness: 0.3,
      emissive: 0x221307,
      emissiveIntensity: 0.2,
    });

    const goldChainMaterial = new THREE.MeshStandardMaterial({
      color: 0xd97706,
      metalness: 0.95,
      roughness: 0.15,
    });

    const potMaterial = new THREE.MeshStandardMaterial({
      color: 0x9a5232, // Terracotta
      roughness: 0.8,
    });

    const leafMaterial = new THREE.MeshStandardMaterial({
      color: 0x3d6139,
      roughness: 0.7,
    });

    // 6. Environment Construction

    // A. Terrace Floor
    const floorGeo = new THREE.PlaneGeometry(30, 30);
    const floorMesh = new THREE.Mesh(floorGeo, stoneMaterial);
    floorMesh.rotation.x = -Math.PI / 2;
    floorMesh.position.y = 0;
    floorMesh.receiveShadow = true;
    scene.add(floorMesh);

    // Floor tile lines
    const gridHelper = new THREE.GridHelper(24, 24, 0xb8ad9e, 0xc7bcae);
    gridHelper.position.y = 0.01;
    scene.add(gridHelper);

    // B. Neoclassical Stone Archway
    const archGroup = new THREE.Group();

    // Twin Columns
    const colLeft = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.42, 4.2, 32), stoneMaterial);
    colLeft.position.set(-2.2, 2.1, -1);
    colLeft.castShadow = true;
    archGroup.add(colLeft);

    const colRight = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.42, 4.2, 32), stoneMaterial);
    colRight.position.set(2.2, 2.1, -1);
    colRight.castShadow = true;
    archGroup.add(colRight);

    // Arch Capital Tops
    const capGeo = new THREE.BoxGeometry(0.9, 0.2, 0.9);
    const capLeft = new THREE.Mesh(capGeo, stoneMaterial);
    capLeft.position.set(-2.2, 4.2, -1);
    archGroup.add(capLeft);

    const capRight = new THREE.Mesh(capGeo, stoneMaterial);
    capRight.position.set(2.2, 4.2, -1);
    archGroup.add(capRight);

    // Semi-circular Arch Curve
    const archCurveGeo = new THREE.TorusGeometry(2.2, 0.35, 24, 48, Math.PI);
    const archCurve = new THREE.Mesh(archCurveGeo, stoneMaterial);
    archCurve.position.set(0, 4.2, -1);
    archCurve.castShadow = true;
    archGroup.add(archCurve);

    scene.add(archGroup);

    // C. Terrace Balustrade Railings (Left & Right Background)
    const buildBalustrade = (startX, endX, z) => {
      const railGroup = new THREE.Group();
      const topRail = new THREE.Mesh(new THREE.BoxGeometry(Math.abs(endX - startX), 0.15, 0.3), stoneMaterial);
      topRail.position.set((startX + endX) / 2, 0.9, z);
      railGroup.add(topRail);

      const count = 10;
      const step = (endX - startX) / count;
      for (let i = 0; i <= count; i++) {
        const post = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.8, 16), stoneMaterial);
        post.position.set(startX + i * step, 0.45, z);
        railGroup.add(post);
      }
      scene.add(railGroup);
    };

    buildBalustrade(-8, -2.8, -1.2);
    buildBalustrade(2.8, 8, -1.2);

    // D. Olive Trees in Pots
    const buildOliveTree = (x, z) => {
      const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.3, 0.6, 24), potMaterial);
      pot.position.set(x, 0.3, z);
      pot.castShadow = true;
      scene.add(pot);

      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 1.2, 12), stoneMaterial);
      trunk.position.set(x, 1.0, z);
      scene.add(trunk);

      const foliage = new THREE.Mesh(new THREE.DodecahedronGeometry(0.7, 2), leafMaterial);
      foliage.position.set(x, 1.8, z);
      foliage.castShadow = true;
      scene.add(foliage);
    };

    buildOliveTree(-4.2, 0.5);
    buildOliveTree(4.2, 0.5);

    // E. Central Pedestal with JUSTITIA / EQUITY engraving
    const pedestalGroup = new THREE.Group();

    const pedBase = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.25, 1.6), stoneMaterial);
    pedBase.position.set(0, 0.125, 0.2);
    pedBase.receiveShadow = true;
    pedestalGroup.add(pedBase);

    const pedMid = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.7, 1.3), stoneMaterial);
    pedMid.position.set(0, 0.6, 0.2);
    pedMid.castShadow = true;
    pedestalGroup.add(pedMid);

    const pedTop = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.15, 1.4), stoneMaterial);
    pedTop.position.set(0, 1.025, 0.2);
    pedestalGroup.add(pedTop);

    scene.add(pedestalGroup);

    // F. Lady Justice Statue (Justitia Assembly)
    const statueGroup = new THREE.Group();
    statueGroup.position.set(0, 1.1, 0.2);

    // Torso / Dress Body
    const bodyGeo = new THREE.CylinderGeometry(0.28, 0.42, 1.6, 32);
    const bodyMesh = new THREE.Mesh(bodyGeo, bronzeStatueMaterial);
    bodyMesh.position.y = 0.8;
    bodyMesh.castShadow = true;
    statueGroup.add(bodyMesh);

    // Head with Blindfold
    const headGeo = new THREE.SphereGeometry(0.18, 24, 24);
    const headMesh = new THREE.Mesh(headGeo, bronzeStatueMaterial);
    headMesh.position.y = 1.75;
    statueGroup.add(headMesh);

    // Right Arm holding Sword
    const armRight = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.7, 16), bronzeStatueMaterial);
    armRight.position.set(-0.35, 1.4, 0.1);
    armRight.rotation.z = Math.PI * 0.15;
    statueGroup.add(armRight);

    // Sword
    const swordBlade = new THREE.Mesh(new THREE.BoxGeometry(0.04, 1.2, 0.02), goldChainMaterial);
    swordBlade.position.set(-0.52, 0.8, 0.2);
    swordBlade.rotation.z = Math.PI * 0.08;
    statueGroup.add(swordBlade);

    // Left Arm Raised holding Scales
    const armLeft = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.8, 16), bronzeStatueMaterial);
    armLeft.position.set(0.4, 1.7, 0);
    armLeft.rotation.z = -Math.PI * 0.3;
    statueGroup.add(armLeft);

    // 3D Scales of Justice Assembly held by left hand
    const scalesAssembly = new THREE.Group();
    scalesAssembly.position.set(0.75, 2.05, 0);

    // Fulcrum hook & Beam
    const beam = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.05, 0.05), goldChainMaterial);
    scalesAssembly.add(beam);

    // Left & Right Scale Pans
    const panLeft = new THREE.Group();
    const panRight = new THREE.Group();
    panLeft.position.set(-0.7, 0, 0);
    panRight.position.set(0.7, 0, 0);

    const attachPan = (group) => {
      const chainGeo = new THREE.CylinderGeometry(0.01, 0.01, 0.7, 8);
      for (let i = 0; i < 3; i++) {
        const ang = (i * Math.PI * 2) / 3;
        const chain = new THREE.Mesh(chainGeo, goldChainMaterial);
        chain.position.set(Math.cos(ang) * 0.2, -0.35, Math.sin(ang) * 0.2);
        chain.rotation.z = Math.cos(ang) * -0.2;
        group.add(chain);
      }
      const bowl = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.08, 0.1, 24), goldChainMaterial);
      bowl.position.y = -0.7;
      group.add(bowl);
    };

    attachPan(panLeft);
    attachPan(panRight);

    scalesAssembly.add(panLeft);
    scalesAssembly.add(panRight);

    statueGroup.add(scalesAssembly);
    scene.add(statueGroup);

    // Sun Ray / Light dust particles
    const particleCount = 80;
    const particlesGeo = new THREE.BufferGeometry();
    const posArray = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      posArray[i] = (Math.random() - 0.5) * 8;
      posArray[i + 1] = Math.random() * 5;
      posArray[i + 2] = (Math.random() - 0.5) * 6;
    }

    particlesGeo.setAttribute("position", new THREE.BufferAttribute(posArray, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0xfff5cf,
      size: 0.035,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
    });
    const dustParticles = new THREE.Points(particlesGeo, particleMat);
    scene.add(dustParticles);

    // 7. Interactive Parallax & Animation Loop
    let targetX = 0;
    let targetY = 0;

    const handleMouseMove = (e) => {
      if (!interactive || prefersReducedMotion) return;
      const x = (e.clientX / window.innerWidth) - 0.5;
      const y = (e.clientY / window.innerHeight) - 0.5;

      targetX = x * 0.4;
      targetY = y * 0.2;
    };

    if (interactive) window.addEventListener("mousemove", handleMouseMove);

    if (!prefersReducedMotion) {
      gsap.from(camera.position, {
        z: 8.5,
        duration: 2.4,
        ease: "power3.out",
      });
      gsap.from(statueGroup.rotation, {
        y: Math.PI * 0.25,
        duration: 2.8,
        ease: "power2.out",
      });
    }

    const clock = new THREE.Clock();

    const animate = () => {
      animFrameId.current = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      if (!prefersReducedMotion) {
        // Camera smooth parallax
        camera.position.x += (targetX - camera.position.x) * 0.04;
        camera.position.y += (1.6 - targetY - camera.position.y) * 0.04;
        camera.lookAt(0, 1.6, 0);

        // Gentle scale sway
        beam.rotation.z = Math.sin(elapsed * 1.4) * 0.04;
        panLeft.position.y = Math.sin(elapsed * 1.4) * 0.04;
        panRight.position.y = -Math.sin(elapsed * 1.4) * 0.04;

        // Dust float
        dustParticles.rotation.y = elapsed * 0.02;
      }

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth || window.innerWidth;
      const h = container.clientHeight || window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      if (animFrameId.current) cancelAnimationFrame(animFrameId.current);
      if (interactive) window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", handleResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [interactive]);

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full pointer-events-none select-none ${className}`}
      aria-hidden="true"
    />
  );
}
