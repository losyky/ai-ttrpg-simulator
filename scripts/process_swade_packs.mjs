/**
 * Process extracted SWADE packs into structured compendium JSON.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { join, resolve } from "path";

const inputDir = resolve("backend/app/systems/swade/default_packs");
const outputDir = resolve("backend/app/systems/swade/default_packs/processed");
mkdirSync(outputDir, { recursive: true });

function loadPack(name) {
  const f = join(inputDir, `${name}.json`);
  if (!existsSync(f)) return [];
  return JSON.parse(readFileSync(f, "utf8"));
}

function isFolder(entry) {
  return !entry.system && !entry.type;
}

function stripHtml(html) {
  if (!html) return "";
  return html.replace(/<[^>]*>/g, "").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").trim();
}

// --- Edges ---
const rawEdges = loadPack("edges").filter(e => !isFolder(e) && e.type === "edge");
const edges = rawEdges.map(e => ({
  slug: e.system?.swid || e.name.toLowerCase().replace(/\s+/g, "-"),
  name: e.name,
  name_cn: e.flags?.babele?.translated ? (e.flags?.babele?.originalName ? e.name : "") : "",
  fvtt_id: e._id,
  description: stripHtml(e.system?.description || ""),
  category: e.system?.category || "",
  rank: e.system?.requirements?.find(r => r.type === "rank")?.value ?? 0,
  is_arcane: e.system?.isArcaneBackground || false,
}));
console.log(`Edges: ${edges.length}`);

// --- Hindrances ---
const rawHind = loadPack("hindrances").filter(e => !isFolder(e) && e.type === "hindrance");
const hindrances = rawHind.map(h => ({
  slug: h.system?.swid || h.name.toLowerCase().replace(/\s+/g, "-"),
  name: h.name,
  name_cn: "",
  fvtt_id: h._id,
  description: stripHtml(h.system?.description || ""),
  major: h.system?.major || false,
}));
console.log(`Hindrances: ${hindrances.length}`);

// --- Powers ---
const rawPowers = loadPack("powers").filter(e => !isFolder(e) && e.type === "power");
const powers = rawPowers.map(p => ({
  slug: p.system?.swid || p.name.toLowerCase().replace(/\s+/g, "-"),
  name: p.name,
  name_cn: "",
  fvtt_id: p._id,
  description: stripHtml(p.system?.description || ""),
  rank: p.system?.rank || "novice",
  pp: p.system?.pp || 0,
  range: p.system?.range || "",
  duration: p.system?.duration || "",
}));
console.log(`Powers: ${powers.length}`);

// --- Write ---
const packs = { edges, hindrances, powers };
for (const [name, data] of Object.entries(packs)) {
  writeFileSync(join(outputDir, `${name}.json`), JSON.stringify(data, null, 2), "utf8");
}
writeFileSync(join(outputDir, "_index.json"), JSON.stringify(
  Object.fromEntries(Object.entries(packs).map(([k, v]) => [k, v.length])),
  null, 2
), "utf8");

console.log("\nProcessed packs written to:", outputDir);
