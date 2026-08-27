/**
 * Vercel clones the monorepo root. If Root Directory is unset, Next.js is
 * under web/anpr-command-web and the deploy 404s. Copy the app to the
 * workspace root so `next build` can run. No-op if already in that folder.
 */
import { cpSync, existsSync, readdirSync } from "fs";
import { join } from "path";

const src = join(process.cwd(), "web", "anpr-command-web");
const marker = join(src, "package.json");

if (!existsSync(marker)) {
  console.log("vercel-flatten-web: already at Next.js root, skip");
  process.exit(0);
}

const skip = new Set(["node_modules", ".next", ".git"]);
for (const name of readdirSync(src)) {
  if (skip.has(name)) continue;
  cpSync(join(src, name), join(process.cwd(), name), { recursive: true, force: true });
}
console.log("vercel-flatten-web: copied web/anpr-command-web to repo root");
