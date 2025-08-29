// utils.js
// Dynamically list all .glb avatar models in public/models (client-side)

export async function listAvatarModels() {
  // This will only work if you have a backend API or static file manifest
  // For static hosting, you may need to hardcode or generate this list at build time
  // Here, we use a static list as a fallback
  // Replace with API call if available
  return [
    "nerd.glb",
    "goth.glb",
    "robin.glb"
  ];
}
