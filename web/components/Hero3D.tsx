"use client";
// Cinematic 3D "memory graph" for the landing hero: topics (spheres, coloured by mastery), misconceptions
// (purple octahedra), the student at the centre, thin links and a soft particle field. ~60 meshes total.
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";

const COLORS = { saffron: "#FF9A3D", green: "#3DD68C", amber: "#F5A524", red: "#E5484D", misc: "#B794F6" };
const TOPIC_COLORS = [COLORS.saffron, COLORS.green, COLORS.amber, COLORS.red, COLORS.green, COLORS.saffron];

type Node = { pos: THREE.Vector3; color: string; size: number; kind: "topic" | "misc"; phase: number };

function fibonacciSphere(n: number, r: number): THREE.Vector3[] {
  const pts: THREE.Vector3[] = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2;
    const rad = Math.sqrt(1 - y * y);
    const th = golden * i;
    pts.push(new THREE.Vector3(Math.cos(th) * rad * r, y * r * 0.82, Math.sin(th) * rad * r));
  }
  return pts;
}

function useGraph() {
  return useMemo(() => {
    const topicPts = fibonacciSphere(18, 3.1);
    const nodes: Node[] = topicPts.map((pos, i) => ({
      pos, color: TOPIC_COLORS[i % TOPIC_COLORS.length], size: 0.12 + ((i * 37) % 10) / 70, kind: "topic", phase: i * 0.7,
    }));
    // misconceptions sit just outside a topic they "affect"
    [1, 4, 7, 10, 13, 16].forEach((ti, k) => {
      const p = topicPts[ti].clone().multiplyScalar(1.28).add(new THREE.Vector3(0.25 * (k % 2 ? 1 : -1), 0.2, 0));
      nodes.push({ pos: p, color: COLORS.misc, size: 0.16, kind: "misc", phase: k * 1.3 });
    });
    // links: student -> every topic, topic -> next topic (prerequisites), misconception -> its topic
    const segs: number[] = [];
    const push = (a: THREE.Vector3, b: THREE.Vector3) => segs.push(a.x, a.y, a.z, b.x, b.y, b.z);
    topicPts.forEach((p, i) => {
      push(new THREE.Vector3(0, 0, 0), p);
      if (i % 3 !== 2) push(p, topicPts[(i + 1) % topicPts.length]);
    });
    [1, 4, 7, 10, 13, 16].forEach((ti, k) => push(topicPts[ti], nodes[18 + k].pos));
    return { nodes, segs: new Float32Array(segs) };
  }, []);
}

function Particles({ count = 700 }: { count?: number }) {
  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const arr = new Float32Array(count * 3);
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < count; i++) {
      const r = 4 + rnd() * 6, th = rnd() * Math.PI * 2, ph = Math.acos(2 * rnd() - 1);
      arr.set([r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph) * 0.6, r * Math.sin(ph) * Math.sin(th)], i * 3);
    }
    g.setAttribute("position", new THREE.BufferAttribute(arr, 3));
    return g;
  }, [count]);
  return (
    <points geometry={geo}>
      <pointsMaterial size={0.03} color="#FFD08A" transparent opacity={0.45} sizeAttenuation depthWrite={false} />
    </points>
  );
}

function Graph({ animate }: { animate: boolean }) {
  const group = useRef<THREE.Group>(null);
  const meshes = useRef<(THREE.Mesh | null)[]>([]);
  const halos = useRef<(THREE.Mesh | null)[]>([]);
  const { nodes, segs } = useGraph();
  const { pointer } = useThree();
  const lineGeo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(segs, 3));
    return g;
  }, [segs]);

  useFrame((state, dt) => {
    if (!animate || !group.current) return;
    const t = state.clock.elapsedTime;
    group.current.rotation.y += dt * 0.08;
    // gentle mouse parallax tilt
    group.current.rotation.x += ((pointer.y * 0.25) - group.current.rotation.x) * 0.04;
    group.current.rotation.z += ((-pointer.x * 0.12) - group.current.rotation.z) * 0.04;
    // one node "remembers" at a time: a saffron pulse travels round the graph
    const active = Math.floor(t / 1.6) % nodes.length;
    nodes.forEach((n, i) => {
      const m = meshes.current[i];
      if (!m) return;
      m.position.y = n.pos.y + Math.sin(t * 0.9 + n.phase) * 0.08;
      if (n.kind === "misc") m.rotation.set(t * 0.6 + n.phase, t * 0.4, 0);
      const h = halos.current[i];
      if (h) {
        h.position.copy(m.position);
        const k = i === active ? 1 + Math.sin(((t % 1.6) / 1.6) * Math.PI) * 1.4 : 1;
        h.scale.setScalar(k);
        (h.material as THREE.MeshBasicMaterial).opacity = i === active ? 0.35 : 0.12;
      }
    });
  });

  return (
    <group ref={group} rotation={[0.25, 0, 0]}>
      <lineSegments geometry={lineGeo}>
        <lineBasicMaterial color="#8B93A1" transparent opacity={0.22} />
      </lineSegments>
      {/* the student */}
      <mesh>
        <sphereGeometry args={[0.32, 32, 32]} />
        <meshStandardMaterial color="#07080A" emissive="#ffffff" emissiveIntensity={0.15} roughness={0.4} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.42, 0.018, 12, 64]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      {nodes.map((n, i) => (
        <group key={i}>
          <mesh ref={(el) => { meshes.current[i] = el; }} position={n.pos}>
            {n.kind === "misc" ? <octahedronGeometry args={[n.size, 0]} /> : <sphereGeometry args={[n.size, 24, 24]} />}
            <meshStandardMaterial color={n.color} emissive={n.color} emissiveIntensity={0.9} roughness={0.35} />
          </mesh>
          <mesh ref={(el) => { halos.current[i] = el; }} position={n.pos}>
            <sphereGeometry args={[n.size * 2.4, 16, 16]} />
            <meshBasicMaterial color={n.color} transparent opacity={0.12} depthWrite={false} blending={THREE.AdditiveBlending} />
          </mesh>
        </group>
      ))}
      <Particles />
    </group>
  );
}

export default function Hero3D() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const on = () => setReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return (
    <Canvas
      dpr={[1, 1.5]}
      camera={{ position: [0, 0.4, 11.5], fov: 42 }}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      frameloop={reduced ? "demand" : "always"}
      aria-hidden
    >
      <ambientLight intensity={0.35} />
      <pointLight position={[0, 0, 0]} intensity={18} distance={9} color="#FF9A3D" />
      <pointLight position={[6, 5, 6]} intensity={30} distance={20} color="#ffffff" />
      <Graph animate={!reduced} />
    </Canvas>
  );
}
