#!/usr/bin/env bash
# Collect a diff bundle (stat, name-status, full patch) into one file.
#
# Usage:
#   collect-diff.sh [-C REPO] [--out FILE] [--base REF] [--head REF]
#   collect-diff.sh [-C REPO] [--out FILE] --pr NUMBER
#   collect-diff.sh [-C REPO] [--out FILE] --range A..B
#   collect-diff.sh [-C REPO] [--out FILE] --worktree   # staged + unstaged + branch commits
#
# Defaults: --worktree if nothing is given. -C defaults to the current directory.
# --out defaults to a fresh private mktemp file under $TMPDIR, never inside the repo.
# The output is plain text, meant to be read once, top to bottom.

set -euo pipefail
# The bundle can hold secrets from the diff: keep every file this script writes private.
umask 077

out=""
repo="."
mode="worktree"
base=""
head="HEAD"
pr=""
range=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -C|--repo) repo="$2"; shift 2 ;;
    --out) out="$2"; shift 2 ;;
    --base) base="$2"; mode="branch"; shift 2 ;;
    --head) head="$2"; mode="branch"; shift 2 ;;
    --pr) pr="$2"; mode="pr"; shift 2 ;;
    --range) range="$2"; mode="range"; shift 2 ;;
    --worktree) mode="worktree"; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Refs and PR come from the model, which may have read hostile text. Reject anything
# git or gh could parse as an option (e.g. --output=FILE), and pass refs after
# --end-of-options as a second guard.
not_option() { [[ "$2" != -* ]] || { echo "invalid $1: $2" >&2; exit 2; }; }
not_option --base "$base"; not_option --head "$head"; not_option --range "$range"
if [[ "$mode" == pr && ! "$pr" =~ ^([0-9]+|https://[^[:space:]]+/pull/[0-9]+/?)$ ]]; then
  echo "invalid --pr: $pr (want a number or a pull request URL)" >&2; exit 2
fi

[[ -n "$out" ]] || out="$(mktemp "${TMPDIR:-/tmp}/recap-diff-XXXXXXXX")"
out="$(cd "$(dirname "$out")" && pwd)/$(basename "$out")"
cd "$repo"

default_branch() {
  git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' \
    || { git show-ref --verify --quiet refs/heads/main && echo main; } \
    || echo master
}

section() { printf '\n==================== %s ====================\n' "$1"; }

{
  echo "# recap diff bundle"
  echo "mode: $mode"
  echo "generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

  case "$mode" in
    pr)
      echo "pr: $pr"
      section "PR METADATA"
      gh pr view "$pr" --json number,title,body,state,mergedAt,baseRefName,headRefName,additions,deletions,changedFiles \
        --template '{{.number}} {{.title}}
state: {{.state}}{{if .mergedAt}}  merged: {{.mergedAt}}{{end}}
base: {{.baseRefName}}  head: {{.headRefName}}
+{{.additions}} -{{.deletions}} files: {{.changedFiles}}

{{.body}}
'
      section "FILES"
      gh pr view "$pr" --json files --jq '.files[] | "\(.additions)\t\(.deletions)\t\(.path)"'
      section "PATCH"
      gh pr diff "$pr"
      ;;
    branch)
      if [[ -z "$base" ]]; then
        db="$(default_branch)"
        base="$(git merge-base --end-of-options "origin/$db" "$head" 2>/dev/null || git merge-base --end-of-options "$db" "$head")"
        echo "base: merge-base with $db = $base"
      else
        echo "base: $base"
      fi
      echo "head: $head"
      section "COMMITS"
      git log --oneline --no-decorate --end-of-options "$base..$head"
      section "STAT"
      git diff --stat=120 --end-of-options "$base" "$head"
      section "NAME-STATUS"
      git diff --name-status -M --end-of-options "$base" "$head"
      section "PATCH"
      git diff -M --no-color --end-of-options "$base" "$head"
      ;;
    range)
      echo "range: $range"
      section "COMMITS"
      git log --oneline --no-decorate --end-of-options "$range"
      section "STAT"
      git diff --stat=120 --end-of-options "$range"
      section "NAME-STATUS"
      git diff --name-status -M --end-of-options "$range"
      section "PATCH"
      git diff -M --no-color --end-of-options "$range"
      ;;
    worktree)
      db="$(default_branch)"
      mb="$(git merge-base --end-of-options "origin/$db" HEAD 2>/dev/null || git merge-base --end-of-options "$db" HEAD 2>/dev/null || echo "")"
      if [[ -n "$mb" && "$mb" != "$(git rev-parse HEAD)" ]]; then
        echo "branch commits since merge-base with $db ($mb):"
        section "COMMITS"
        git log --oneline --no-decorate --end-of-options "$mb..HEAD"
        section "STAT (committed on branch)"
        git diff --stat=120 --end-of-options "$mb" HEAD
        section "NAME-STATUS (committed on branch)"
        git diff --name-status -M --end-of-options "$mb" HEAD
        section "PATCH (committed on branch)"
        git diff -M --no-color --end-of-options "$mb" HEAD
      fi
      section "STAT (uncommitted: staged + unstaged)"
      git diff --stat=120 --end-of-options HEAD
      section "NAME-STATUS (uncommitted)"
      git diff --name-status -M --end-of-options HEAD
      section "UNTRACKED"
      git ls-files --others --exclude-standard
      section "PATCH (uncommitted)"
      git diff -M --no-color --end-of-options HEAD
      ;;
  esac
} > "$out"

echo "wrote $out ($(wc -l < "$out" | tr -d ' ') lines)"
