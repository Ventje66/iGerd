# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
This is a skills package for the "superpowers" agent plugin. It contains agent
skill definitions (Markdown plus supporting scripts) under `.agents/skills/`,
mirrored into `.claude/skills/` via symlinks. `skills-lock.json` records the
upstream skill sources (`obra/superpowers`).

There is **no dependency manifest** (`package.json`, `requirements.txt`, etc.),
**no build step, no automated test suite, and no linter** configured in this
repo. Node.js (v22) and Python 3 are preinstalled; the one runnable component
below uses only Node built-in modules, so there is nothing to install.

### The only runnable app: brainstorming visual companion
A zero-dependency Node HTTP + WebSocket server the `brainstorming` skill uses to
show mockups in a browser. Source: `.agents/skills/brainstorming/scripts/`
(`server.cjs`, `start-server.sh`, `stop-server.sh`, `frame-template.html`,
`helper.js`).

Start it (foreground, inside a persistent shell such as tmux):

```
.agents/skills/brainstorming/scripts/start-server.sh \
  --project-dir /workspace --host 0.0.0.0 --url-host localhost --foreground
```

Non-obvious notes:
- Run it with `--foreground` in a persistent shell here. Default background mode
  can be reaped, and the server also self-exits if its owner PID dies or after
  30 minutes of inactivity.
- On startup it prints a JSON line with `url`, `screen_dir`, and `state_dir`; the
  same JSON is also written to `<state_dir>/server-info`.
- To drive it, write an `.html` file into `screen_dir`. The server serves the
  newest file at `/` (wrapping content fragments in `frame-template.html` and
  injecting `helper.js`) and broadcasts a WebSocket `reload` so open browsers
  auto-update. Browser clicks on `[data-choice]` elements are appended to
  `<state_dir>/events` (one JSON object per line).
- With `--project-dir /workspace`, session files live under
  `/workspace/.superpowers/brainstorm/<id>/` (gitignored) and persist after the
  server stops; without `--project-dir` they go to `/tmp` and are deleted on stop.
- Stop it: `.agents/skills/brainstorming/scripts/stop-server.sh <session_dir>`.

### Verify the environment
No linter or automated test suite is configured. To smoke-test the runnable server:

```
./scripts/verify-environment.sh
```

Starts a temporary companion server on port 59999 (override with `VERIFY_PORT`),
pushes a screen, checks HTTP serving and 404 handling, then tears down.

### Verify plugin install (`install.sh`)
After merging the installer, smoke-test the local install path:

```
./scripts/verify-plugin-install.sh
```

Runs `sh -n` / `bash -n`, `--list`, `--dry-run`, a real install into a temp
directory, and `--uninstall`. Human install docs live in `README.md`.

### Verify Cursor plugin (cursor/plugins spec)
This repo is a single Cursor plugin. Manifest:
`.cursor-plugin/plugin.json`. Skills stay under `.agents/skills/` (the
manifest `skills` field points there). Smoke-test:

```
./scripts/verify-cursor-plugin.sh
```

Runs `scripts/validate-cursor-plugin.cjs` against the checkout, a staged
`~/.cursor/plugins/local/igerd`-style copy, and a deliberately invalid
manifest (must fail). Zero npm dependencies.
