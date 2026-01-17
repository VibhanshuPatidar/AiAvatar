import {
  CameraControls,
  ContactShadows,
  Environment,
  Text,
  Sky,
  useGLTF
} from "@react-three/drei";
import { Suspense, useEffect, useRef, useState } from "react";
import { useChat } from "../hooks/useChat";
import { Avatar } from "./Avatar";
import * as THREE from "three";



function EnvironmentScene({ url, onGroundDetected }) {
  const { scene } = useGLTF(url);

  useEffect(() => {
    scene.traverse((obj) => {
      if (obj.isMesh && obj.material) {
        obj.material.side = THREE.DoubleSide;
        obj.material.needsUpdate = true;
      }
    });

    // detect ground level of environment
    const box = new THREE.Box3().setFromObject(scene);
    onGroundDetected(box.min.y);  // pass lowest Y back up
  }, [scene, onGroundDetected]);

  return <primitive object={scene} scale={5} />;
}

const Dots = (props) => {
  const { loading } = useChat();
  const [loadingText, setLoadingText] = useState("");
  useEffect(() => {
    if (loading) {
      const interval = setInterval(() => {
        setLoadingText((loadingText) => {
          if (loadingText.length > 2) {
            return ".";
          }
          return loadingText + ".";
        });
      }, 800);
      return () => clearInterval(interval);
    } else {
      setLoadingText("");
    }
  }, [loading]);
  if (!loading) return null;
  return (
    <group {...props}>
      <Text fontSize={0.14} anchorX={"left"} anchorY={"bottom"}>
        {loadingText}
        <meshBasicMaterial attach="material" color="black" />
      </Text>
    </group>
  );
};

export const Experience = ({ selectedModel }) => {
  const cameraControls = useRef();
  const { cameraZoomed } = useChat();

  const [envGround, setEnvGround] = useState(0);

  useEffect(() => {
    cameraControls.current.setLookAt(-1, envGround + 1.5, 2, -1, envGround + 1.5, 0);
  }, [envGround]);

  return (
    <>
      <CameraControls ref={cameraControls} />

      {/* Lights */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={2} castShadow />

      {/* Environment light */}
      <Environment preset="city" />

      {/* <Suspense>
        <EnvironmentScene
          url="/textures/beautiful_city.glb"
          onGroundDetected={(y) => setEnvGround(y)}
        />
      </Suspense> */}

      {/* Avatar positioned automatically on ground */}
      <Suspense>
        <group position={[-1, envGround + 0.08, 0]} rotation={[0, 0, 0]}>
          <Avatar key={selectedModel} model={selectedModel} />
        </group>
        <Dots position={[-1.03, envGround + 1.85, 0]} />
      </Suspense>

      <ContactShadows opacity={0.7} />
    </>
  );
};