#!/usr/bin/env bash
# Claude Code status line script
# Reads JSON from stdin and outputs a formatted status line

set -euo pipefail

# ── Colors ───────────────────────────────────────────────────────────
readonly RST='\033[0m'
readonly RED='\033[0;31m'
readonly GRN='\033[0;32m'
readonly YEL='\033[0;33m'
readonly BLU='\033[0;34m'
readonly MAG='\033[0;35m'
readonly CYN='\033[0;36m'
readonly WHT='\033[0;37m'
readonly GRY='\033[0;90m'

# ── Helpers ──────────────────────────────────────────────────────────

# Wrap text in a color.
paint() { printf "%b%s%b" "$1" "$2" "$RST"; }

# GRN < 50 ≤ YEL < 80 ≤ RED
threshold_color() {
  local n=${1%.*}
  if   (( n >= 80 )); then printf '%s' "$RED"
  elif (( n >= 50 )); then printf '%s' "$YEL"
  else                     printf '%s' "$GRN"
  fi
}

# Format seconds as "1d2h" / "3h4m" / "5m6s" / "7s".
format_duration() {
  local s=$1
  if   (( s >= 86400 )); then printf '%dd%dh' $((s/86400)) $((s%86400/3600))
  elif (( s >= 3600 ));  then printf '%dh%dm' $((s/3600))  $((s%3600/60))
  elif (( s >= 60 ));    then printf '%dm%ds' $((s/60))    $((s%60))
  else                        printf '%ds'    "$s"
  fi
}

# Build a rate-limit segment: " lim 5h:67% 2h0m" with split colors.
build_limit_part() {
  local rate=$1 resets=$2 label=$3
  [[ -z "$rate" ]] && return
  local rounded suffix="" remaining color
  rounded=$(printf '%.0f' "$rate")
  color=$(threshold_color "$rounded")
  if [[ -n "$resets" ]]; then
    remaining=$(( resets - $(date +%s) ))
    (( remaining > 0 )) && suffix=" $(paint "$WHT" "$(format_duration "$remaining")")"
  fi
  printf ' %s %s%s' \
    "$(paint "$GRY" "lim")" \
    "$(paint "$color" "${label}:${rounded}%")" \
    "$suffix"
}

# ── Input ────────────────────────────────────────────────────────────
input=$(cat)

{
  read -r model
  read -r cwd
  read -r used_pct
  read -r total_cost
  read -r duration_ms
  read -r lines_add
  read -r lines_rm
  read -r rate_5h
  read -r resets_5h
  read -r rate_7d
  read -r resets_7d
} < <(
  jq -r '
    .model.display_name                    // "Unknown model",
    .workspace.current_dir // .cwd         // "",
    .context_window.used_percentage        // "",
    .cost.total_cost_usd                   // "",
    .cost.total_duration_ms                // "",
    .cost.total_lines_added                // "",
    .cost.total_lines_removed              // "",
    .rate_limits.five_hour.used_percentage // "",
    .rate_limits.five_hour.resets_at       // "",
    .rate_limits.seven_day.used_percentage // "",
    .rate_limits.seven_day.resets_at       // ""
  ' <<<"$input"
)

short_cwd="${cwd/#$HOME/~}"

# ── Git info (skip lock to avoid blocking) ───────────────────────────
branch=""
dirty=""
if [[ -n "$cwd" ]] && git -C "$cwd" rev-parse --git-dir &>/dev/null; then
  branch=$(git -C "$cwd" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null || true)
  if [[ -n $(git -C "$cwd" --no-optional-locks status --porcelain 2>/dev/null) ]]; then
    dirty="●"
  fi
fi

# ── Build parts ──────────────────────────────────────────────────────

# Context usage — threshold color
ctx_part=""
if [[ -n "$used_pct" ]]; then
  ctx_part=" $(paint "$(threshold_color "$used_pct")" "ctx:${used_pct}%")"
fi

# Rate-limit windows — threshold color, rounded, with reset countdown
limit_5h_part=$(build_limit_part "$rate_5h" "$resets_5h" "5h")
limit_7d_part=$(build_limit_part "$rate_7d" "$resets_7d" "7d")

# Session duration — WHT
duration_part=""
if [[ -n "$duration_ms" ]]; then
  duration_part=" $(paint "$WHT" "dur:$(format_duration $((duration_ms/1000)))")"
fi

# Cost — YEL
cost_part=""
if [[ -n "$total_cost" ]]; then
  cost_part=" $(paint "$YEL" "$(printf '$%.2f' "$total_cost")")"
fi

# Lines changed — GRN/RED (conventional diff colors)
lines_part=""
if [[ -n "$lines_add" && -n "$lines_rm" ]] && (( lines_add + lines_rm > 0 )); then
  lines_part=" $(paint "$GRN" "+${lines_add}")/$(paint "$RED" "-${lines_rm}")"
fi

# Branch + dirty — CYN / RED dot
branch_part=""
if [[ -n "$branch" ]]; then
  branch_part=" $(paint "$CYN" "⎇ ${branch}")"
  [[ -n "$dirty" ]] && branch_part+="$(paint "$RED" "$dirty")"
fi

# ── Output ───────────────────────────────────────────────────────────
# model  ctx  5h  7d  dur  cost  lines  cwd  branch
printf "%b%s%s%s%s%s%s  %b%s" \
  "$(paint "$MAG" "$model")" \
  "$ctx_part" \
  "$limit_5h_part" \
  "$limit_7d_part" \
  "$duration_part" \
  "$cost_part" \
  "$lines_part" \
  "$(paint "$BLU" "$short_cwd")" \
  "$branch_part"
