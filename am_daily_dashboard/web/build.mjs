// Bundle the AM Brief board into ONE self-contained offline HTML file.
//
//   node build.mjs            write ../handoffs/elite_am_brief_web.html
//   node build.mjs --check    verify the committed file is up to date
//
// The single-file output is non-negotiable: the brief is opened from OneDrive
// and from copied folders with no server and no network. So there is no CSS or
// asset pipeline here — app.css and icons.svg are concatenated verbatim (they
// were never the spaghetti, and processing them would add behaviour risk for
// nothing). Only src/*.ts goes through esbuild.
//
// Not minified, on purpose: the built file is committed, so a readable bundle
// keeps `git diff` reviewable.

import esbuild from "esbuild";
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(__dirname, "src");
const SHELL = path.join(__dirname, "shell.html");
const OUT = path.join(__dirname, "..", "handoffs", "elite_am_brief_web.html");

const STAMP_MARKER = "__BUILD_STAMP__";
const STAMP_RE = /<!-- am-brief-build sources sha256:[0-9a-f]{64} output sha256:[0-9a-f]{64} -->/;

// Hash LF-normalised bytes in every implementation. The repo is checked out
// with CRLF on Windows (core.autocrlf=true), so hashing raw bytes would make a
// fresh clone disagree with the machine that built it.
const lf = (s) => s.replace(/\r\n/g, "\n");
const sha = (s) => createHash("sha256").update(lf(s), "utf-8").digest("hex");

function sourceFiles() {
  const files = [
    ["shell.html", SHELL],
    ["build.mjs", path.join(__dirname, "build.mjs")],
  ];
  const walk = (dir, prefix) => {
    for (const entry of readdirSync(dir, { withFileTypes: true }).sort((a, b) =>
      a.name < b.name ? -1 : 1
    )) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full, `${prefix}${entry.name}/`);
      else files.push([`src/${prefix}${entry.name}`, full]);
    }
  };
  walk(SRC, "");
  return files.sort((a, b) => (a[0] < b[0] ? -1 : 1));
}

function fileHashBytes(full) {
  const ext = path.extname(full).toLowerCase();
  if (ext === ".png" || ext === ".jpg" || ext === ".jpeg" || ext === ".webp") {
    return readFileSync(full);
  }
  return Buffer.from(lf(readFileSync(full, "utf-8")), "utf-8");
}

// One hash over every input to the build, so "edited the TS and forgot to
// rebuild" is a loud test failure rather than a board that silently ignores
// the change.
export function sourcesHash() {
  const h = createHash("sha256");
  for (const [name, full] of sourceFiles()) {
    h.update(name);
    h.update("\0");
    h.update(fileHashBytes(full));
    h.update("\0");
  }
  return h.digest("hex");
}

// Hash of the built file with its own stamp line blanked back to the marker,
// since the stamp carries this value and cannot contain itself. Catches the
// opposite mistake: hand-editing the generated HTML, whose change would
// otherwise vanish at the next build with no warning.
export function outputHash(html) {
  return sha(html.replace(STAMP_RE, STAMP_MARKER));
}

async function bundle() {
  const result = await esbuild.build({
    entryPoints: [path.join(SRC, "main.ts")],
    bundle: true,
    format: "iife",
    target: "es2019",
    minify: false,
    write: false,
    logLevel: "warning",
    loader: { ".png": "dataurl" },
    // Unminified output gets a "// src/foo.ts" comment before each module,
    // relative to absWorkingDir (default: process.cwd()). Pin it to this
    // directory so the build is byte-identical regardless of the caller's
    // cwd - e.g. tests_js/package.json's pretest invokes this file as
    // "../web/build.mjs", which would otherwise stamp every comment
    // "../web/src/foo.ts" instead of "src/foo.ts".
    absWorkingDir: __dirname,
    // The pre-refactor board ran under an inline `"use strict"`. Pinning it to
    // the bundle rather than to whichever module statement lands first keeps
    // that guarantee no matter how the modules are later reshuffled.
    banner: { js: '"use strict";' },
  });
  return result.outputFiles[0].text;
}

async function buildHtml() {
  const js = await bundle();
  const shell = readFileSync(SHELL, "utf-8");
  for (const marker of ["__APP_CSS__", "__ICON_SPRITE__", "__APP_JS__", STAMP_MARKER]) {
    if (!shell.includes(marker)) throw new Error(`shell.html is missing ${marker}`);
  }
  // __PAYLOAD_JSON__ is deliberately left in place: the built file is a
  // template that Python fills in per report via elite_lib.html_export.
  const html = shell
    .replace("__APP_CSS__", () => readFileSync(path.join(SRC, "app.css"), "utf-8"))
    .replace("__ICON_SPRITE__", () => readFileSync(path.join(SRC, "icons.svg"), "utf-8"))
    .replace("__APP_JS__", () => `\n${js}  `);

  const sources = sourcesHash();
  const stamped = html.replace(
    STAMP_MARKER,
    () => `<!-- am-brief-build sources sha256:${sources} output sha256:${"0".repeat(64)} -->`
  );
  const output = outputHash(stamped);
  return stamped.replace(
    STAMP_RE,
    () => `<!-- am-brief-build sources sha256:${sources} output sha256:${output} -->`
  );
}

async function main() {
  const html = await buildHtml();
  if (process.argv.includes("--check")) {
    const committed = readFileSync(OUT, "utf-8");
    if (lf(committed) !== lf(html)) {
      console.error(
        "FAIL: handoffs/elite_am_brief_web.html is not what web/ builds.\n" +
          "      Run `node am_daily_dashboard/web/build.mjs` and commit the result."
      );
      process.exit(1);
    }
    console.log("OK: the committed shell matches web/ sources.");
    return;
  }
  writeFileSync(OUT, html, "utf-8");
  console.log(`Built ${path.relative(path.join(__dirname, ".."), OUT)} (${html.length} chars)`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
  await main();
}
