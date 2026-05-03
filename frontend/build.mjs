/**
 * Writes public/index.html from template.html, replacing __API_BASE__.
 * Set API_BASE_URL for your Render backend (no trailing slash required).
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const base = (process.env.API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const tplPath = path.join(__dirname, "template.html");
const outDir = path.join(__dirname, "public");
const outPath = path.join(outDir, "index.html");

const tpl = fs.readFileSync(tplPath, "utf8");
if (!tpl.includes("__API_BASE__")) {
  console.error("template.html must contain __API_BASE__ placeholder");
  process.exit(1);
}

const html = tpl.replaceAll("__API_BASE__", base);
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(outPath, html, "utf8");
console.log("Built", outPath, "with API_BASE_URL =", base);
