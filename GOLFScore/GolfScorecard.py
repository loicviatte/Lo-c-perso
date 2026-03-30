"""
Golf Scorecard Plugin for DaVinci Resolve 20.3
-----------------------------------------------
Run from: Workspace > Scripts > GolfScorecard

Dashboard lets you:
- Set player name
- Add holes (hole #, PAR, distance, stroke count)
- Insert a Fusion comp overlay per stroke at the playhead
"""

import sys

# ── DaVinci Resolve API bootstrap ────────────────────────────────────────────
try:
    import DaVinciResolveScript as dvr_script
    resolve = dvr_script.scriptapp("Resolve")
except ImportError:
    # Running inside DR's built-in Python interpreter
    resolve = bmd.scriptapp("Resolve")  # noqa: F821  (bmd is DR's global)

if resolve is None:
    print("ERROR: Could not connect to DaVinci Resolve.")
    sys.exit(1)

fusion  = resolve.Fusion()
ui      = fusion.UIManager
disp    = bmd.UIDispatcher(ui)  # noqa: F821

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY       = 0xFF1A2B4A
WHITE      = 0xFFFFFFFF
CYAN       = 0xFF4DD0E1
DARK_PANEL = 0xFF1E1E2E
MID_PANEL  = 0xFF2A2A3E
BTN_GREEN  = 0xFF2E7D32
BTN_RED    = 0xFFC62828
BTN_BLUE   = 0xFF1565C0

# ── State ─────────────────────────────────────────────────────────────────────
state = {
    "player": "",
    "holes":  [],       # list of { number, par, distance, strokes }
}

# ── Score helpers ─────────────────────────────────────────────────────────────
def calc_score_str(strokes_total, par_total):
    diff = strokes_total - par_total
    if diff == 0:  return "E"
    if diff > 0:   return f"+{diff}"
    return str(diff)

def cumulative_score_before(hole_index):
    """Score relative to par through all holes BEFORE hole_index."""
    total_s = sum(h["strokes"] for h in state["holes"][:hole_index])
    total_p = sum(h["par"]     for h in state["holes"][:hole_index])
    return calc_score_str(total_s, total_p)

def cumulative_score_after(hole_index):
    """Score relative to par AFTER hole_index is completed."""
    total_s = sum(h["strokes"] for h in state["holes"][:hole_index + 1])
    total_p = sum(h["par"]     for h in state["holes"][:hole_index + 1])
    return calc_score_str(total_s, total_p)

def score_to_int(score_str):
    if score_str == "E": return 0
    return int(score_str.replace("+", ""))

# ── Fusion scorecard builder ───────────────────────────────────────────────────
def build_stroke_string(total_strokes, current_stroke):
    """
    Returns a styled RTF-like string for DR Text+.
    Current stroke number will be highlighted via a separate Text+ node.
    Returns plain list of stroke numbers and the index to highlight.
    """
    return list(range(1, total_strokes + 1)), current_stroke

def insert_scorecard(hole_idx, stroke_num):
    """Creates a Fusion comp overlay and inserts it at the current playhead."""
    project  = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()

    if timeline is None:
        disp.ShowWarning("No active timeline found. Please open a timeline first.")
        return

    hole         = state["holes"][hole_idx]
    player       = state["player"] or "PLAYER"
    total_strokes= hole["strokes"]
    is_last      = (stroke_num == total_strokes)
    score_before = cumulative_score_before(hole_idx)
    score_after  = cumulative_score_after(hole_idx)

    # Create a new Fusion comp in the Media Pool
    media_pool = project.GetMediaPool()
    comp_name  = f"Scorecard_H{hole['number']}_S{stroke_num}"

    # Add a Fusion title clip to the timeline at the playhead
    playhead_frame = timeline.GetCurrentTimecode()  # timecode string
    fps            = float(timeline.GetSetting("timelineFrameRate"))
    duration_frames= int(fps * 7)  # default 7-second clip

    # We insert a Fusion Clip (blank) then populate its Fusion comp
    success = _create_and_insert_fusion_comp(
        timeline, media_pool, comp_name,
        hole, player, stroke_num, total_strokes,
        score_before, score_after, is_last, duration_frames, fps
    )

    if success:
        print(f"[GolfScorecard] Inserted: {comp_name}")
    else:
        print(f"[GolfScorecard] Failed to insert: {comp_name}")


def _create_and_insert_fusion_comp(
    timeline, media_pool, comp_name,
    hole, player, stroke_num, total_strokes,
    score_before, score_after, is_last,
    duration_frames, fps
):
    """
    Inserts a Fusion Title generator clip at the current playhead position
    and populates it with the scorecard nodes.
    """
    # Get current playhead position in frames
    tc      = timeline.GetCurrentTimecode()
    start_f = _tc_to_frames(tc, fps)
    end_f   = start_f + duration_frames - 1

    # Find or create video track 2
    track_count = timeline.GetTrackCount("video")
    if track_count < 2:
        timeline.AddTrack("video")

    # Insert Fusion Title generator
    # DaVinci Resolve 18+ supports InsertFusionTitleIntoTimeline
    inserted = timeline.InsertFusionTitleIntoTimeline(comp_name)

    if inserted is None:
        print("[GolfScorecard] InsertFusionTitleIntoTimeline not available, trying fallback.")
        return False

    # Get the Fusion comp attached to this clip and build nodes
    comp = inserted.GetFusionCompByIndex(1)
    if comp is None:
        print("[GolfScorecard] Could not access Fusion comp on inserted clip.")
        return False

    comp.Lock()
    try:
        _build_scorecard_nodes(
            comp, hole, player, stroke_num, total_strokes,
            score_before, score_after, is_last, duration_frames, fps
        )
    finally:
        comp.Unlock()

    return True


def _build_scorecard_nodes(
    comp, hole, player, stroke_num, total_strokes,
    score_before, score_after, is_last, duration_frames, fps
):
    """
    Builds the node graph inside the Fusion comp:

    Layout (1920x1080 reference, top-right anchor):
    ┌─────────────────────────────────────────┐
    │  [7]  │  AP                      [E]    │
    │ 387yds│  1  2  [3]  4                   │
    └─────────────────────────────────────────┘
    """
    # Clear default nodes
    for node in comp.GetToolList().values():
        node.Delete()

    # ── Dimensions (all positions in 0..1 normalised Fusion space) ────────
    # Fusion uses 0,0 = bottom-left, 0.5,0.5 = centre, 1,1 = top-right
    # Card is approx 860x120 px on a 1920x1080 canvas → ~0.45 x 0.11
    card_w  = 0.45
    card_h  = 0.115
    anchor_x= 0.97   # right edge
    anchor_y= 0.93   # near top

    cx = anchor_x - card_w / 2
    cy = anchor_y - card_h / 2

    # ── 1. Card background ────────────────────────────────────────────────
    bg = comp.AddTool("Background", -2, 2)
    bg.TopLeftRed   [0] = 0.102
    bg.TopLeftGreen [0] = 0.169
    bg.TopLeftBlue  [0] = 0.290
    bg.TopLeftAlpha [0] = 1.0
    bg.Width  = comp.WIDTH  if hasattr(comp, "WIDTH") else 1920
    bg.Height = comp.HEIGHT if hasattr(comp, "HEIGHT") else 1080

    # ── 2. Card rectangle mask ────────────────────────────────────────────
    rect = comp.AddTool("RectangleMask", -2, 1)
    rect.Width      [0] = card_w
    rect.Height     [0] = card_h
    rect.Center     [0] = {1: cx, 2: cy}
    rect.CornerRadius[0]= 0.012
    rect.SoftEdge   [0] = 0.0

    # ── 3. Card border (slightly larger rectangle, white) ─────────────────
    border_bg = comp.AddTool("Background", -1, 2)
    border_bg.TopLeftRed   [0] = 1.0
    border_bg.TopLeftGreen [0] = 1.0
    border_bg.TopLeftBlue  [0] = 1.0
    border_bg.TopLeftAlpha [0] = 1.0
    border_bg.Width  = 1920
    border_bg.Height = 1080

    border_rect = comp.AddTool("RectangleMask", -1, 1)
    border_rect.Width       [0] = card_w + 0.005
    border_rect.Height      [0] = card_h + 0.007
    border_rect.Center      [0] = {1: cx, 2: cy}
    border_rect.CornerRadius[0] = 0.014
    border_rect.SoftEdge    [0] = 0.0

    # ── 4. Text nodes ─────────────────────────────────────────────────────
    left_x = anchor_x - card_w + 0.035
    top_y   = anchor_y - 0.022
    bot_y   = anchor_y - card_h + 0.022

    _add_text(comp, str(hole["number"]), left_x, top_y - 0.008,
              size=0.085, bold=True, r=1, g=1, b=1, node_x=0, node_y=2)

    dist_str = f"{hole['distance']} yds"
    _add_text(comp, dist_str, left_x, bot_y,
              size=0.030, bold=False, r=0.85, g=0.85, b=0.85, node_x=0, node_y=1)

    # Vertical divider
    div_x = anchor_x - card_w + 0.095
    div = comp.AddTool("RectangleMask", 1, 1)
    div.Width  [0] = 0.0015
    div.Height [0] = card_h * 0.75
    div.Center [0] = {1: div_x, 2: cy}
    div.SoftEdge[0]= 0.0

    # Player name
    name_x = anchor_x - card_w + 0.19
    _add_text(comp, player.upper(), name_x, top_y,
              size=0.048, bold=True, r=1, g=1, b=1,
              h_align="Left", node_x=1, node_y=2)

    # Stroke indicators
    stroke_spacing = 0.038
    for s in range(1, total_strokes + 1):
        sx = name_x + (s - 1) * stroke_spacing
        is_active = (s == stroke_num)
        r = 0.302 if is_active else 1.0
        g = 0.816 if is_active else 1.0
        b = 0.882 if is_active else 1.0
        sz = 0.034 if is_active else 0.030
        _add_text(comp, str(s), sx, bot_y, size=sz, bold=is_active,
                  r=r, g=g, b=b, h_align="Left",
                  node_x=2 + s, node_y=1)

    # Score
    score_x = anchor_x - 0.022
    t_score = _add_text(comp, score_before, score_x, top_y - 0.008,
                        size=0.060, bold=True, r=1, g=1, b=1,
                        h_align="Right", node_x=3, node_y=2)
    if is_last:
        _animate_score(comp, t_score, score_before, score_after, fps)

    # MediaOut
    comp.AddTool("MediaOut", 10, 0)


def _add_text(comp, text, x, y, size=0.04, bold=False,
              r=1.0, g=1.0, b=1.0, h_align="Center",
              node_x=0, node_y=0):
    t = comp.AddTool("TextPlus", node_x, node_y)
    t.StyledText[0]  = text
    t.Size      [0]  = size
    t.Style          = "Bold" if bold else "Regular"
    t.HorizontalAnchoring[0] = h_align
    t.Red1      [0]  = r
    t.Green1    [0]  = g
    t.Blue1     [0]  = b
    t.Center    [0]  = {1: x, 2: y}
    t.VerticalAnchoring[0] = "Center"
    return t


def _animate_score(comp, text_node, score_before, score_after, fps):
    """
    Keyframe the score Text+ node to count up/down from score_before
    to score_after over the first 30 frames.
    """
    val_start = score_to_int(score_before)
    val_end   = score_to_int(score_after)

    if val_start == val_end:
        return

    direction = 1 if val_end > val_start else -1
    steps     = abs(val_end - val_start)
    anim_dur  = min(30, int(fps))  # max 30 frames

    text_node.StyledText.MakeCubicSpline()
    for i in range(steps + 1):
        frame = int(i * anim_dur / steps)
        current_val = val_start + direction * i
        if current_val == 0:
            label = "E"
        elif current_val > 0:
            label = f"+{current_val}"
        else:
            label = str(current_val)
        text_node.StyledText[frame] = label


# ── Timecode helper ───────────────────────────────────────────────────────────
def _tc_to_frames(tc_str, fps):
    """Convert HH:MM:SS:FF timecode string to frame number."""
    try:
        parts = tc_str.replace(";", ":").split(":")
        h, m, s, f = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        return int((h * 3600 + m * 60 + s) * fps) + f
    except Exception:
        return 0


# ── UI helpers ────────────────────────────────────────────────────────────────
def _make_hole_row(hole_idx):
    """Return a UI VGroup describing one hole card."""
    h    = state["holes"][hole_idx]
    hnum = h["number"]

    rows = []
    rows.append(ui.HGroup({"Spacing": 6, "Weight": 0}, [
        ui.Label({"Text": f"HOLE {hnum}", "Weight": 0,
                  "StyleSheet": "color:#4DD0E1; font-weight:bold; font-size:13px;"}),
        ui.HGap(0),
        ui.Button({"Text": "✕", "ID": f"del_hole_{hole_idx}",
                   "Weight": 0,
                   "StyleSheet": "color:#FF5555; font-size:11px; padding:2px 6px;"}),
    ]))

    rows.append(ui.HGroup({"Spacing": 8, "Weight": 0}, [
        ui.Label({"Text": "PAR", "Weight": 0,
                  "StyleSheet": "color:#AAAAAA; font-size:11px;"}),
        ui.SpinBox({"ID": f"par_{hole_idx}", "Value": h["par"],
                    "Minimum": 3, "Maximum": 6, "Weight": 0.15}),
        ui.Label({"Text": "Distance (yds)", "Weight": 0,
                  "StyleSheet": "color:#AAAAAA; font-size:11px;"}),
        ui.SpinBox({"ID": f"dist_{hole_idx}", "Value": h["distance"],
                    "Minimum": 50, "Maximum": 700, "Weight": 0.25}),
        ui.Label({"Text": "Strokes", "Weight": 0,
                  "StyleSheet": "color:#AAAAAA; font-size:11px;"}),
        ui.SpinBox({"ID": f"strokes_{hole_idx}", "Value": h["strokes"],
                    "Minimum": 1, "Maximum": 15, "Weight": 0.15}),
    ]))

    stroke_btns = []
    for s in range(1, h["strokes"] + 1):
        is_last = (s == h["strokes"])
        label   = f"Stroke {s}{'  ★' if is_last else ''} → Insert at Playhead"
        stroke_btns.append(
            ui.Button({"Text": label,
                       "ID": f"ins_{hole_idx}_{s}",
                       "StyleSheet": (
                           "background:#1565C0; color:white; padding:4px 10px;"
                           if not is_last else
                           "background:#2E7D32; color:white; padding:4px 10px; font-weight:bold;"
                       )})
        )

    rows += stroke_btns

    return ui.VGroup({"Spacing": 4, "Weight": 0,
                      "StyleSheet": (
                          "background:#2A2A3E; border:1px solid #4DD0E1;"
                          "border-radius:6px; padding:8px; margin:4px;"
                      )}, rows)


# ── Main window ───────────────────────────────────────────────────────────────
def build_main_window():
    win = disp.AddWindow(
        {
            "ID":          "GolfScorecard",
            "WindowTitle": "Golf Scorecard",
            "Geometry":    [100, 100, 520, 700],
            "StyleSheet":  "background:#1E1E2E; color:#FFFFFF; font-family:'Open Sans', Arial;",
        },
        [
            ui.VGroup({"Spacing": 8, "Weight": 1}, [

                ui.Label({
                    "Text": "GOLF SCORECARD",
                    "Alignment": {"AlignHCenter": True},
                    "StyleSheet": (
                        "color:#4DD0E1; font-size:18px; font-weight:bold;"
                        "padding:10px; border-bottom:1px solid #4DD0E1;"
                    ),
                }),

                ui.HGroup({"Spacing": 8, "Weight": 0}, [
                    ui.Label({"Text": "Player Name", "Weight": 0,
                              "StyleSheet": "color:#AAAAAA; font-size:12px;"}),
                    ui.LineEdit({"ID": "player_name",
                                 "PlaceholderText": "e.g. Tiger Woods",
                                 "StyleSheet": (
                                     "background:#2A2A3E; color:white;"
                                     "border:1px solid #555; border-radius:4px; padding:4px;"
                                 )}),
                ]),

                ui.Button({
                    "ID":   "add_hole",
                    "Text": "+ Add Hole",
                    "StyleSheet": (
                        "background:#1565C0; color:white; font-weight:bold;"
                        "font-size:13px; padding:6px; border-radius:4px;"
                    ),
                    "Weight": 0,
                }),

                ui.ScrollArea({
                    "ID":         "holes_scroll",
                    "Weight":     1,
                    "StyleSheet": "border:none;",
                }, [
                    ui.VGroup({"ID": "holes_container", "Spacing": 6, "Weight": 0}, []),
                ]),

            ]),
        ]
    )
    return win


# ── Event handlers ────────────────────────────────────────────────────────────
def refresh_holes(win):
    """Rebuild all hole cards inside the scroll area."""
    container = win.Find("holes_container")
    container.Clear()
    for i in range(len(state["holes"])):
        container.AddChild(_make_hole_row(i))


def run():
    win = build_main_window()
    win.Show()

    def on_close(ev):
        disp.ExitLoop()

    def on_add_hole(ev):
        next_num = len(state["holes"]) + 1
        state["holes"].append({
            "number":   next_num,
            "par":      4,
            "distance": 350,
            "strokes":  4,
        })
        refresh_holes(win)

    def on_clicked(ev):
        btn_id = ev["who"]

        if btn_id.startswith("del_hole_"):
            idx = int(btn_id.split("_")[-1])
            state["holes"].pop(idx)
            for i, h in enumerate(state["holes"]):
                h["number"] = i + 1
            refresh_holes(win)
            return

        if btn_id.startswith("ins_"):
            parts      = btn_id.split("_")
            hole_idx   = int(parts[1])
            stroke_num = int(parts[2])
            _sync_state(win)
            state["player"] = win.Find("player_name").Text
            insert_scorecard(hole_idx, stroke_num)
            return

    def _sync_state(win):
        """Pull current SpinBox values back into state."""
        for i, h in enumerate(state["holes"]):
            par_box     = win.Find(f"par_{i}")
            dist_box    = win.Find(f"dist_{i}")
            strokes_box = win.Find(f"strokes_{i}")
            if par_box:     h["par"]      = par_box.Value
            if dist_box:    h["distance"] = dist_box.Value
            if strokes_box: h["strokes"]  = strokes_box.Value

    win.On["GolfScorecard"].Close   = on_close
    win.On["add_hole"].Clicked      = on_add_hole
    win.On["GolfScorecard"].Clicked = on_clicked

    disp.RunLoop()
    win.Hide()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run()
else:
    run()
