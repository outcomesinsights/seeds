#!/usr/bin/env bash
# Configure branch protection for main branch.
# Run once after creating the GitHub repo.
#
# Usage: ./scripts/setup-branch-protection.sh owner/repo

set -euo pipefail

REPO="${1:?Usage: $0 owner/repo}"

gh api -X PUT "repos/${REPO}/branches/main/protection" \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint", "test (3.9)", "test (3.10)", "test (3.11)", "test (3.12)", "test (3.13)"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
EOF

echo "Branch protection configured for ${REPO}:main"
echo "Required checks: lint + test matrix (3.9–3.13)"
