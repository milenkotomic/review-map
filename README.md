# review-map

A Claude Code skill that turns a diff into a map for the reviewer: what
changed and why, contract deltas, file footprint by role, the load-bearing
hunks with notes, and a severity-tagged risk read. Rendered as a styled HTML
page and opened in the browser. Everything runs locally; nothing is uploaded.

```
/review-map:review-map 215            # a PR number
/review-map:review-map feat/j2-api    # a branch, diffed against its merge base
/review-map:review-map abc123..def456 # a commit range
/review-map:review-map                # the current work unit (branch commits + working tree)
```

Installed as a plugin, the command is namespaced as `/review-map:review-map`.
With the symlink install below it is plain `/review-map`.

Flags: `--hunks N`, `--max-lines N`, `--force` (recap a tiny diff anyway),
`--md` (Markdown in chat instead of the page), `--artifact` (publish a
shareable claude.ai page).

## What you get

1. Title and a two-sentence brief
2. What changed and why
3. UI impact (only when rendered UI changed)
4. Contract changes: schema, API, config, permissions, with before/after
5. Open questions the author raised, each checked against the code
6. Footprint: changed files grouped by role (Contract, Logic, Wiring, Tests,
   Docs, Generated) with a handwritten-versus-generated split
7. Key changes: an index, then 3 to 8 hunks, notes first, code collapsed
8. Review notes tagged Blocker / Should fix / Consider / FYI, blockers first
9. Excluded: what was left out and why

The structured parts (file list, flags, field names, routes, before/after
code) are copied from the real diff. Only the prose is the model's.

## Install

Requires Claude Code, `git`, `gh` (for PR mode) and Python 3.

The plugin is published through my plugin marketplace,
[milenkotomic/claude-plugins](https://github.com/milenkotomic/claude-plugins).
From a shell:

```sh
claude plugin marketplace add milenkotomic/claude-plugins
claude plugin install review-map@milenkotomic
```

Or inside Claude Code: `/plugin marketplace add milenkotomic/claude-plugins`,
then `/plugin install review-map@milenkotomic`. Start a new session and type
`/review-map:review-map`.

### Update

```sh
claude plugin marketplace update milenkotomic
claude plugin update review-map@milenkotomic
```

Restart Claude Code afterwards. The plugin runs from a cached copy, so
changes pushed to this repo reach you only through an update.

### Developing the skill

To edit the skill and see changes without a push and update, use the symlink
install instead:

```sh
git clone https://github.com/milenkotomic/review-map.git ~/Developer/review-map
~/Developer/review-map/install.sh
```

It links `skills/review-map` into `~/.claude/skills/`, so the command is
`/review-map` and edits take effect in the next session. Use one install
method per machine, not both: uninstall the plugin first
(`claude plugin uninstall review-map@milenkotomic`), or remove the
`~/.claude/skills/review-map` link before installing the plugin.

## Configure

The Defaults table at the top of `skills/review-map/SKILL.md` controls hunk
count, hunk length, total length, the tiny-diff threshold and the output
mode. Edit it there.

Colors and type live in the `:root` blocks of `skills/review-map/scripts/render.py`.
The shipped stylesheet follows the Milenko Tomic brand book (Cobalt, Ink,
Paper, Wire; Geist and JetBrains Mono; light and dark). Swap the raw tokens
for your own and nothing else needs to change.

## Layout

```
skills/review-map/
  SKILL.md                 the skill
  scripts/collect-diff.sh  gathers PR / branch / range / working-tree diffs into one bundle
  scripts/render.py        Markdown to styled, sanitized HTML, no dependencies beyond Python 3
  scripts/vendor/          marked.js 12.0.2 and DOMPurify 3.1.6, inlined into every page
  evals/                   test cases for `claude plugin eval` and the skill-creator loop
install.sh                 symlink install for developing the skill
.claude-plugin/            plugin.json
```

## Credits

The idea of a "reverse plan" built from a diff, and the discipline of
deriving structured blocks mechanically from the diff while the model writes
only prose, come from BuilderIO's
[visual-recap](https://github.com/BuilderIO/skills/tree/main/skills/visual-recap)
skill (MIT). This is an independent rewrite with no hosted dependency; no
text was copied.

Vendored, unmodified, with their license headers intact:
[marked](https://github.com/markedjs/marked) (MIT) and
[DOMPurify](https://github.com/cure53/DOMPurify) (Apache 2.0 or MPL 2.0).
Both match the cdnjs SRI hashes for their versions.

## License

MIT, see [LICENSE](LICENSE).
