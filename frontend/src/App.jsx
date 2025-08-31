import { Loader } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Leva } from "leva";
import { Experience } from "./components/Experience";
import { UI } from "./components/UI";

import { useState, useEffect } from "react";
import { listAvatarModels } from "./utils";

function App() {
  const [avatarModels, setAvatarModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("robin.glb");

  useEffect(() => {
    async function fetchModels() {
      const models = await listAvatarModels();
      setAvatarModels(models);
      // If selectedModel is not in the new models list, set to default or first
      if (!models.includes(selectedModel)) {
        if (models.includes("robin.glb")) {
          setSelectedModel("robin.glb");
        } else if (models.length > 0) {
          setSelectedModel(models[0]);
        }
      }
    }
    fetchModels();
  }, [selectedModel]);
  return (
    <>
      <Loader />
      <Leva hidden/>
      <UI
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
        avatarModels={avatarModels}
      />
      <Canvas shadows camera={{ position: [0, 0, 1], fov: 30 }}>
        <Experience selectedModel={selectedModel} />
      </Canvas>
    </>
  );
}

export default App;
