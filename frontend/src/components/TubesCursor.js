import React, { useEffect } from 'react';
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';

const TubesCursor = () => {
  useEffect(() => {
    const canvas = document.getElementById('canvas');
    if (!canvas) return;

    // Use a black clear color because we will use CSS mix-blend-mode: screen
    // to composite the bloom effect perfectly over the HTML background gradient.
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: false });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 1); 

    const scene = new THREE.Scene();
    
    // Camera setup
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 40;

    // Configuration from "Neural Ribbon" Requirements
    const tubeColors = ['#a0feff', '#4afffe', '#bd10e0', '#7d00f5', '#00ff41'];
    const numTubes = 10; // Exactly 10 threads
    const numPoints = 40;
    const tubes = [];
    
    // Geometry & Material
    for (let i = 0; i < numTubes; i++) {
      const colorHex = tubeColors[i % tubeColors.length];
      const color = new THREE.Color(colorHex);
      
      // Initialize points slightly apart to prevent CatmullRomCurve3 NaN tangent crash
      const points = new Array(numPoints).fill(0).map((_, idx) => new THREE.Vector3(idx * 0.001, 0, 0));
      const curve = new THREE.CatmullRomCurve3(points);
      
      // extremely thin tubes (0.02 to 0.05)
      const geometry = new THREE.TubeGeometry(curve, 64, 0.03, 8, false);
      const material = new THREE.MeshPhysicalMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 1.0, // Reduced from 2.5
        metalness: 0.9,
        roughness: 0.1,
        transparent: true,
        opacity: 0.9,
      });
      
      const mesh = new THREE.Mesh(geometry, material);
      scene.add(mesh);
      
      tubes.push({ 
        mesh, 
        points, 
        curve, 
        offsetPhase: (i * Math.PI * 2) / numTubes,
        // Varying lerp factor for "liquid" fringe effect
        lerpFactor: 0.05 + (i * 0.015), 
        // Keep spread tight (30% smaller)
        spreadFactor: 0.3 + (i * 0.05) 
      });
    }

    // Lights
    const pointLight = new THREE.PointLight(0xffffff, 1, 100);
    scene.add(pointLight);
    scene.add(new THREE.AmbientLight(0xffffff, 0.2));

    // Post-Processing: UnrealBloomPass
    const renderScene = new RenderPass(scene, camera);
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(window.innerWidth, window.innerHeight), 
      0.5,   // strength (reduced from 1.5)
      0.5,   // radius
      0.1    // threshold
    );
    
    const composer = new EffectComposer(renderer);
    composer.addPass(renderScene);
    composer.addPass(bloomPass);

    // Mouse tracking
    const mouse = new THREE.Vector2(0, 0);
    const target = new THREE.Vector3(0, 0, 0);
    const raycaster = new THREE.Raycaster();
    const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
    let targetOpacity = 0.9; // Base target opacity

    const onMouseMove = (e) => {
      mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
      
      raycaster.setFromCamera(mouse, camera);
      raycaster.ray.intersectPlane(plane, target);

      // Hover interaction logic: fade out if hovering over interactive elements or cards
      const hoveredElement = document.elementFromPoint(e.clientX, e.clientY);
      if (hoveredElement) {
        // Check if the element matches common interactive elements or the glass cards
        const isInteractive = hoveredElement.closest('button, input, textarea, a, .glass-card, [role="button"], select');
        if (isInteractive) {
          targetOpacity = 0.0; // Hide
        } else {
          targetOpacity = 0.9; // Show
        }
      }
    };

    window.addEventListener('mousemove', onMouseMove);

    // Animation Loop
    let time = 0;
    let animationFrameId;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      // Pause rendering if the intro video is playing to free up GPU/CPU
      if (document.body.classList.contains("video-playing")) {
        return;
      }

      time += 0.03;

      // Update tubes
      tubes.forEach((tube) => {
        // Dynamic offset for interweaving
        const offset = new THREE.Vector3(
          Math.sin(time * 2 + tube.offsetPhase) * tube.spreadFactor,
          Math.cos(time * 2 + tube.offsetPhase) * tube.spreadFactor,
          Math.sin(time + tube.offsetPhase) * (tube.spreadFactor * 0.5)
        );
        
        // 1. Move the head (first point) towards the mouse target + offset
        tube.points[0].lerp(target.clone().add(offset), tube.lerpFactor);

        // 2. Momentum/inertia: other points follow the point ahead of them
        for (let i = 1; i < tube.points.length; i++) {
          tube.points[i].lerp(tube.points[i - 1], 0.3);
        }

        // Rebuild geometry
        tube.curve.points = tube.points;
        tube.mesh.geometry.dispose();
        tube.mesh.geometry = new THREE.TubeGeometry(tube.curve, 64, 0.03, 8, false);

        // Smoothly lerp material opacity based on hover state
        tube.mesh.material.opacity = THREE.MathUtils.lerp(tube.mesh.material.opacity, targetOpacity, 0.1);
      });

      // Point light follows the cursor
      pointLight.position.copy(target);
      pointLight.position.z += 5;

      composer.render(); // Render using the composer for post-processing
    };

    animate();

    // Resize handler
    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
      composer.setSize(window.innerWidth, window.innerHeight);
    };
    
    window.addEventListener('resize', onResize);

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', onResize);
      cancelAnimationFrame(animationFrameId);
      
      tubes.forEach(t => {
        t.mesh.geometry.dispose();
        t.mesh.material.dispose();
      });
      renderer.dispose();
      composer.dispose();
    };
  }, []);

  return (
    <canvas
      id="canvas"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 0,
        pointerEvents: 'none',
        // Using screen blend mode to composite the bloom glow over the CSS background perfectly!
        mixBlendMode: 'screen',
      }}
    />
  );
};

export default TubesCursor;
