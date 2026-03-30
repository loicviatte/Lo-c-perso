"""
Golf Scorecard Plugin for DaVinci Resolve 20.3
Run from: Workspace > Scripts > Utility > GolfScorecard
"""

import sys

# ── DaVinci Resolve bootstrap ────────────────────────────────────────────────
try:
    import DaVinciResolveScript as dvr_script
    resolve = dvr_script.scriptapp("Resolve")
except ImportError:
    resolve = bmd.scriptapp("Resolve")  # noqa: F821

if resolve is None:
    print("[GolfScorecard] ERROR: Could not connect to DaVinci Resolve.")
    sys.exit(1)

fusion = resolve.Fusion()
ui     = fusion.UIManager
disp   = bmd.UIDispatcher(ui)  # noqa: F821

# ── State ──────────────────────────────────────────────────────────────────
state = {
    "player": "",
    "holes":  [],
}

# ── Score helpers ───────────────────────────────────────────────────────────
def calc_score_str(strokes_total, par_total):
    diff = strokes_total - par_total
    if diff == 0: return "E"
    if diff > 0:  return f"+{diff}"
    return str(diff)

def cumulative_score_before(hole_index):
    total_s = sum(h["strokes"] for h in state["holes"][:hole_index])
    total_p = sum(h["par"]     for h in state["holes"][:hole_index])
    return calc_score_str(total_s, total_p)

def cumulative_score_after(hole_index):
    total_s = sum(h["strokes"] for h in state["holes"][:hole_index + 1])
    total_p = sum(h["par"]     for h in state["holes"][:hole_index + 1])
    return calc_score_str(total_s, total_p)

def score_to_int(score_str):
    if score_str == "E": return 0
    return int(score_str.replace("+", ""))

# ── Timeline insertion ─────────────────────────────────────────────────────────
def insert_scorecard(hole_idx, stroke_num):
    project  = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    if timeline is None:
        print("[GolfScorecard] ERROR: No active timeline.")
        return

    hole          = state["holes"][hole_idx]
    player        = state["player"] or "PLAYER"
    total_strokes = hole["strokes"]
    is_last       = (stroke_num == total_strokes)
    score_before  = cumulative_score_before(hole_idx)
    score_after   = cumulative_score_after(hole_idx)
    comp_name     = f"Scorecard_H{hole['number']}_S{stroke_num}"
    fps           = float(timeline.GetSetting("timelineFrameRate"))

    if timeline.GetTrackCount("video") < 2:
        timeline.AddTrack("video")

    inserted = timeline.InsertFusionTitleIntoTimeline(comp_name)
    if inserted is None:
        print("[GolfScorecard] InsertFusionTitleIntoTimeline failed.")
        return

    comp = inserted.GetFusionCompByIndex(1)
    if comp is None:
        print("[GolfScorecard] Could not access Fusion comp.")
        return

    comp.Lock()
    try:
        _build_scorecard_nodes(
            comp, hole, player, stroke_num, total_strokes,
            score_before, score_after, is_last, fps
        )
    finally:
        comp.Unlock()
    print(f"[GolfScorecard] Inserted: {comp_name}")


# ── Fusion node builder ──────────────────────────────────────────────────────────
def _build_scorecard_nodes(
    comp, hole, player, stroke_num, total_strokes,
    score_before, score_after, is_last, fps
):
    for node in comp.GetToolList().values():
        node.Delete()

    card_w   = 0.45
    card_h   = 0.115
    anchor_x = 0.97
    anchor_y = 0.93
    cx = anchor_x - card_w / 2
    cy = anchor_y - card_h / 2

    bg = comp.AddTool("Background", -2, 2)
    bg.TopLeftRed[0]   = 0.102
    bg.TopLeftGreen[0] = 0.169
    bg.TopLeftBlue[0]  = 0.290
    bg.TopLeftAlpha[0] = 1.0

    rect = comp.AddTool("RectangleMask", -2, 1)
    rect.Width[0]        = card_w
    rect.Height[0]       = card_h
    rect.Center[0]       = {1: cx, 2: cy}
    rect.CornerRadius[0] = 0.012
    rect.SoftEdge[0]     = 0.0

    border_bg = comp.AddTool("Background", -1, 2)
    border_bg.TopLeftRed[0]   = 1.0
    border_bg.TopLeftGreen[0] = 1.0
    border_bg.TopLeftBlue[0]  = 1.0
    border_bg.TopLeftAlpha[0] = 1.0

    border_rect = comp.AddTool("RectangleMask", -1, 1)
    border_rect.Width[0]        = card_w + 0.005
    border_rect.Height[0]       = card_h + 0.007
    border_rect.Center[0]       = {1: cx, 2: cy}
    border_rect.CornerRadius[0] = 0.014
    border_rect.SoftEdge[0]     = 0.0

    left_x = anchor_x - card_w + 0.035
    top_y  = anchor_y - 0.022
    bot_y  = anchor_y - card_h + 0.022

    _add_text(comp, str(hole["number"]), left_x, top_y - 0.008,
              size=0.085, bold=True, node_x=0, node_y=2)
    _add_text(comp, f"{hole['distance']} yds", left_x, bot_y,
              size=0.030, r=0.85, g=0.85, b=0.85, node_x=0, node_y=1)

    div_x = anchor_x - card_w + 0.095
    div = comp.AddTool("RectangleMask", 1, 1)
    div.Width[0]    = 0.0015
    div.Height[0]   = card_h * 0.75
    div.Center[0]   = {1: div_x, 2: cy}
    div.SoftEdge[0] = 0.0

    name_x = anchor_x - card_w + 0.19
    _add_text(comp, player.upper(), name_x, top_y,
              size=0.048, bold=True, h_align="Left", node_x=1, node_y=2)

    for s in range(1, total_strokes + 1):
        sx        = name_x + (s - 1) * 0.038
        is_active = (s == stroke_num)
        _add_text(comp, str(s), sx, bot_y,
                  size=0.034 if is_active else 0.030,
                  bold=is_active,
                  r=0.302 if is_active else 1.0,
                  g=0.816 if is_active else 1.0,
                  b=0.882 if is_active else 1.0,
                  h_align="Left", node_x=2 + s, node_y=1)

    score_x = anchor_x - 0.022
    t_score = _add_text(comp, score_before, score_x, top_y - 0.008,
                        size=0.060, bold=True, h_align="Right", node_x=3, node_y=2)
    if is_last:
        _animate_score(t_score, score_before, score_after, fps)

    comp.AddTool("MediaOut", 10, 0)


def _add_text(comp, text, x, y, size=0.04, bold=False,
              r=1.0, g=1.0, b=1.0, h_align="Center",
              node_x=0, node_y=0):
    t = comp.AddTool("TextPlus", node_x, node_y)
    t.StyledText[0]          = text
    t.Size[0]                = size
    t.Style                  = "Bold" if bold else "Regular"
    t.HorizontalAnchoring[0] = h_align
    t.Red1[0]                = r
    t.Green1[0]              = g
    t.Blue1[0]               = b
    t.Center[0]              = {1: x, 2: y}
    t.VerticalAnchoring[0]   = "Center"
    return t


def _animate_score(text_node, score_before, score_after, fps):
    val_start = score_to_int(score_before)
    val_end   = score_to_int(score_after)
    if val_start == val_end:
        return
    direction = 1 if val_end > val_start else -1
    steps     = abs(val_end - val_start)
    anim_dur  = min(30, int(fps))
    text_node.StyledText.MakeCubicSpline()
    for i in range(steps + 1):
        frame = int(i * anim_dur / steps)
        v     = val_start + direction * i
        label = "E" if v == 0 else (f"+{v}" if v > 0 else str(v))
        text_node.StyledText[frame] = label


# ── UI ─────────────────────────────────────────────────────────────────────────
def _make_hole_row(hole_idx):
    h = state["holes"][hole_idx]
    rows = [
        ui.HGroup({"Spacing": 6, "Weight": 0}, [
            ui.Label({"Text": f"HOLE {h['number']}", "Weight": 0,
                      "StyleSheet": "color:#4DD0E1; font-weight:bold; font-size:13px;"}),
            ui.Label({"Text": "", "Weight": 1}),
            ui.Button({"Text": "✕", "ID": f"del_hole_{hole_idx}", "Weight": 0,
                       "StyleSheet": "color:#FF5555; font-size:11px; padding:2px 6px;"}),
        ]),
        ui.HGroup({"Spacing": 6, "Weight": 0}, [
            ui.Label({"Text": "PAR", "Weight": 0,
                      "StyleSheet": "color:#AAAAAA; font-size:11px;"}),
            ui.SpinBox({"ID": f"par_{hole_idx}", "Value": h["par"],
                        "Minimum": 3, "Maximum": 6, "Weight": 0.15}),
            ui.Label({"Text": "Dist (yds)", "Weight": 0,
                      "StyleSheet": "color:#AAAAAA; font-size:11px;"}),
            ui.SpinBox({"ID": f"dist_{hole_idx}", "Value": h["distance"],
                        "Minimum": 50, "Maximum": 700, "Weight": 0.25}),
            ui.Label({"Text": "Strokes", "Weight": 0,
                      "StyleSheet": "color:#AAAAAA; font-size:11px;"}),
            ui.SpinBox({"ID": f"strokes_{hole_idx}", "Value": h["strokes"],
                        "Minimum": 1, "Maximum": 15, "Weight": 0.15}),
        ]),
    ]
    for s in range(1, h["strokes"] + 1):
        is_last = (s == h["strokes"])
        rows.append(ui.Button({
            "Text": f"Stroke {s}{'  ★' if is_last else ''} → Insert at Playhead",
            "ID":   f"ins_{hole_idx}_{s}",
            "StyleSheet": (
                "background:#2E7D32; color:white; padding:4px 10px; font-weight:bold;"
                if is_last else
                "background:#1565C0; color:white; padding:4px 10px;"
            ),
        }))
    return ui.VGroup({"Spacing": 4, "Weight": 0,
                      "StyleSheet": (
                          "background:#2A2A3E; border:1px solid #4DD0E1;"
                          "border-radius:6px; padding:8px; margin:4px;"
                      )}, rows)


def build_main_window():
    return disp.AddWindow(
        {
            "ID":          "GolfScorecard",
            "WindowTitle": "Golf Scorecard",
            "Geometry":    [100, 100, 520, 700],
            "StyleSheet":  "background:#1E1E2E; color:#FFFFFF;",
        },
        [ui.VGroup({"Spacing": 8, "Weight": 1}, [
            ui.Label({
                "Text":      "GOLF SCORECARD",
                "Alignment": {"AlignHCenter": True},
                "StyleSheet": (
                    "color:#4DD0E1; font-size:18px; font-weight:bold;"
                    "padding:10px; border-bottom:1px solid #4DD0E1;"
                ),
                "Weight": 0,
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
                "ID":         "add_hole",
                "Text":       "+ Add Hole",
                "StyleSheet": (
                    "background:#1565C0; color:white; font-weight:bold;"
                    "font-size:13px; padding:6px; border-radius:4px;"
                ),
                "Weight": 0,
            }),
            ui.VGroup({"ID": "holes_container", "Spacing": 6, "Weight": 1}, []),
        ])]
    )


def _sync_state(win):
    for i, h in enumerate(state["holes"]):
        par_box     = win.Find(f"par_{i}")
        dist_box    = win.Find(f"dist_{i}")
        strokes_box = win.Find(f"strokes_{i}")
        if par_box:     h["par"]      = par_box.Value
        if dist_box:    h["distance"] = dist_box.Value
        if strokes_box: h["strokes"]  = strokes_box.Value


def refresh_holes(win):
    """Rebuild hole cards and register their button handlers."""
    container = win.Find("holes_container")
    container.Clear()
    for i in range(len(state["holes"])):
        container.AddChild(_make_hole_row(i))

    # Register delete buttons
    for i in range(len(state["holes"])):
        def make_del(idx):
            def handler(ev):
                state["holes"].pop(idx)
                for j, h in enumerate(state["holes"]):
                    h["number"] = j + 1
                refresh_holes(win)
            return handler
        win.On[f"del_hole_{i}"].Clicked = make_del(i)

    # Register insert buttons
    for i, h in enumerate(state["holes"]):
        for s in range(1, h["strokes"] + 1):
            def make_ins(hidx, snum):
                def handler(ev):
                    _sync_state(win)
                    state["player"] = win.Find("player_name").Text
                    insert_scorecard(hidx, snum)
                return handler
            win.On[f"ins_{i}_{s}"].Clicked = make_ins(i, s)


def run():
    win = build_main_window()

    win.On["GolfScorecard"].Close = lambda ev: disp.ExitLoop()

    win.On["add_hole"].Clicked = lambda ev: (
        state["holes"].append({
            "number":   len(state["holes"]) + 1,
            "par":      4,
            "distance": 350,
            "strokes":  4,
        }) or refresh_holes(win)
    )

    win.Show()
    disp.RunLoop()
    win.Hide()


if __name__ == "__main__":
    run()
else:
    run()
