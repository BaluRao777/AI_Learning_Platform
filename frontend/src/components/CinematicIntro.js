import React, { useRef, useState, useMemo, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  Text3D,
  Center,
  Float,
  PerspectiveCamera,
  Environment,
  MeshWobbleMaterial,
  Sparkles,
  Bloom,
  EffectComposer,
} from "@react-three/drei";
import * as THREE from "three";
import { gsap } from "gsap";

// --- Constants & Config ---
const FONT_URL = "https://threejs.org/examples/fonts/helvetiker_bold.typeface.json";
export const HERO_WORDS = "Master Complex Topics with AI-Powered Clarity";

// --- Sub-Components ---

/**
 * Background glowing concentric rings
 */
const GlowingRings = ({ opacity = 1 }) => {
  const ringsRef = useRef();
  
  useFrame((state) => {
    if (ringsRef.current) {
      ringsRef.current.rotation.z += 0.005;
      ringsRef.current.children.forEach((ring, i) => {
        ring.rotation.x = Math.sin(state.clock.elapsedTime * 0.5 + i) * 0.2;
      });
    }
  });

  return (
    <group ref={ringsRef}>
      {[...Array(8)].map((_, i) => (
        <mesh key={i} rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[i * 2 + 5, i * 2 + 5.1, 64]} />
          <meshBasicMaterial 
            color={new THREE.Color().setHSL(i / 8, 0.8, 0.5)} 
            transparent 
            opacity={opacity * (1 - i / 8) * 0.5} 
            side={THREE.DoubleSide}
          />
        </mesh>
      ))}
    </group>
  );
};

/**
 * Mock Book Component
 * Structured for future GLB swap.
 */
const Book = ({ progress, pageFlipSpeed, opacity = 1, explosionProgress = 0 }) => {
  const group = useRef();
  const coverRef = useRef();
  const leftPageRef = useRef();
  const rightPageRef = useRef();

  // Basic geometric mock of a book
  return (
    <group ref={group} scale={1 - explosionProgress}>
      {/* Back Cover */}
      <mesh position={[0, 0, -0.1]}>
        <boxGeometry args={[4.2, 6, 0.2]} />
        <meshStandardMaterial color="#1a1a1a" roughness={0.8} transparent opacity={opacity} />
      </mesh>
      
      {/* Left Page (Static after opening) */}
      <mesh position={[-2, 0, 0]} rotation={[0, -progress * Math.PI, 0]}>
        <boxGeometry args={[2, 5.8, 0.05]} />
        <meshStandardMaterial color="#f5f5f5" emissive="#3b82f6" emissiveIntensity={0.2} transparent opacity={opacity} />
      </mesh>

      {/* Right Page (Static) */}
      <mesh position={[2, 0, 0]}>
        <boxGeometry args={[2, 5.8, 0.05]} />
        <meshStandardMaterial color="#f5f5f5" emissive="#3b82f6" emissiveIntensity={0.2} transparent opacity={opacity} />
      </mesh>

      {/* Magical Glow from Spine */}
      <pointLight position={[0, 0, 0.5]} intensity={2 * opacity} color="#8b5cf6" distance={10} />
      <Sparkles count={50} scale={4} size={2} speed={0.4} opacity={opacity * 0.5} />
    </group>
  );
};

/**
 * Exploding Words Component
 */
const ExplodingWords = ({ text, active, onCompleteExplosion }) => {
  const words = useMemo(() => text.split(" "), [text]);
  const groupRef = useRef();
  const [phase, setPhase] = useState("idle"); // idle -> floating -> spinning -> condensing -> explosion

  useEffect(() => {
    if (active && phase === "idle") {
      setPhase("floating");
      const tl = gsap.timeline({
        onComplete: () => onCompleteExplosion()
      });

      // 1. Detach and Float (Zero-G)
      tl.to(groupRef.current.position, { y: 2, duration: 3, ease: "power1.inOut" });
      
      // 2. Rapid Spin
      tl.to(groupRef.current.rotation, { y: Math.PI * 10, duration: 1.5, ease: "power2.in" }, "+=0.5");
      
      // 3. Condense into ball
      tl.to(groupRef.current.children.map(c => c.position), { 
        x: 0, y: 0, z: 0, 
        duration: 0.8, 
        ease: "back.in(2)",
        stagger: 0.02 
      }, "-=0.5");

      // 4. Scale down group as it condenses
      tl.to(groupRef.current.scale, { x: 0.1, y: 0.1, z: 0.1, duration: 0.5 }, "-=0.3");
    }
  }, [active, phase, onCompleteExplosion]);

  if (!active) return null;

  return (
    <group ref={groupRef}>
      {words.map((word, i) => (
        <Center key={i} position={[(i - words.length/2) * 1.2, Math.sin(i) * 0.5, 0]}>
          <Text3D font={FONT_URL} size={0.5} height={0.1} curveSegments={12}>
            {word}
            <MeshWobbleMaterial color="#c4b5fd" factor={0.1} speed={2} factor={0.2} />
          </Text3D>
        </Center>
      ))}
    </group>
  );
};

// --- Main Cinematic Scene ---

const Scene = ({ heroText, onComplete }) => {
  const { camera } = useThree();
  const [state, setState] = useState("falling"); // falling -> opening -> exploding -> finished
  const [ringOpacity, setRingOpacity] = useState(1);
  const [bookProgress, setBookProgress] = useState(0);
  const [bookOpacity, setBookOpacity] = useState(1);
  const [flashOpacity, setFlashOpacity] = useState(0);

  const bookRef = useRef();
  const explosionProgress = useRef(0);

  useEffect(() => {
    // Initial Camera: Top-down
    camera.position.set(0, 50, 0);
    camera.lookAt(0, 0, 0);

    const tl = gsap.timeline();

    // SCENE 1: The Falling Book
    tl.to(camera.position, {
      y: 0, z: 15,
      duration: 4,
      ease: "power2.inOut",
      onUpdate: () => camera.lookAt(0, 0, 0)
    });

    tl.to(setRingOpacity, { value: 0, duration: 2, ease: "power2.out" }, "-=2");

    // SCENE 2: The Opening Pages (Accelerating)
    tl.to({}, { 
      duration: 2,
      onStart: () => setState("opening"),
      onUpdate: function() {
        const p = this.progress();
        setBookProgress(Math.pow(p, 2)); // Quadratic acceleration
      }
    });

    // SCENE 3: The Word Explosion
    tl.to({}, {
      duration: 0.5,
      onStart: () => setState("exploding")
    });

    // Book fades out during explosion
    tl.to(setBookOpacity, { value: 0, duration: 1 }, "+=1");

  }, [camera]);

  const handleExplosionBlast = () => {
    const tl = gsap.timeline({
      onComplete: () => {
        // Signal parent to unmount
        setTimeout(onComplete, 500);
      }
    });

    // White Flash
    tl.to(setFlashOpacity, { value: 1, duration: 0.1 });
    tl.to(setFlashOpacity, { value: 0, duration: 0.8 });
  };

  return (
    <>
      <color attach="background" args={["#000000"]} />
      <Environment preset="city" />
      <ambientLight intensity={0.2} />
      
      <GlowingRings opacity={ringOpacity} />
      
      <group ref={bookRef} position={[0, state === "falling" ? 10 : 0, 0]}>
        <Book 
          progress={bookProgress} 
          opacity={bookOpacity} 
          explosionProgress={state === "exploding" ? 0.5 : 0} 
        />
      </group>

      <ExplodingWords 
        text={heroText} 
        active={state === "exploding"} 
        onCompleteExplosion={handleExplosionBlast}
      />

      {/* Full Screen Flash Overlay (Handled in HTML layer usually, or as a big plane) */}
      <mesh position={[0, 0, 5]} scale={[100, 100, 1]}>
        <planeGeometry />
        <meshBasicMaterial color="white" transparent opacity={flashOpacity} depthTest={false} />
      </mesh>
    </>
  );
};

export default function CinematicIntro({ heroText = HERO_WORDS, onComplete }) {
  useEffect(() => {
    // Add class to body to signal WebGL is running (useful for CSS cursor logic etc)
    document.body.classList.add("video-playing");
    return () => document.body.classList.remove("video-playing");
  }, []);

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 10000, background: "#000" }}>
      <Canvas shadows gl={{ antialias: true }}>
        <Scene heroText={heroText} onComplete={onComplete} />
      </Canvas>
    </div>
  );
}
