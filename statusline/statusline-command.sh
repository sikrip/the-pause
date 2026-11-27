#!/usr/bin/env bash
# Claude Code statusLine command
# Reads session JSON from stdin and prints a one-line status string:
#   <model>  <dir> (<branch>)  ctx:<tokens>
# Needs jq and bc.

input=$(cat)

# --- model display name ---
model=$(echo "$input" | jq -r '.model.display_name // "unknown model"')

# --- current directory (basename) ---
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')
dir=$(basename "$cwd")

# --- git branch (empty outside a repo or on a detached HEAD; skips locks) ---
branch=$(git -C "$cwd" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null)

# --- context window: absolute tokens in current context ---
# current_usage.input_tokens is the number of tokens actually sent in the last
# API call's context (includes cache reads). Use this as the "live context" figure.
# Falls back to deriving from used_percentage * window_size if current_usage is null.
ctx_tokens=$(echo "$input" | jq -r '
  if .context_window.current_usage != null then
    ( .context_window.current_usage.input_tokens
    + .context_window.current_usage.cache_read_input_tokens )
  elif .context_window.used_percentage != null then
    ( .context_window.used_percentage / 100
    * .context_window.context_window_size )
    | floor
  else
    empty
  end
')

# Format with k/M suffix
format_tokens() {
  local n=$1
  if   [ "$n" -ge 1000000 ]; then
    printf "%.1fM" "$(echo "scale=2; $n / 1000000" | bc)"
  elif [ "$n" -ge 1000 ]; then
    printf "%.1fk" "$(echo "scale=1; $n / 1000" | bc)"
  else
    printf "%d" "$n"
  fi
}

# --- assemble ---
branch_str=""
[ -n "$branch" ] && branch_str=" ($branch)"

ctx_str=""
if [ -n "$ctx_tokens" ]; then
  ctx_str="  ctx:$(format_tokens "$ctx_tokens")"
fi

printf "%s  %s%s%s\n" "$model" "$dir" "$branch_str" "$ctx_str"
