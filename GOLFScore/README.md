# Golf Scorecard – DaVinci Resolve Plugin

A Python script plugin for DaVinci Resolve 20.3 that creates animated golf scorecard overlays directly in the timeline.

## Requirements

- DaVinci Resolve 20.3 (free or Studio)
- macOS

## Installation

```bash
cd /Users/loicp/Documents/Claude/Projects/GOLFScore
./install.sh
```

This copies `GolfScorecard.py` to:
`~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/`

## How to use

1. Open DaVinci Resolve and open a project with a timeline
2. Go to **Workspace → Scripts → GolfScorecard**
3. The dashboard window opens

### Dashboard workflow

1. **Player Name** – enter the player's name (shown on every scorecard)
2. **+ Add Hole** – adds a hole card with:
   - PAR (3–6)
   - Distance in yards
   - Number of strokes the player took
3. For each hole, one button appears per stroke:
   - **Stroke N → Insert at Playhead** — click to place the scorecard overlay at the current playhead position in the timeline
   - The last stroke is marked with ★ and triggers the score animation

### Scorecard layout

```
┌──────────────────────────────────────────────┐
│  7  │  TIGER WOODS                      +1   │
│387yds│  1   2  [3]  4                        │
└──────────────────────────────────────────────┘
```

- **Left** — Hole number (large) + distance in yards
- **Centre** — Player name + stroke indicators (active stroke in cyan)
- **Right** — Score relative to par: `E`, `+1`, `-2`, etc.
- **Position** — Top-right corner of the frame

### Score animation (last stroke)

On the final stroke clip of each hole, the score number counts up/down to the new value over ~30 frames to signal hole completion.

### Tips

- Each clip = 1 stroke — place it above your video footage on a higher video track
- Default clip duration is 7 seconds — trim as needed in the timeline
- Add your own fade in/out transitions on the clip

## File structure

```
GOLFScore/
├── GolfScorecard.py    # Main plugin script
├── install.sh          # Installer
└── README.md           # This file
```

## Uninstall

```bash
rm ~/Library/Application\ Support/Blackmagic\ Design/DaVinci\ Resolve/Fusion/Scripts/Comp/GolfScorecard.py
```
