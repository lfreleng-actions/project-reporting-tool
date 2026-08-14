#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

set -euo pipefail

# Generate index.html for GitHub Pages
# Usage: generate-index.sh <report_dir> [environment]
#   report_dir: Directory containing reports (e.g., "." for root or "previews/123")
#   environment: "production" or "previews" (default: production)

REPORT_DIR="${1:-.}"
ENVIRONMENT="${2:-production}"

# Reports regenerate daily. A report older than this many days means
# the project's most recent run produced nothing, leaving the previous
# run's output in place. Without a marker that stale output presents
# itself as current.
STALE_THRESHOLD_DAYS="${STALE_THRESHOLD_DAYS:-2}"

# Guard the override: a non-numeric value would abort the whole script
# at the -ge comparison below (set -e), taking index generation with
# it. A bad threshold must not cost us the index page.
if ! [[ "$STALE_THRESHOLD_DAYS" =~ ^[0-9]+$ ]]; then
  echo "⚠️  Ignoring invalid STALE_THRESHOLD_DAYS='${STALE_THRESHOLD_DAYS}', using 2"
  STALE_THRESHOLD_DAYS=2
fi

# Escape HTML metacharacters before interpolating a value into the
# generated markup. Project names legitimately contain ampersands
# ("R&D"), which would otherwise emit a broken entity, and this keeps
# metadata from being able to inject markup into the published index.
#
# Deliberately uses sed rather than ${var//pat/repl}: bash 5.2 enables
# patsub_replacement by default, under which an unescaped & in the
# replacement expands to the matched text, so "${s//</&lt;}" yields
# "<lt;" on the runners but "&lt;" on older bash. sed's & has the same
# meaning but is escaped explicitly below, giving one behaviour
# everywhere. Ampersand is substituted first so that it cannot
# re-escape the entities introduced by the later expressions.
html_escape() {
  printf '%s' "$1" | sed \
    -e 's/&/\&amp;/g' \
    -e 's/</\&lt;/g' \
    -e 's/>/\&gt;/g' \
    -e 's/"/\&quot;/g'
}

# Convert an ISO-8601 UTC timestamp to epoch seconds. Tries GNU date
# (CI runners) then BSD date (local macOS development).
iso_to_epoch() {
  local ts="$1"
  date -u -d "$ts" +%s 2>/dev/null \
    || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$ts" +%s 2>/dev/null \
    || return 1
}

# Format an ISO-8601 timestamp for display, in UTC to match the label.
# Same GNU-then-BSD handling as above; falls back to the raw string so
# an unexpected format still renders something.
format_timestamp() {
  local ts="$1"
  date -u -d "$ts" "+%Y-%m-%d %H:%M UTC" 2>/dev/null \
    || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$ts" "+%Y-%m-%d %H:%M UTC" 2>/dev/null \
    || echo "$ts"
}

# Whole days between an ISO-8601 timestamp and now.
# Emits nothing when the timestamp is absent or cannot be parsed, so
# that an unreadable date is never mistaken for a fresh report.
report_age_days() {
  local ts="$1"
  local generated_epoch now_epoch
  if [ "$ts" = "N/A" ]; then
    return 0
  fi
  generated_epoch=$(iso_to_epoch "$ts") || return 0
  now_epoch=$(date -u +%s)
  echo $(( (now_epoch - generated_epoch) / 86400 ))
}

echo "📄 Generating index page for: $REPORT_DIR"

# Get repository name from environment or extract from URL
REPO_NAME="${GITHUB_REPOSITORY##*/}"
if [ -z "$REPO_NAME" ]; then
  REPO_NAME="project-reporting-tool"
fi

# Determine the base path for links
if [ "$ENVIRONMENT" = "previews" ]; then
  # Preview environment: /project-reporting-tool/previews/6
  BASE_PATH="/${REPO_NAME}/${REPORT_DIR}"
  PAGE_TITLE="Report Preview"
  PAGE_SUBTITLE="Preview reports for changes under review"
else
  # Production at root: /project-reporting-tool/
  BASE_PATH="/${REPO_NAME}"
  PAGE_TITLE="Production Reports"
  PAGE_SUBTITLE="Linux Foundation Project Reports"
fi

# Find all report.html files
REPORTS=()
if [ "$REPORT_DIR" = "." ]; then
  # Root level: find project directories with report.html
  # Exclude previews/ directory and any hidden directories
  while IFS= read -r -d '' report_file; do
    project_dir=$(dirname "$report_file")
    project_slug=$(basename "$project_dir")

    # Skip if this is under previews/
    if [[ "$project_dir" == previews/* ]] || [[ "$project_dir" == ./previews/* ]]; then
      continue
    fi

    # Skip if this is a hidden directory
    if [[ "$project_slug" == .* ]]; then
      continue
    fi

    # Get project name from metadata if available
    project_name="$project_slug"
    metadata_file="$project_dir/metadata.json"
    if [ -f "$metadata_file" ]; then
      project_name=$(jq -r --arg slug "$project_slug" '.project // $slug' "$metadata_file")
      generated_at=$(jq -r '.generated_at // "N/A"' "$metadata_file")
    else
      generated_at="N/A"
    fi

    REPORTS+=("$project_slug|$project_name|$generated_at|$(report_age_days "$generated_at")")
  done < <(find . -maxdepth 2 -name "report.html" -print0)
elif [ -d "$REPORT_DIR" ]; then
  # Subdirectory (like previews/6): find all reports under it
  while IFS= read -r -d '' report_file; do
    project_dir=$(dirname "$report_file")
    project_slug=$(basename "$project_dir")

    # Get project name from metadata if available
    project_name="$project_slug"
    metadata_file="$project_dir/metadata.json"
    if [ -f "$metadata_file" ]; then
      project_name=$(jq -r --arg slug "$project_slug" '.project // $slug' "$metadata_file")
      generated_at=$(jq -r '.generated_at // "N/A"' "$metadata_file")
    else
      generated_at="N/A"
    fi

    REPORTS+=("$project_slug|$project_name|$generated_at|$(report_age_days "$generated_at")")
  done < <(find "$REPORT_DIR" -name "report.html" -print0)
fi

report_count=${#REPORTS[@]}
echo "Found $report_count report(s)"

# Determine output file location
if [ "$REPORT_DIR" = "." ]; then
  INDEX_FILE="index.html"
else
  INDEX_FILE="$REPORT_DIR/index.html"
fi

# Generate HTML
cat > "$INDEX_FILE" <<'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PAGE_TITLE_PLACEHOLDER - Linux Foundation Reports</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                   'Helvetica Neue', Arial, sans-serif;
      line-height: 1.6;
      color: #333;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      padding: 2rem 1rem;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
    }

    header {
      background: white;
      border-radius: 12px;
      padding: 2rem;
      margin-bottom: 2rem;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    h1 {
      font-size: 2.5rem;
      margin-bottom: 0.5rem;
      color: #2d3748;
    }

    .subtitle {
      font-size: 1.1rem;
      color: #718096;
      margin-bottom: 1rem;
    }

    .meta {
      display: flex;
      gap: 2rem;
      flex-wrap: wrap;
      font-size: 0.9rem;
      color: #718096;
      padding-top: 1rem;
      border-top: 1px solid #e2e8f0;
    }

    .meta-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .meta-icon {
      font-size: 1.2rem;
    }

    main {
      background: white;
      border-radius: 12px;
      padding: 2rem;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .reports-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
      border-bottom: 2px solid #e2e8f0;
    }

    .reports-title {
      font-size: 1.5rem;
      color: #2d3748;
    }

    .report-count {
      background: #667eea;
      color: white;
      padding: 0.5rem 1rem;
      border-radius: 20px;
      font-weight: 600;
    }

    .reports-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1.5rem;
    }

    .report-card {
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 1.5rem;
      transition: all 0.3s ease;
      background: #fafafa;
    }

    .report-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 16px rgba(102, 126, 234, 0.2);
      border-color: #667eea;
    }

    .report-card.stale {
      border-color: #d69e2e;
      background: #fffaf0;
    }

    .stale-badge {
      display: inline-block;
      font-size: 0.7rem;
      font-weight: 600;
      color: #975a16;
      background: #faf089;
      border-radius: 4px;
      padding: 0.1rem 0.4rem;
      margin-left: 0.5rem;
      vertical-align: middle;
    }

    .stale-note {
      font-size: 0.8rem;
      line-height: 1.4;
      color: #975a16;
      margin-bottom: 1rem;
    }

    .report-name {
      font-size: 1.25rem;
      font-weight: 600;
      color: #2d3748;
      margin-bottom: 0.5rem;
    }

    .report-info {
      font-size: 0.85rem;
      color: #718096;
      margin-bottom: 1rem;
    }

    .report-links {
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 500;
      font-size: 0.9rem;
      transition: all 0.2s ease;
    }

    .btn-primary {
      background: #667eea;
      color: white;
    }

    .btn-primary:hover {
      background: #5568d3;
      transform: translateY(-1px);
    }

    .btn-secondary {
      background: #e2e8f0;
      color: #4a5568;
    }

    .btn-secondary:hover {
      background: #cbd5e0;
    }

    .empty-state {
      text-align: center;
      padding: 4rem 2rem;
      color: #718096;
    }

    .empty-state-icon {
      font-size: 4rem;
      margin-bottom: 1rem;
    }

    footer {
      text-align: center;
      padding: 2rem;
      color: white;
      margin-top: 2rem;
    }

    footer a {
      color: white;
      text-decoration: underline;
    }

    @media (max-width: 768px) {
      h1 {
        font-size: 2rem;
      }

      .reports-grid {
        grid-template-columns: 1fr;
      }

      .meta {
        flex-direction: column;
        gap: 0.5rem;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>📊 PAGE_TITLE_PLACEHOLDER</h1>
      <p class="subtitle">PAGE_SUBTITLE_PLACEHOLDER</p>
      <div class="meta">
        <div class="meta-item">
          <span class="meta-icon">🕐</span>
          <span>Generated: GENERATED_TIMESTAMP_PLACEHOLDER</span>
        </div>
        <div class="meta-item">
          <span class="meta-icon">🏢</span>
          <span>Linux Foundation</span>
        </div>
        <div class="meta-item">
          <span class="meta-icon">🔄</span>
          <span>ENVIRONMENT_BADGE_PLACEHOLDER</span>
        </div>
      </div>
    </header>

    <main>
      <div class="reports-header">
        <h2 class="reports-title">Available Reports</h2>
        <span class="report-count">REPORT_COUNT_PLACEHOLDER reports</span>
      </div>

      REPORTS_CONTENT_PLACEHOLDER
    </main>

    <footer>
      <p>
        Generated by
        <a href="https://github.com/lfreleng-actions/project-reporting-tool" target="_blank">
          Linux Foundation Reporting Tool
        </a>
      </p>
      <p style="margin-top: 0.5rem; font-size: 0.9rem;">
        &copy; 2025 The Linux Foundation | Apache-2.0 License
      </p>
    </footer>
  </div>
</body>
</html>
HTMLEOF

# Generate reports HTML content
if [ "$report_count" -eq 0 ]; then
  REPORTS_HTML='
      <div class="empty-state">
        <div class="empty-state-icon">📭</div>
        <h3>No Reports Available</h3>
        <p>Reports will appear here once they are generated.</p>
      </div>'
else
  REPORTS_HTML='<div class="reports-grid">'

  for report_entry in "${REPORTS[@]}"; do
    IFS='|' read -r slug name timestamp age_days <<< "$report_entry"

    # Format timestamp for display. The label claims UTC, so force the
    # conversion to UTC rather than relying on the runner's timezone.
    if [ "$timestamp" = "N/A" ]; then
      display_time="N/A"
    else
      display_time=$(format_timestamp "$timestamp")
    fi

    # Flag reports whose most recent run produced no output. The
    # previous run's report survives on the branch and would otherwise
    # present itself as current.
    card_class="report-card"
    stale_badge=""
    stale_note=""
    if [ -n "$age_days" ] && [ "$age_days" -ge "$STALE_THRESHOLD_DAYS" ]; then
      if [ "$age_days" -eq 1 ]; then
        day_label="day"
      else
        day_label="days"
      fi
      card_class="report-card stale"
      stale_badge=" <span class=\"stale-badge\">⚠️ STALE</span>"
      stale_note="<div class=\"stale-note\">⚠️ Generated ${age_days} ${day_label} ago. Recent runs produced no report for this project, so the data below is out of date.</div>"
    fi

    # Escape every metadata-derived value before it reaches the markup.
    name_esc=$(html_escape "$name")
    slug_esc=$(html_escape "$slug")
    display_time_esc=$(html_escape "$display_time")

    REPORTS_HTML+="
        <div class=\"$card_class\">
          <div class=\"report-name\">$name_esc$stale_badge</div>
          <div class=\"report-info\">
            <div>🔖 Slug: <code>$slug_esc</code></div>
            <div>📅 Generated: $display_time_esc</div>
          </div>
          $stale_note
          <div class=\"report-links\">
            <a href=\"$BASE_PATH/$slug_esc/report.html\" class=\"btn btn-primary\">
              📊 View Report
            </a>
            <a href=\"$BASE_PATH/$slug_esc/report_raw.json\" class=\"btn btn-secondary\">
              📄 JSON
            </a>
          </div>
        </div>"
  done

  REPORTS_HTML+='
      </div>'
fi

# Determine environment badge
if [ "$ENVIRONMENT" = "previews" ]; then
  ENV_BADGE="Preview Environment"
else
  ENV_BADGE="Production Environment"
fi

# Get current timestamp
CURRENT_TIME=$(date -u +"%Y-%m-%d %H:%M UTC")

# Debug output
echo "DEBUG: PAGE_TITLE='$PAGE_TITLE'"
echo "DEBUG: PAGE_SUBTITLE='$PAGE_SUBTITLE'"
echo "DEBUG: CURRENT_TIME='$CURRENT_TIME'"
echo "DEBUG: ENV_BADGE='$ENV_BADGE'"
echo "DEBUG: report_count='$report_count'"

# Create a safe temporary file
TMP_FILE=$(mktemp)
TMP_FILE2=$(mktemp)

echo "DEBUG: TMP_FILE='$TMP_FILE'"
echo "DEBUG: TMP_FILE2='$TMP_FILE2'"
echo "DEBUG: Source file='$REPORT_DIR/index.html'"

# Verify source file exists
if [ ! -f "$REPORT_DIR/index.html" ]; then
  echo "ERROR: Source file $REPORT_DIR/index.html does not exist!"
  exit 1
fi

# Copy the template to temp file
cp "$REPORT_DIR/index.html" "$TMP_FILE"

# Verify copy succeeded
if [ ! -s "$TMP_FILE" ]; then
  echo "ERROR: Failed to copy template to temp file or file is empty!"
  ls -lah "$REPORT_DIR/index.html"
  ls -lah "$TMP_FILE"
  exit 1
fi

echo "DEBUG: Source file size: $(wc -c < "$REPORT_DIR/index.html") bytes"
echo "DEBUG: Temp file size: $(wc -c < "$TMP_FILE") bytes"

# Replace placeholders one at a time with proper escaping
# Escape special characters that could break sed
PAGE_TITLE_ESC=$(printf '%s' "$PAGE_TITLE" | sed 's/[&/\]/\\&/g; s/|/\\|/g')
PAGE_SUBTITLE_ESC=$(printf '%s' "$PAGE_SUBTITLE" | sed 's/[&/\]/\\&/g; s/|/\\|/g')
CURRENT_TIME_ESC=$(printf '%s' "$CURRENT_TIME" | sed 's/[&/\]/\\&/g; s/|/\\|/g')
ENV_BADGE_ESC=$(printf '%s' "$ENV_BADGE" | sed 's/[&/\]/\\&/g; s/|/\\|/g')

echo "DEBUG: PAGE_TITLE_ESC='$PAGE_TITLE_ESC'"
echo "DEBUG: PAGE_SUBTITLE_ESC='$PAGE_SUBTITLE_ESC'"
echo "DEBUG: CURRENT_TIME_ESC='$CURRENT_TIME_ESC'"
echo "DEBUG: ENV_BADGE_ESC='$ENV_BADGE_ESC'"

# Replace each placeholder (use unique placeholder names to avoid substring conflicts)
echo "DEBUG: Running sed command 1..."
sed "s|PAGE_TITLE_PLACEHOLDER|${PAGE_TITLE_ESC}|g" "$TMP_FILE" > "$TMP_FILE2" || {
  echo "ERROR: sed command 1 failed with exit code $?"
  echo "DEBUG: Command was: sed \"s|PAGE_TITLE_PLACEHOLDER|\${PAGE_TITLE_ESC}|g\" \"$TMP_FILE\""
  exit 1
}

echo "DEBUG: Running sed command 2..."
sed "s|PAGE_SUBTITLE_PLACEHOLDER|${PAGE_SUBTITLE_ESC}|g" "$TMP_FILE2" > "$TMP_FILE" || {
  echo "ERROR: sed command 2 failed"
  exit 1
}

echo "DEBUG: Running sed command 3..."
sed "s|GENERATED_TIMESTAMP_PLACEHOLDER|${CURRENT_TIME_ESC}|g" "$TMP_FILE" > "$TMP_FILE2" || {
  echo "ERROR: sed command 3 failed"
  exit 1
}

echo "DEBUG: Running sed command 4..."
sed "s|ENVIRONMENT_BADGE_PLACEHOLDER|${ENV_BADGE_ESC}|g" "$TMP_FILE2" > "$TMP_FILE" || {
  echo "ERROR: sed command 4 failed"
  exit 1
}

echo "DEBUG: Running sed command 5..."
sed "s|REPORT_COUNT_PLACEHOLDER|${report_count}|g" "$TMP_FILE" > "$TMP_FILE2" || {
  echo "ERROR: sed command 5 failed"
  exit 1
}

# Replace the REPORTS_CONTENT_PLACEHOLDER using awk for better handling of multiline content
awk -v reports="$REPORTS_HTML" '{
  if ($0 ~ /REPORTS_CONTENT_PLACEHOLDER/) {
    print reports
  } else {
    print $0
  }
}' "$TMP_FILE2" > "$REPORT_DIR/index.html"

# Clean up temp files
rm -f "$TMP_FILE" "$TMP_FILE2"

echo "✅ Index page generated: $INDEX_FILE"

# Skip creating separate root landing page since production IS at root
echo "✅ Index generation complete"
