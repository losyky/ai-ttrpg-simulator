/**
 * Extract FVTT LevelDB compendium packs to JSON files.
 *
 * Usage:
 *   node scripts/extract_fvtt_packs.mjs <system_path> <output_dir>
 *
 * Examples:
 *   node scripts/extract_fvtt_packs.mjs /path/to/daggerheart backend/app/systems/daggerheart/default_packs
 *   node scripts/extract_fvtt_packs.mjs /path/to/swade       backend/app/systems/swade/default_packs
 *   node scripts/extract_fvtt_packs.mjs /path/to/pf2e        extracted_packs
 */

import { ClassicLevel } from "classic-level";
import { readFileSync, mkdirSync, writeFileSync, readdirSync, existsSync, statSync } from "fs";
import { join, resolve, basename } from "path";

if (!process.argv[2]) {
  console.error("Usage: node scripts/extract_fvtt_packs.mjs <system_path> [output_dir]");
  console.error("  <system_path>  Path to the FVTT system directory (must contain packs/)");
  console.error("  [output_dir]   Output directory for extracted JSON (default: extracted_packs)");
  process.exit(1);
}

const systemPath = resolve(process.argv[2]);
const outputDir = resolve(process.argv[3] || "extracted_packs");

function isLevelDB(dir) {
  return existsSync(join(dir, "CURRENT"));
}

function findPackDirs(dir, results = []) {
  if (isLevelDB(dir)) {
    results.push(dir);
    return results;
  }
  try {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      if (statSync(full).isDirectory()) {
        findPackDirs(full, results);
      }
    }
  } catch { /* */ }
  return results;
}

async function extractPack(dbPath) {
  const db = new ClassicLevel(dbPath, { valueEncoding: "utf8" });
  const entries = [];
  try {
    for await (const [key, value] of db.iterator()) {
      try {
        const doc = JSON.parse(value);
        entries.push(doc);
      } catch {
        // skip non-JSON entries
      }
    }
  } finally {
    await db.close();
  }
  return entries;
}

async function main() {
  console.log(`System path: ${systemPath}`);
  console.log(`Output dir:  ${outputDir}`);

  // Read system.json for pack metadata
  const systemJsonPath = join(systemPath, "system.json");
  let packsMeta = [];
  if (existsSync(systemJsonPath)) {
    const sysJson = JSON.parse(readFileSync(systemJsonPath, "utf8"));
    packsMeta = sysJson.packs || [];
  }

  const packsRoot = join(systemPath, "packs");
  if (!existsSync(packsRoot)) {
    console.error("No packs/ directory found");
    process.exit(1);
  }

  mkdirSync(outputDir, { recursive: true });

  const packDirs = findPackDirs(packsRoot);
  console.log(`Found ${packDirs.length} LevelDB packs\n`);

  const summary = {};

  for (const dbPath of packDirs) {
    // Derive pack name from relative path
    const relPath = dbPath.replace(packsRoot + "\\", "").replace(packsRoot + "/", "");
    const packName = relPath.replace(/[\\/]/g, "_");

    // Find metadata
    const meta = packsMeta.find(
      (p) => p.path?.replace(/\.db$/, "").replace(/^packs[\\/]/, "").replace(/[\\/]/g, "_") === packName
    );

    console.log(`Extracting: ${packName} (${meta?.label || "unknown"}, type: ${meta?.type || "?"})`);

    try {
      const entries = await extractPack(dbPath);
      console.log(`  → ${entries.length} entries`);

      if (entries.length > 0) {
        const outFile = join(outputDir, `${packName}.json`);
        writeFileSync(outFile, JSON.stringify(entries, null, 2), "utf8");
        summary[packName] = {
          label: meta?.label || packName,
          type: meta?.type || "Item",
          count: entries.length,
        };
      }
    } catch (err) {
      console.error(`  ERROR: ${err.message}`);
    }
  }

  // Write summary
  writeFileSync(join(outputDir, "_summary.json"), JSON.stringify(summary, null, 2), "utf8");
  console.log("\nDone! Summary:");
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
