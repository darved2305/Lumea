/**
 * TwinViewer – 3D digital-twin body with clickable organ hotspots.
 *
 * Lazy-loaded via React.lazy in the page to keep initial bundle small.
 * Uses @react-three/fiber + drei.  All styling uses the site's sage-green accent.
 */

import React, { useRef, useState, useCallback, Suspense, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Html, Environment, Float } from '@react-three/drei';
import * as THREE from 'three';

// ---------- Types ----------

export interface OrganHotspot {
  id: string;
  label: string;
  position: [number, number, number];
  color: string;
}

interface TwinViewerProps {
  selectedOrgan: string | null;
  onSelectOrgan: (id: string) => void;
  organScores?: Record<string, { score: number; status: string }>;
}

// ---------- Default hotspots (positioned on abstract torso) ----------

const DEFAULT_HOTSPOTS: OrganHotspot[] = [
  { id: 'brain',  label: 'Brain',  position: [0, 2.6, 0.3],   color: '#8B7EC8' },
  { id: 'heart',  label: 'Heart',  position: [0.3, 1.0, 0.5], color: '#D4645C' },
  { id: 'lungs',  label: 'Lungs',  position: [-0.3, 1.2, 0.4], color: '#6BAEDB' },
  { id: 'liver',  label: 'Liver',  position: [0.5, 0.3, 0.4], color: '#C4855C' },
  { id: 'kidney', label: 'Kidney', position: [-0.4, 0.0, 0.3], color: '#7AA874' },
  { id: 'blood',  label: 'Blood',  position: [0.0, 0.6, 0.6], color: '#c9525e' },
];

// ---------- Sage-green accent from Lumea tokens ----------
const SAGE = '#6b9175';
const SAGE_LIGHT = '#8fb199';

// ---------- Human body mesh (stylised capsule torso + head) ----------

function HumanBody() {
  const meshRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.15) * 0.08;
    }
  });

  return (
    <group ref={meshRef}>
      {/* Torso */}
      <mesh position={[0, 0.5, 0]}>
        <capsuleGeometry args={[0.55, 1.6, 16, 32]} />
        <meshStandardMaterial
          color="#e8ddd0"
          transparent
          opacity={0.35}
          roughness={0.6}
          metalness={0.1}
        />
      </mesh>
      {/* Head */}
      <mesh position={[0, 2.3, 0]}>
        <sphereGeometry args={[0.45, 32, 32]} />
        <meshStandardMaterial
          color="#e8ddd0"
          transparent
          opacity={0.35}
          roughness={0.6}
          metalness={0.1}
        />
      </mesh>
      {/* Neck */}
      <mesh position={[0, 1.7, 0]}>
        <cylinderGeometry args={[0.18, 0.22, 0.4, 16]} />
        <meshStandardMaterial
          color="#e8ddd0"
          transparent
          opacity={0.3}
          roughness={0.6}
          metalness={0.1}
        />
      </mesh>
      {/* Spine line */}
      <mesh position={[0, 0.5, -0.15]}>
        <cylinderGeometry args={[0.04, 0.04, 2.0, 8]} />
        <meshStandardMaterial color={SAGE} transparent opacity={0.2} />
      </mesh>
    </group>
  );
}

// ---------- Organ orb ----------

interface OrganOrbProps {
  hotspot: OrganHotspot;
  selected: boolean;
  onSelect: () => void;
  score?: number;
  status?: string;
}

function OrganOrb({ hotspot, selected, onSelect, score, status }: OrganOrbProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const glowColor = useMemo(() => {
    if (!status) return SAGE;
    if (status === 'Healthy') return '#6b9175';
    if (status === 'Watch') return '#d4a843';
    return '#c4645c';
  }, [status]);

  useFrame((state) => {
    if (meshRef.current) {
      const scale = selected
        ? 1.35 + Math.sin(state.clock.elapsedTime * 2) * 0.08
        : hovered
          ? 1.15
          : 1.0;
      meshRef.current.scale.setScalar(scale);
    }
  });

  return (
    <Float speed={1.5} rotationIntensity={0} floatIntensity={selected ? 0.3 : 0.1}>
      <group position={hotspot.position}>
        <mesh
          ref={meshRef}
          onClick={(e) => { e.stopPropagation(); onSelect(); }}
          onPointerOver={() => setHovered(true)}
          onPointerOut={() => setHovered(false)}
        >
          <sphereGeometry args={[0.18, 32, 32]} />
          <meshStandardMaterial
            color={selected ? glowColor : hotspot.color}
            emissive={selected || hovered ? glowColor : hotspot.color}
            emissiveIntensity={selected ? 0.8 : hovered ? 0.4 : 0.15}
            transparent
            opacity={selected ? 0.95 : 0.75}
            roughness={0.3}
            metalness={0.2}
          />
        </mesh>

        {/* Selection ring */}
        {selected && (
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.26, 0.3, 32]} />
            <meshBasicMaterial color={glowColor} transparent opacity={0.5} side={THREE.DoubleSide} />
          </mesh>
        )}

        {/* Label */}
        <Html
          position={[0, 0.35, 0]}
          center
          distanceFactor={6}
          style={{ pointerEvents: 'none', userSelect: 'none' }}
        >
          <div style={{
            background: selected ? 'rgba(107,145,117,0.95)' : 'rgba(245,240,232,0.92)',
            color: selected ? '#fff' : '#2d3e2f',
            padding: '3px 10px',
            borderRadius: '12px',
            fontSize: '11px',
            fontWeight: 600,
            fontFamily: '"DM Sans", sans-serif',
            whiteSpace: 'nowrap',
            border: `1px solid ${selected ? SAGE : '#d5cfc5'}`,
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
            transition: 'all 0.3s ease',
          }}>
            {hotspot.label}
            {score != null && (
              <span style={{ marginLeft: 6, opacity: 0.85 }}>
                {Math.round(score)}%
              </span>
            )}
          </div>
        </Html>
      </group>
    </Float>
  );
}

// ---------- Camera controller (smooth tween to organ) ----------

function CameraController({ target }: { target: [number, number, number] | null }) {
  const { camera } = useThree();
  const targetVec = useRef(new THREE.Vector3(0, 1.2, 4));

  useFrame(() => {
    if (target) {
      targetVec.current.set(target[0] * 0.3, target[1] * 0.6 + 1.0, 3.5);
    } else {
      targetVec.current.set(0, 1.2, 4);
    }
    camera.position.lerp(targetVec.current, 0.03);
    camera.lookAt(0, 1.0, 0);
  });

  return null;
}

// ---------- VR mode check ----------

function useWebXRSupported() {
  const [supported, setSupported] = useState<boolean | null>(null);
  React.useEffect(() => {
    if (navigator.xr) {
      navigator.xr.isSessionSupported('immersive-vr').then(setSupported).catch(() => setSupported(false));
    } else {
      setSupported(false);
    }
  }, []);
  return supported;
}

// ---------- Main component ----------

const TwinViewer: React.FC<TwinViewerProps> = ({ selectedOrgan, onSelectOrgan, organScores }) => {
  const vrSupported = useWebXRSupported();

  const selectedHotspot = DEFAULT_HOTSPOTS.find((h) => h.id === selectedOrgan);
  const cameraTarget = selectedHotspot ? selectedHotspot.position : null;

  const handleCanvasClick = useCallback(() => {
    // Clicking empty space deselects (handled by parent)
  }, []);

  return (
    <div className="twin-viewer-container">
      <Canvas
        camera={{ position: [0, 1.2, 4], fov: 45 }}
        onClick={handleCanvasClick}
        style={{ background: 'transparent' }}
        dpr={[1, 1.5]}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[3, 5, 3]} intensity={0.7} color="#f5f0e8" />
          <directionalLight position={[-2, 3, -2]} intensity={0.3} color={SAGE_LIGHT} />
          <pointLight position={[0, 1, 2]} intensity={0.3} color={SAGE_LIGHT} />

          <Environment preset="apartment" />

          <HumanBody />

          {DEFAULT_HOTSPOTS.map((hotspot) => (
            <OrganOrb
              key={hotspot.id}
              hotspot={hotspot}
              selected={selectedOrgan === hotspot.id}
              onSelect={() => onSelectOrgan(hotspot.id)}
              score={organScores?.[hotspot.id]?.score}
              status={organScores?.[hotspot.id]?.status}
            />
          ))}

          <CameraController target={cameraTarget} />
          <OrbitControls
            enablePan={false}
            enableZoom={true}
            minDistance={2.5}
            maxDistance={7}
            minPolarAngle={Math.PI / 6}
            maxPolarAngle={Math.PI / 1.5}
            autoRotate={!selectedOrgan}
            autoRotateSpeed={0.3}
          />
        </Suspense>
      </Canvas>

      {/* VR toggle */}
      <div className="twin-vr-badge">
        {vrSupported === true ? (
          <button
            className="dash-btn dash-btn-secondary twin-vr-btn"
            onClick={() => {/* TODO: enter XR session */}}
          >
            VR Mode
          </button>
        ) : (
          <span className="twin-vr-note">VR not available on this device</span>
        )}
      </div>
    </div>
  );
};

export default TwinViewer;
