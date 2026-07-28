#!/bin/sh
# iGerd skills installer for macOS and Linux.
#
#   curl -fsSL https://jcode.sh/install | bash
#
# Downloads the iGerd repository and installs the skills it ships
# (.agents/skills/*) into your Claude Code skills directory, by default
# ~/.claude/skills.
#
# The script is POSIX sh: it runs under bash, dash, zsh and ash.

set -eu

VERSION="0.1.0"
REPO="${IGERD_REPO:-Ventje66/iGerd}"
REF="${IGERD_REF:-}"
DEST="${IGERD_INSTALL_DIR:-${HOME}/.claude/skills}"
SOURCE_SUBDIR="${IGERD_SOURCE_SUBDIR:-.agents/skills}"

BACKUP=1
BACKED_UP=0
DRY_RUN=0
QUIET=0
LIST_ONLY=0
UNINSTALL=0
LOCAL_PATH=""
WANTED=""

TMPDIR_SELF=""
DOWNLOADER=""

# ---------------------------------------------------------------- output ----

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
	C_RESET=$(printf '\033[0m')
	C_BOLD=$(printf '\033[1m')
	C_DIM=$(printf '\033[2m')
	C_RED=$(printf '\033[31m')
	C_GREEN=$(printf '\033[32m')
	C_YELLOW=$(printf '\033[33m')
else
	C_RESET=""; C_BOLD=""; C_DIM=""; C_RED=""; C_GREEN=""; C_YELLOW=""
fi

say() {
	[ "$QUIET" -eq 1 ] && return 0
	printf '%s\n' "$*"
}

info() { say "${C_DIM}==>${C_RESET} $*"; }
ok()   { say "${C_GREEN}  ok${C_RESET} $*"; }
warn() { printf '%swarning:%s %s\n' "$C_YELLOW" "$C_RESET" "$*" >&2; }

die() {
	printf '%serror:%s %s\n' "$C_RED" "$C_RESET" "$*" >&2
	exit 1
}

cleanup() {
	[ -n "$TMPDIR_SELF" ] && [ -d "$TMPDIR_SELF" ] && rm -rf "$TMPDIR_SELF"
	return 0
}
trap cleanup EXIT
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

usage() {
	cat <<EOF
${C_BOLD}iGerd skills installer${C_RESET} v${VERSION}

Installs the skills shipped in ${REPO} into your Claude Code skills directory.

${C_BOLD}Usage${C_RESET}
  curl -fsSL https://jcode.sh/install | bash
  curl -fsSL https://jcode.sh/install | bash -s -- [options]
  ./install.sh [options]

${C_BOLD}Options${C_RESET}
  -d, --dir DIR       Install into DIR (default: \$HOME/.claude/skills)
  -s, --skill NAME    Install only NAME; repeatable (default: every skill)
  -r, --ref REF       Branch, tag or commit to install from (default: the
                      repository's default branch)
      --repo OWNER/R  Source repository (default: ${REPO})
      --local [PATH]  Install from a local checkout instead of downloading
                      (default: the directory containing this script)
  -l, --list          List the available skills and exit
  -f, --force         Overwrite existing skills without keeping a backup
      --no-backup     Alias for --force
  -n, --dry-run       Show what would happen, change nothing
      --uninstall     Remove the installed skills from the install directory
  -q, --quiet         Only print warnings and errors
  -h, --help          Show this help and exit
  -V, --version       Print the installer version and exit

${C_BOLD}Environment${C_RESET}
  IGERD_INSTALL_DIR   Same as --dir
  IGERD_REF           Same as --ref
  IGERD_REPO          Same as --repo
  NO_COLOR            Disable coloured output

${C_BOLD}Examples${C_RESET}
  # install everything
  curl -fsSL https://jcode.sh/install | bash

  # install a single skill into a project-local directory
  curl -fsSL https://jcode.sh/install | bash -s -- --skill brainstorming --dir ./.claude/skills

  # preview an install from a feature branch
  curl -fsSL https://jcode.sh/install | bash -s -- --ref my-branch --dry-run
EOF
}

# ------------------------------------------------------------------ args ----

while [ $# -gt 0 ]; do
	case "$1" in
		-d|--dir)
			[ $# -ge 2 ] || die "$1 requires a directory"
			DEST="$2"; shift 2 ;;
		--dir=*)   DEST="${1#*=}"; shift ;;
		-s|--skill)
			[ $# -ge 2 ] || die "$1 requires a skill name"
			WANTED="${WANTED} $2"; shift 2 ;;
		--skill=*) WANTED="${WANTED} ${1#*=}"; shift ;;
		-r|--ref)
			[ $# -ge 2 ] || die "$1 requires a ref"
			REF="$2"; shift 2 ;;
		--ref=*)   REF="${1#*=}"; shift ;;
		--repo)
			[ $# -ge 2 ] || die "$1 requires OWNER/REPO"
			REPO="$2"; shift 2 ;;
		--repo=*)  REPO="${1#*=}"; shift ;;
		--local)
			shift
			if [ $# -gt 0 ] && [ -d "$1" ]; then
				LOCAL_PATH="$1"; shift
			else
				LOCAL_PATH="."
			fi ;;
		--local=*) LOCAL_PATH="${1#*=}"; shift ;;
		-l|--list)      LIST_ONLY=1; shift ;;
		-f|--force|--no-backup) BACKUP=0; shift ;;
		-n|--dry-run)   DRY_RUN=1; shift ;;
		--uninstall)    UNINSTALL=1; shift ;;
		-q|--quiet)     QUIET=1; shift ;;
		-h|--help)      usage; exit 0 ;;
		-V|--version)   printf '%s\n' "$VERSION"; exit 0 ;;
		--) shift; break ;;
		-*) die "unknown option: $1 (try --help)" ;;
		*)  die "unexpected argument: $1 (try --help)" ;;
	esac
done

# --------------------------------------------------------------- preflight --

check_platform() {
	uname_s=$(uname -s 2>/dev/null || echo unknown)
	case "$uname_s" in
		Darwin) PLATFORM="macOS" ;;
		Linux)  PLATFORM="Linux" ;;
		*)
			die "unsupported platform: ${uname_s}. This installer supports macOS and Linux only.
On Windows, use WSL or copy ${SOURCE_SUBDIR}/ into your Claude skills directory by hand."
			;;
	esac
}

check_tools() {
	command -v tar >/dev/null 2>&1 || die "'tar' is required but was not found in PATH"
	command -v mktemp >/dev/null 2>&1 || die "'mktemp' is required but was not found in PATH"

	if command -v curl >/dev/null 2>&1; then
		DOWNLOADER="curl"
	elif command -v wget >/dev/null 2>&1; then
		DOWNLOADER="wget"
	else
		die "either 'curl' or 'wget' is required to download ${REPO}"
	fi
}

download() {
	# download <url> <output-path>
	if [ "$DOWNLOADER" = "curl" ]; then
		curl -fsSL --retry 3 --retry-delay 2 --proto '=https' --tlsv1.2 \
			-o "$2" "$1"
	else
		wget -q --tries=3 --waitretry=2 -O "$2" "$1"
	fi
}

# ---------------------------------------------------------------- sources ---

fetch_source() {
	# Populates SRC_ROOT with a directory containing the repository tree.
	if [ -n "$LOCAL_PATH" ]; then
		[ -d "$LOCAL_PATH" ] || die "local path not found: ${LOCAL_PATH}"
		SRC_ROOT=$(cd "$LOCAL_PATH" && pwd)
		info "Using local checkout ${C_BOLD}${SRC_ROOT}${C_RESET}"
		return 0
	fi

	TMPDIR_SELF=$(mktemp -d "${TMPDIR:-/tmp}/igerd-install.XXXXXX") \
		|| die "could not create a temporary directory"

	# codeload serves branch, tag and commit tarballs anonymously and without
	# the API's rate limit; the literal ref "HEAD" resolves to the
	# repository's default branch, whatever it happens to be named.
	if [ -n "$REF" ]; then
		url="https://codeload.github.com/${REPO}/tar.gz/${REF}"
		info "Downloading ${C_BOLD}${REPO}${C_RESET} @ ${C_BOLD}${REF}${C_RESET}"
	else
		url="https://codeload.github.com/${REPO}/tar.gz/HEAD"
		info "Downloading ${C_BOLD}${REPO}${C_RESET} (default branch)"
	fi

	tarball="${TMPDIR_SELF}/source.tar.gz"
	download "$url" "$tarball" \
		|| die "download failed: ${url}
Check the repository name, the ref, and your network connection."
	[ -s "$tarball" ] || die "downloaded an empty archive from ${url}"

	SRC_ROOT="${TMPDIR_SELF}/src"
	mkdir -p "$SRC_ROOT"
	tar -xzf "$tarball" -C "$SRC_ROOT" --strip-components=1 \
		|| die "could not extract the downloaded archive"
}

discover_skills() {
	# Prints the name of every directory under SRC_ROOT/SOURCE_SUBDIR that
	# looks like a skill (i.e. contains a SKILL.md).
	skills_dir="${SRC_ROOT}/${SOURCE_SUBDIR}"
	[ -d "$skills_dir" ] || die "no skills directory at ${SOURCE_SUBDIR} in ${REPO}"

	found=0
	for candidate in "$skills_dir"/*; do
		[ -d "$candidate" ] || continue
		[ -f "${candidate}/SKILL.md" ] || continue
		name=$(basename "$candidate")
		# Skill names travel through unquoted word splitting below, so a name
		# containing whitespace would silently install as two broken halves.
		case "$name" in
			*[[:space:]]*)
				warn "skipping '${name}': skill names must not contain whitespace"
				continue ;;
		esac
		printf '%s\n' "$name"
		found=1
	done
	[ "$found" -eq 1 ] || die "no skills found in ${SOURCE_SUBDIR}/ (expected directories containing SKILL.md)"
}

selected_skills() {
	# Filters discover_skills through --skill, erroring on unknown names.
	available=$(discover_skills)

	if [ -z "${WANTED# }" ]; then
		printf '%s\n' "$available"
		return 0
	fi

	for want in $WANTED; do
		matched=0
		for have in $available; do
			[ "$want" = "$have" ] && matched=1 && break
		done
		[ "$matched" -eq 1 ] || die "unknown skill: ${want}
Available: $(printf '%s' "$available" | tr '\n' ' ')"
		printf '%s\n' "$want"
	done
}

# ---------------------------------------------------------------- actions ---

install_skill() {
	# install_skill <name>
	name="$1"
	src="${SRC_ROOT}/${SOURCE_SUBDIR}/${name}"
	dst="${DEST}/${name}"

	if [ -e "$dst" ]; then
		if [ "$BACKUP" -eq 1 ]; then
			backup="${dst}.bak-$(date +%Y%m%d%H%M%S)"
			if [ "$DRY_RUN" -eq 1 ]; then
				say "  would back up ${C_DIM}${dst}${C_RESET} -> ${C_DIM}${backup}${C_RESET}"
			else
				mv "$dst" "$backup" || die "could not back up ${dst}"
				say "  backed up existing ${name} -> ${C_DIM}$(basename "$backup")${C_RESET}"
				BACKED_UP=$((BACKED_UP + 1))
			fi
		elif [ "$DRY_RUN" -eq 1 ]; then
			say "  would overwrite ${C_DIM}${dst}${C_RESET}"
		else
			rm -rf "$dst" || die "could not remove ${dst}"
		fi
	fi

	if [ "$DRY_RUN" -eq 1 ]; then
		say "  would install ${C_BOLD}${name}${C_RESET} -> ${dst}"
		return 0
	fi

	# Copy to a staging path first so an interrupted copy never leaves a
	# half-written skill behind at the destination.
	staging="${DEST}/.${name}.incoming.$$"
	rm -rf "$staging"
	cp -R "$src" "$staging" || die "could not copy ${name} into ${DEST}"
	mv "$staging" "$dst" || { rm -rf "$staging"; die "could not install ${name}"; }

	ok "${C_BOLD}${name}${C_RESET}"
}

uninstall_skill() {
	# uninstall_skill <name>
	name="$1"
	dst="${DEST}/${name}"

	if [ ! -d "$dst" ]; then
		say "  ${C_DIM}not installed:${C_RESET} ${name}"
		return 0
	fi
	if [ ! -f "${dst}/SKILL.md" ]; then
		warn "skipping ${dst}: it does not look like a skill (no SKILL.md)"
		return 0
	fi

	if [ "$DRY_RUN" -eq 1 ]; then
		say "  would remove ${dst}"
		return 0
	fi

	if [ "$BACKUP" -eq 1 ]; then
		backup="${dst}.bak-$(date +%Y%m%d%H%M%S)"
		mv "$dst" "$backup" || die "could not move ${dst}"
		ok "removed ${C_BOLD}${name}${C_RESET} ${C_DIM}(kept $(basename "$backup"))${C_RESET}"
	else
		rm -rf "$dst" || die "could not remove ${dst}"
		ok "removed ${C_BOLD}${name}${C_RESET}"
	fi
}

# ------------------------------------------------------------------- main ---

main() {
	check_platform

	# Downloading is the only step with extra tool requirements.
	if [ -z "$LOCAL_PATH" ]; then
		check_tools
	fi

	# When piped from the web there is no script directory to fall back on,
	# so --local only defaults sensibly for a real file on disk.
	if [ "$LOCAL_PATH" = "." ] && [ ! -d "./${SOURCE_SUBDIR}" ]; then
		die "--local was given but ${SOURCE_SUBDIR}/ is not in the current directory.
Pass an explicit path, e.g. --local /path/to/iGerd"
	fi

	fetch_source
	skills=$(selected_skills)

	if [ "$LIST_ONLY" -eq 1 ]; then
		if [ -n "$LOCAL_PATH" ]; then
			say "${C_BOLD}Skills in ${SRC_ROOT}${C_RESET}"
		else
			say "${C_BOLD}Skills in ${REPO}${C_RESET}"
		fi
		for name in $skills; do
			summary=$(sed -n 's/^description:[[:space:]]*//p' \
				"${SRC_ROOT}/${SOURCE_SUBDIR}/${name}/SKILL.md" 2>/dev/null \
				| head -n 1 | sed 's/^["'\'']//; s/["'\'']$//')
			if [ -n "$summary" ]; then
				say "  ${name} ${C_DIM}- $(printf '%.100s' "$summary")${C_RESET}"
			else
				say "  ${name}"
			fi
		done
		exit 0
	fi

	if [ "$UNINSTALL" -eq 1 ]; then
		info "Uninstalling from ${C_BOLD}${DEST}${C_RESET}"
		[ -d "$DEST" ] || die "nothing to uninstall: ${DEST} does not exist"
		for name in $skills; do
			uninstall_skill "$name"
		done
		say ""
		say "Done."
		exit 0
	fi

	if [ "$DRY_RUN" -eq 1 ]; then
		info "Dry run - nothing will be written"
	elif [ ! -d "$DEST" ]; then
		mkdir -p "$DEST" || die "could not create ${DEST}"
	fi

	if [ "$DRY_RUN" -eq 0 ] && [ ! -w "$DEST" ]; then
		die "${DEST} is not writable by $(id -un 2>/dev/null || echo "the current user")"
	fi

	info "Installing into ${C_BOLD}${DEST}${C_RESET} on ${PLATFORM}"
	count=0
	for name in $skills; do
		install_skill "$name"
		count=$((count + 1))
	done

	say ""
	if [ "$DRY_RUN" -eq 1 ]; then
		say "${C_BOLD}Dry run complete${C_RESET} - ${count} skill(s) would be installed."
	else
		say "${C_BOLD}Installed ${count} skill(s).${C_RESET}"
		say "Restart Claude Code (or start a new session) to pick them up."
		if [ "$BACKED_UP" -gt 0 ]; then
			say "${C_DIM}${BACKED_UP} replaced skill(s) kept alongside as *.bak-<timestamp>.${C_RESET}"
		fi
	fi
}

main
