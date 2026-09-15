#!/usr/bin/env bash
# Sync Obsidian vault skills -> Cursor / Claude Code / Codex agent skill paths
set -euo pipefail

VAULT_SKILLS="$(cd "$(dirname "$0")" && pwd)"
CURSOR_SKILLS="${HOME}/.cursor/skills"
CLAUDE_SKILLS="${HOME}/.claude/skills"
CODEX_SKILLS="${HOME}/.codex/skills"

link_skill() {
  local name="$1"
  local target_base="$2"
  local src="${VAULT_SKILLS}/${name}"
  local dest="${target_base}/${name}"

  if [[ ! -d "$src" ]]; then
    echo "skip: missing ${src}"
    return
  fi

  mkdir -p "$target_base"

  if [[ -L "$dest" ]]; then
    rm "$dest"
  elif [[ -d "$dest" ]]; then
    echo "warn: ${dest} is a real directory (not symlink). Backing up to ${dest}.bak"
    mv "$dest" "${dest}.bak.$(date +%Y%m%d%H%M%S)"
  elif [[ -e "$dest" ]]; then
    rm -f "$dest"
  fi

  ln -s "$src" "$dest"
  echo "linked: ${dest} -> ${src}"
}

echo "Vault skills: ${VAULT_SKILLS}"
for s in learn-tech-framework layered-tech-deep-dive leetcode-five-minute-read skill-confluence-markdown-upload \
         analyze-change-context define-capability-contract design-responsibility-architecture \
         define-development-task-contract code-implementation-spec plan-behavioral-validation \
         execute-contract-verification write-precise-process-description humanizer \
         process-logic-design diagram-authoring; do
  link_skill "$s" "$CURSOR_SKILLS"
  link_skill "$s" "$CLAUDE_SKILLS"
  link_skill "$s" "$CODEX_SKILLS"
done
echo "done."
