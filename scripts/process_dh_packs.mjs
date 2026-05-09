/**
 * Process extracted Daggerheart packs into structured compendium JSON
 * for the charbuilder / compendium system.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { join, resolve } from "path";

const inputDir = resolve("backend/app/systems/daggerheart/default_packs");
const outputDir = resolve("backend/app/systems/daggerheart/default_packs/processed");
mkdirSync(outputDir, { recursive: true });

function loadPack(name) {
  const f = join(inputDir, `${name}.json`);
  if (!existsSync(f)) return [];
  return JSON.parse(readFileSync(f, "utf8"));
}

function isFolder(entry) {
  return !entry.system && entry.sorting !== undefined && !entry.img;
}

function stripHtml(html) {
  if (!html) return "";
  return html.replace(/<[^>]*>/g, "").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").trim();
}

// --- Classes ---
const rawClasses = loadPack("classes").filter(e => !isFolder(e) && e.type === "class");
const classes = rawClasses.map(c => ({
  slug: c.name.toLowerCase().replace(/\s+/g, "-"),
  name: c.name,
  fvtt_id: c._id,
  img: c.img || "",
  description: stripHtml(c.system?.description || ""),
  base_hp: c.system?.hitPoints?.base ?? 6,
  base_evasion: c.system?.evasion?.base ?? 8,
  base_stress: c.system?.stressMax ?? 6,
  domains: (c.system?.domains || []),
  spellcasting_trait: c.system?.spellcastingTrait || null,
}));
console.log(`Classes: ${classes.length}`);

// --- Subclasses ---
const rawSubs = loadPack("subclasses").filter(e => !isFolder(e));
const subclasses = rawSubs.filter(e => e.type === "subclass").map(s => ({
  slug: s.name.toLowerCase().replace(/\s+/g, "-"),
  name: s.name,
  fvtt_id: s._id,
  img: s.img || "",
  description: stripHtml(s.system?.description || ""),
  spellcasting_trait: s.system?.spellcastingTrait || null,
  linked_class: s.system?.linkedClass || null,
}));
const subFeatures = rawSubs.filter(e => e.type === "feature").map(f => ({
  slug: f.name.toLowerCase().replace(/\s+/g, "-"),
  name: f.name,
  fvtt_id: f._id,
  type: "subclass_feature",
  img: f.img || "",
  description: stripHtml(f.system?.description || ""),
}));
console.log(`Subclasses: ${subclasses.length}, Sub-Features: ${subFeatures.length}`);

// --- Domains (domain cards) ---
const rawDomains = loadPack("domains").filter(e => !isFolder(e));
const domainCards = rawDomains.filter(e => e.type === "domainCard").map(d => ({
  slug: d.name.toLowerCase().replace(/\s+/g, "-"),
  name: d.name,
  fvtt_id: d._id,
  img: d.img || "",
  description: stripHtml(d.system?.description || ""),
  domain: d.system?.domain || "",
  level: d.system?.level ?? 1,
  recall_cost: d.system?.recallCost ?? 0,
  card_type: d.system?.type || "",
}));
console.log(`Domain Cards: ${domainCards.length}`);

// --- Ancestries ---
const rawAncs = loadPack("ancestries").filter(e => !isFolder(e));
const ancestries = rawAncs.filter(e => e.type === "ancestry").map(a => ({
  slug: a.name.toLowerCase().replace(/\s+/g, "-"),
  name: a.name,
  fvtt_id: a._id,
  img: a.img || "",
  description: stripHtml(a.system?.description || ""),
}));
const ancestryFeatures = rawAncs.filter(e => e.type === "feature").map(f => ({
  slug: f.name.toLowerCase().replace(/\s+/g, "-"),
  name: f.name,
  fvtt_id: f._id,
  type: "ancestry_feature",
  img: f.img || "",
  description: stripHtml(f.system?.description || ""),
}));
console.log(`Ancestries: ${ancestries.length}, Ancestry Features: ${ancestryFeatures.length}`);

// --- Communities ---
const rawComs = loadPack("communities").filter(e => !isFolder(e));
const communities = rawComs.filter(e => e.type === "community").map(c => ({
  slug: c.name.toLowerCase().replace(/\s+/g, "-"),
  name: c.name,
  fvtt_id: c._id,
  img: c.img || "",
  description: stripHtml(c.system?.description || ""),
}));
console.log(`Communities: ${communities.length}`);

// --- Weapons ---
const rawWeapons = loadPack("items_weapons").filter(e => !isFolder(e) && e.type === "weapon");
const weapons = rawWeapons.map(w => ({
  slug: w.name.toLowerCase().replace(/\s+/g, "-"),
  name: w.name,
  fvtt_id: w._id,
  img: w.img || "",
  description: stripHtml(w.system?.description || ""),
  tier: w.system?.tier ?? 1,
  burden: w.system?.burden ?? 1,
  damage_die: w.system?.attack?.damageDie || "",
  damage_type: w.system?.attack?.type || "",
  range: w.system?.attack?.range || "",
}));
console.log(`Weapons: ${weapons.length}`);

// --- Armors ---
const rawArmors = loadPack("items_armors").filter(e => !isFolder(e) && e.type === "armor");
const armors = rawArmors.map(a => ({
  slug: a.name.toLowerCase().replace(/\s+/g, "-"),
  name: a.name,
  fvtt_id: a._id,
  img: a.img || "",
  description: stripHtml(a.system?.description || ""),
  tier: a.system?.tier ?? 1,
  base_score: a.system?.baseScore ?? 0,
}));
console.log(`Armors: ${armors.length}`);

// --- Consumables ---
const rawCons = loadPack("items_consumables").filter(e => !isFolder(e) && e.type === "consumable");
const consumables = rawCons.map(c => ({
  slug: c.name.toLowerCase().replace(/\s+/g, "-"),
  name: c.name,
  fvtt_id: c._id,
  img: c.img || "",
  description: stripHtml(c.system?.description || ""),
}));
console.log(`Consumables: ${consumables.length}`);

// --- Loot ---
const rawLoot = loadPack("items_loot").filter(e => !isFolder(e) && e.type === "loot");
const loot = rawLoot.map(l => ({
  slug: l.name.toLowerCase().replace(/\s+/g, "-"),
  name: l.name,
  fvtt_id: l._id,
  img: l.img || "",
  description: stripHtml(l.system?.description || ""),
}));
console.log(`Loot: ${loot.length}`);

// --- Beastforms ---
const rawBeast = loadPack("beastforms").filter(e => !isFolder(e) && e.type === "beastform");
const beastforms = rawBeast.map(b => ({
  slug: b.name.toLowerCase().replace(/\s+/g, "-"),
  name: b.name,
  fvtt_id: b._id,
  img: b.img || "",
  tier: b.system?.tier ?? 1,
  main_trait: b.system?.mainTrait || "",
}));
console.log(`Beastforms: ${beastforms.length}`);

// --- Write processed files ---
const packs = {
  classes,
  subclasses,
  subclass_features: subFeatures,
  domain_cards: domainCards,
  ancestries,
  ancestry_features: ancestryFeatures,
  communities,
  weapons,
  armors,
  consumables,
  loot,
  beastforms,
};

for (const [name, data] of Object.entries(packs)) {
  writeFileSync(join(outputDir, `${name}.json`), JSON.stringify(data, null, 2), "utf8");
}

// Write combined index
writeFileSync(join(outputDir, "_index.json"), JSON.stringify(
  Object.fromEntries(Object.entries(packs).map(([k, v]) => [k, v.length])),
  null, 2
), "utf8");

console.log("\nProcessed packs written to:", outputDir);
