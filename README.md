# iGerd

A collection of [Claude Code](https://claude.com/claude-code) skills, plus a
one-line installer that drops them into your skills directory.

The skills live in [`.agents/skills/`](.agents/skills), one directory per
skill. Their provenance is tracked in [`skills-lock.json`](skills-lock.json).

| Skill | What it does |
| --- | --- |
| `brainstorming` | Explores intent, requirements and design before any creative or implementation work. |
| `using-superpowers` | Establishes how to find and use skills at the start of a conversation. |

## macOS &amp; Linux

```sh
curl -fsSL https://jcode.sh/install | bash
```

That downloads this repository and copies every skill into
`~/.claude/skills/`. Restart Claude Code (or start a new session) afterwards
and the skills are available.

If you would rather not go through `jcode.sh`, the same script is served
straight from GitHub:

```sh
curl -fsSL https://raw.githubusercontent.com/Ventje66/iGerd/HEAD/install.sh | bash
```

Windows is not supported by the installer — use WSL, or copy
`.agents/skills/*` into `%USERPROFILE%\.claude\skills\` by hand.

### Read it before you run it

Piping a script from the internet into `bash` runs whatever that URL happens
to serve. [`install.sh`](install.sh) is short and dependency-free; reading it
first is a reasonable habit:

```sh
curl -fsSL https://jcode.sh/install | less
```

## Options

Pass options through `bash -s --`:

```sh
# see what is on offer without installing anything
curl -fsSL https://jcode.sh/install | bash -s -- --list

# install one skill into a project rather than your home directory
curl -fsSL https://jcode.sh/install | bash -s -- --skill brainstorming --dir ./.claude/skills

# preview an install from a feature branch
curl -fsSL https://jcode.sh/install | bash -s -- --ref my-branch --dry-run
```

| Option | Effect |
| --- | --- |
| `-d`, `--dir DIR` | Install into `DIR` (default `$HOME/.claude/skills`). |
| `-s`, `--skill NAME` | Install only `NAME`. Repeatable. Default is every skill. |
| `-r`, `--ref REF` | Install from a branch, tag or commit. Default is the repository's default branch. |
| `--repo OWNER/REPO` | Install from a different repository with the same layout. |
| `--local [PATH]` | Install from a local checkout instead of downloading. |
| `-l`, `--list` | List the available skills and exit. |
| `-f`, `--force` | Overwrite existing skills instead of keeping a backup. |
| `-n`, `--dry-run` | Print what would happen; change nothing. |
| `--uninstall` | Remove the installed skills again. |
| `-q`, `--quiet` | Only print warnings and errors. |
| `-h`, `--help` | Full help. |

The environment variables `IGERD_INSTALL_DIR`, `IGERD_REF` and `IGERD_REPO`
mirror `--dir`, `--ref` and `--repo`, which is handy when you cannot pass
arguments through a pipe. `NO_COLOR` disables coloured output.

### Existing skills are kept

If a skill of the same name is already installed, the old copy is moved aside
to `<name>.bak-<timestamp>` in the same directory before the new one lands.
Pass `--force` to overwrite without a backup, and delete the `.bak-*`
directories once you are happy with the result.

## Uninstall

```sh
curl -fsSL https://jcode.sh/install | bash -s -- --uninstall
```

Each removed skill is moved to `<name>.bak-<timestamp>` unless you also pass
`--force`. Only directories that contain a `SKILL.md` are touched.

## Installing without the script

```sh
git clone https://github.com/Ventje66/iGerd.git
cp -R iGerd/.agents/skills/* ~/.claude/skills/
```

Or, from a checkout you already have:

```sh
./install.sh --local .
```

## Hosting the installer at `jcode.sh/install`

`https://jcode.sh/install` should serve the contents of `install.sh` verbatim,
as `text/plain`, over HTTPS. A redirect to
`https://raw.githubusercontent.com/Ventje66/iGerd/HEAD/install.sh` works too —
`curl -fsSL` follows redirects, including across hosts.

## Requirements

- macOS or Linux
- `curl` or `wget`, and `tar` — all present by default on both platforms

The installer is POSIX `sh`, so it also runs under `dash`, `zsh` and `ash`,
not just `bash`.

## Development

This repository has no dependency manifest or linter. Node.js (v22+) is required
only for the brainstorming visual-companion server (built-in modules only).

Verify the environment from a checkout:

```sh
./scripts/verify-environment.sh      # companion server HTTP smoke test
./scripts/verify-plugin-install.sh   # install.sh local install cycle
```

Cloud agents and contributors should also read [`AGENTS.md`](AGENTS.md) for
non-obvious run notes (tmux/foreground server, session directories).
