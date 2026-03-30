#!/bin/bash
# Golf Scorecard – DaVinci Resolve installer (macOS)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts"

echo "Golf Scorecard Installer"
echo "========================"
echo ""

mkdir -p "$BASE/Utility" "$BASE/Edit"

cp "$SCRIPT_DIR/GolfScorecard.py" "$BASE/Utility/GolfScorecard.py"
cp "$SCRIPT_DIR/GolfScorecard.py" "$BASE/Edit/GolfScorecard.py"

echo "✓ Installed to Utility and Edit script folders."
echo ""
echo "In DaVinci Resolve:"
echo "  • Edit page  → Workspace > Scripts > Edit > GolfScorecard"
echo "  • Any page   → Workspace > Scripts > Utility > GolfScorecard"
echo ""
echo "TIP: open a project with a timeline BEFORE clicking Insert at Playhead."
