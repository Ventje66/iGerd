#!/usr/bin/env node
/**
 * Validate this repo as a single-plugin Cursor plugin.
 *
 * Checks match the Cursor plugin spec used by
 * https://github.com/cursor/plugins (plugin.json schema + path safety +
 * skill frontmatter). Zero npm dependencies — Node built-ins only.
 *
 * Usage: node scripts/validate-cursor-plugin.cjs [plugin-root]
 */
"use strict";

const fs = require("fs");
const path = require("path");

const PLUGIN_NAME_RE = /^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$/;
const SEMVER_RE =
  /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?$/;
const URI_RE = /^https?:\/\/\S+$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const ALLOWED_PLUGIN_KEYS = new Set([
  "name",
  "displayName",
  "description",
  "version",
  "minClientVersions",
  "author",
  "publisher",
  "homepage",
  "repository",
  "license",
  "logo",
  "keywords",
  "category",
  "tags",
  "commands",
  "agents",
  "skills",
  "rules",
  "hooks",
  "variables",
  "mcpServers",
]);

const PATH_FIELDS = [
  "logo",
  "rules",
  "skills",
  "agents",
  "commands",
  "hooks",
  "mcpServers",
];

const errors = [];
const warnings = [];

function fail(message) {
  errors.push(message);
}

function warn(message) {
  warnings.push(message);
}

function pluginRootFromArgv() {
  const arg = process.argv[2];
  if (arg) {
    return path.resolve(arg);
  }
  return path.resolve(__dirname, "..");
}

function readJson(filePath, label) {
  if (!fs.existsSync(filePath)) {
    fail(`${label} is missing: ${filePath}`);
    return null;
  }
  const raw = fs.readFileSync(filePath, "utf8");
  try {
    return JSON.parse(raw);
  } catch (err) {
    fail(`${label} is not valid JSON (${filePath}): ${err.message}`);
    return null;
  }
}

function isSafeRelativePath(value) {
  if (typeof value !== "string" || value.length === 0) {
    return false;
  }
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return true;
  }
  if (path.isAbsolute(value)) {
    return false;
  }
  const normalized = path.posix.normalize(value.replace(/\\/g, "/"));
  return !normalized.startsWith("../") && normalized !== "..";
}

function extractPathValues(value) {
  if (typeof value === "string") {
    return [value];
  }
  if (Array.isArray(value)) {
    return value.flatMap(extractPathValues);
  }
  if (value && typeof value === "object") {
    const out = [];
    if (typeof value.path === "string") {
      out.push(value.path);
    }
    if (typeof value.file === "string") {
      out.push(value.file);
    }
    return out;
  }
  return [];
}

function parseFrontmatter(content) {
  const normalized = content.replace(/\r\n/g, "\n");
  if (!normalized.startsWith("---\n")) {
    return null;
  }
  const closingIndex = normalized.indexOf("\n---\n", 4);
  if (closingIndex === -1) {
    return null;
  }
  const fields = {};
  for (const line of normalized.slice(4, closingIndex).split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    const separator = line.indexOf(":");
    if (separator === -1) {
      continue;
    }
    const key = line.slice(0, separator).trim();
    let value = line.slice(separator + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    fields[key] = value;
  }
  return fields;
}

function walkFiles(dirPath) {
  const files = [];
  const stack = [dirPath];
  while (stack.length > 0) {
    const current = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      fail(`cannot read directory: ${current}`);
      continue;
    }
    for (const entry of entries) {
      const entryPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(entryPath);
      } else if (entry.isFile() || entry.isSymbolicLink()) {
        files.push(entryPath);
      }
    }
  }
  return files;
}

function resolveComponentDirs(pluginDir, manifest, field, defaultDir) {
  if (manifest[field] === undefined) {
    const fallback = path.join(pluginDir, defaultDir);
    return fs.existsSync(fallback) ? [fallback] : [];
  }
  const dirs = [];
  for (const value of extractPathValues(manifest[field])) {
    if (value.startsWith("http://") || value.startsWith("https://")) {
      continue;
    }
    dirs.push(path.resolve(pluginDir, value));
  }
  return dirs;
}

function validateReferencedPath(pluginDir, fieldName, pathValue) {
  if (pathValue.startsWith("http://") || pathValue.startsWith("https://")) {
    return;
  }
  if (!isSafeRelativePath(pathValue)) {
    fail(
      `field "${fieldName}" has invalid path "${pathValue}". Use a relative path without ".." or absolute prefixes.`
    );
    return;
  }
  const resolved = path.resolve(pluginDir, pathValue);
  if (!fs.existsSync(resolved)) {
    fail(`field "${fieldName}" references missing path "${pathValue}".`);
  }
}

function validateSkillFrontmatter(pluginDir, manifest) {
  const skillDirs = resolveComponentDirs(
    pluginDir,
    manifest,
    "skills",
    "skills"
  );
  let skillCount = 0;
  for (const dir of skillDirs) {
    if (!fs.existsSync(dir)) {
      continue;
    }
    for (const file of walkFiles(dir)) {
      if (path.basename(file) !== "SKILL.md") {
        continue;
      }
      skillCount += 1;
      const content = fs.readFileSync(file, "utf8");
      const parsed = parseFrontmatter(content);
      const relativeFile = path.relative(pluginDir, file);
      if (!parsed) {
        fail(`skill file missing YAML frontmatter: ${relativeFile}`);
        continue;
      }
      for (const key of ["name", "description"]) {
        if (!parsed[key] || parsed[key].length === 0) {
          fail(`skill file missing "${key}" in frontmatter: ${relativeFile}`);
        }
      }
    }
  }
  if (skillCount === 0) {
    fail('no SKILL.md files found under the configured skills path');
  }
}

function validateManifest(pluginDir, manifest) {
  for (const key of Object.keys(manifest)) {
    if (!ALLOWED_PLUGIN_KEYS.has(key)) {
      fail(`plugin.json has unknown field "${key}"`);
    }
  }

  if (typeof manifest.name !== "string" || !PLUGIN_NAME_RE.test(manifest.name)) {
    fail(
      '"name" must be lowercase kebab-case (alphanumerics, hyphens, periods) and start/end with an alphanumeric character.'
    );
  }

  if (manifest.version !== undefined && !SEMVER_RE.test(String(manifest.version))) {
    fail(`"version" must be a semantic version, got "${manifest.version}"`);
  }

  if (manifest.author !== undefined) {
    if (
      !manifest.author ||
      typeof manifest.author !== "object" ||
      typeof manifest.author.name !== "string" ||
      manifest.author.name.length === 0
    ) {
      fail('"author.name" is required when "author" is set');
    }
    if (
      manifest.author &&
      manifest.author.email !== undefined &&
      !EMAIL_RE.test(String(manifest.author.email))
    ) {
      fail(`"author.email" is not a valid email: "${manifest.author.email}"`);
    }
  } else {
    warn('"author" is recommended');
  }

  for (const field of ["homepage", "repository"]) {
    if (manifest[field] !== undefined && !URI_RE.test(String(manifest[field]))) {
      fail(`"${field}" must be an http(s) URL`);
    }
  }

  for (const field of ["keywords", "tags"]) {
    if (manifest[field] !== undefined) {
      if (
        !Array.isArray(manifest[field]) ||
        manifest[field].some((item) => typeof item !== "string")
      ) {
        fail(`"${field}" must be an array of strings`);
      }
    }
  }

  if (!manifest.description) {
    warn('"description" is recommended');
  }
  if (!manifest.license) {
    warn('"license" is recommended');
  }

  for (const field of PATH_FIELDS) {
    if (manifest[field] === undefined) {
      continue;
    }
    for (const value of extractPathValues(manifest[field])) {
      validateReferencedPath(pluginDir, field, value);
    }
  }

  validateSkillFrontmatter(pluginDir, manifest);
}

function main() {
  const pluginDir = pluginRootFromArgv();
  const marketplacePath = path.join(
    pluginDir,
    ".cursor-plugin",
    "marketplace.json"
  );
  if (fs.existsSync(marketplacePath)) {
    fail(
      "this validator covers a single-plugin repo; remove marketplace.json or extend the script"
    );
  }

  const manifestPath = path.join(pluginDir, ".cursor-plugin", "plugin.json");
  const manifest = readJson(manifestPath, "plugin manifest");
  if (manifest) {
    validateManifest(pluginDir, manifest);
  }

  if (warnings.length > 0) {
    console.log("Warnings:");
    for (const message of warnings) {
      console.log(`- ${message}`);
    }
    console.log("");
  }

  if (errors.length > 0) {
    console.error("Validation failed:");
    for (const message of errors) {
      console.error(`- ${message}`);
    }
    process.exit(1);
  }

  console.log("OK: Cursor plugin manifest and skills validated");
}

main();
