import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
  build: {
    outDir: "../src/threadstudio/ui/web",
    emptyOutDir: true,
  },
});
