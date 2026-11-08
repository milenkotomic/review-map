#!/usr/bin/env bash
# Symlink the review-map skill into ~/.claude/skills so Claude Code picks it up.
# Re-running is safe; an existing real directory is backed up first.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
src="$here/skills/review-map"
dst="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/review-map"

mkdir -p "$(dirname "$dst")"
chmod +x "$src/scripts/"*

if [[ -L "$dst" ]]; then
  rm "$dst"
elif [[ -d "$dst" ]]; then
  backup="$dst.bak.$(date +%s)"
  echo "existing directory moved to $backup"
  mv "$dst" "$backup"
fi

ln -s "$src" "$dst"
echo "linked $dst -> $src"

for tool in git python3; do
  command -v "$tool" >/dev/null || echo "warning: $tool not found; the skill needs it"
done
command -v gh >/dev/null || echo "note: gh not found; PR mode (/review-map <number>) needs it"
echo "start a new Claude Code session and type /review-map"
