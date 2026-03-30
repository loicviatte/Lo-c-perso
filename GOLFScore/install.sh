#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Golf Scorecard – DaVinci Resolve installer (macOS)
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DR_SCRIPTS="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp"

echo "Golf Scorecard Installer"
echo "========================"
echo ""

if [ ! -d "$DR_SCRIPTS" ]; then
    echo "Creating DaVinci Resolve Scripts/Comp folder..."
    mkdir -p "$DR_SCRIPTS"
fi

echo "Installing GolfScorecard.py → $DR_SCRIPTS"
cp "$SCRIPT_DIR/GolfScorecard.py" "$DR_SCRIPTS/GolfScorecard.py"

echo ""
echo "✓ Installation complete."
echo ""
echo "How to use:"
echo "  1. Open DaVinci Resolve 20.3"
echo "  2. Go to: Workspace → Scripts → GolfScorecard"
echo "  3. The dashboard window will open"
echo ""
echo "To uninstall:"
echo "  rm \"$DR_SCRIPTS/GolfScorecard.py\""
