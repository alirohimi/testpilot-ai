#!/bin/bash
# Deploy static site to GitHub Pages (gh-pages branch)
# Uses fresh clone approach to avoid worktree conflicts

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
WEB_DIR="$REPO_ROOT/web"
TMP_DIR=$(mktemp -d)
BRANCH="gh-pages"

echo "=== Deploying to GitHub Pages ==="
echo "Web source: $WEB_DIR"

# Clone gh-pages branch fresh
rm -rf "$TMP_DIR"
git clone --branch gh-pages --single-branch \
    "https://github.com/alirohimi/testpilot-ai.git" "$TMP_DIR" 2>/dev/null || {
    echo "Cloning failed, trying with origin main as fallback..."
    git clone --branch gh-pages --single-branch \
        "https://github.com/alirohimi/testpilot-ai.git" "$TMP_DIR"
}

# Copy static assets to root (overwrite everything)
rm -rf "$TMP_DIR"/*
cp -r "$WEB_DIR/landing/"* "$TMP_DIR/"
cp -r "$WEB_DIR/ui/"* "$TMP_DIR/"

# Configure git
cd "$TMP_DIR"
git config user.email "agent@hermes.ai"
git config user.name "Hermes Agent"

# Check if there are changes
CHANGED=false
for f in index.html auth.html dashboard.html; do
    if ! diff -q "$REPO_ROOT/web/$f" "$TMP_DIR/$f" > /dev/null 2>&1; then
        CHANGED=true
        break
    fi
done

if [ "$CHANGED" = false ]; then
    echo "No changes detected."
    rm -rf "$TMP_DIR"
    exit 0
fi

# Commit and push
git add -A
git status
git commit -m "chore: deploy static HTML pages to GitHub Pages

- Landing page: index.html (light theme)
- Auth page: auth.html (login/register with API key flow)
- Dashboard: dashboard.html (key management UI)"

echo "Pushing to origin/$BRANCH..."
git push origin "$BRANCH"

echo ""
echo "=== ✅ Deployed! ==="
echo ""
echo "Preview URLs:"
echo "  Landing:    https://alirohimi.github.io/testpilot-ai/"
echo "  Auth:       https://alirohimi.github.io/testpilot-ai/auth.html"
echo "  Dashboard:  https://alirohimi.github.io/testpilot-ai/dashboard.html"

rm -rf "$TMP_DIR"
