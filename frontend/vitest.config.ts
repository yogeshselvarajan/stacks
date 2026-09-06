import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Mirrors tsconfig.json's "@/*" -> "./*" path mapping (Next.js's own
    // build resolves this already; Vitest needs it spelled out
    // separately since it doesn't read tsconfig "paths" on its own).
    alias: {
      "@": fileURLToPath(new URL(".", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
  },
});
