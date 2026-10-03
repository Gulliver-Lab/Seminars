#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_TOKEN:?Set GITHUB_TOKEN to a fine-grained token for Gulliver-Lab/Seminars}"

calendar_url="${CALENDAR_URL:-https://swift.gulliver.espci.fr/seminars/calendar.ics}"
repository="Gulliver-Lab/Seminars"

ics_base64="$({ curl --fail --silent --show-error --location "$calendar_url"; } | base64 | tr -d '\n')"
payload="$(jq -n --arg ics_base64 "$ics_base64" '{
  event_type: "publish-calendar",
  client_payload: {ics_base64: $ics_base64}
}')"

if [ "${#ics_base64}" -ge 65000 ]; then
  echo "Calendar feed is too large for a repository_dispatch payload." >&2
  exit 1
fi

curl --fail --silent --show-error --location \
  --request POST \
  --header "Accept: application/vnd.github+json" \
  --header "Authorization: Bearer $GITHUB_TOKEN" \
  --header "X-GitHub-Api-Version: 2026-03-10" \
  --header "Content-Type: application/json" \
  --data "$payload" \
  "https://api.github.com/repos/$repository/dispatches"

echo "Calendar publication requested. Check the Actions tab for deployment status."
