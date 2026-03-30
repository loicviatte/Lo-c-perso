"""
Golf Scorecard Plugin for DaVinci Resolve 20.3
Run from: Workspace > Scripts > Utility > GolfScorecard
"""

import sys

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

state  = {"player": "", "holes": []}
_win   = [None]
_win_n = [0]

# ── Score helpers ──────────────────────────────────────────────────────────
def calc_score_str(strokes_total, par_total):
    diff = strokes_total - par_total
    if diff == 0: return "E"
    return f"+{diff}" if diff > 0 else str(diff)

def cumulative_score_before(hole_index):
    s = sum(h["strokes"] for h in state["holes"][:hole_index])
    p = sum(h["par"]     for h in state["holes"][:hole_index])
    return calc_score_str(s, p)

def cumulative_score_after(hole_index):
    s = sum(h["strokes"] for h in state["holes"][:hole_index + 1])
    p = sum(h["par"]     for h in state["holes"][:hole_index + 1])
    return calc_score_str(s, p)

def score_to_int(score_str):
    if score_str == "E": return 0
    return int(score_str.replace("+", ""))


# ── UI ─────────────────────────────────────────────────────────────────────────
STYLE_WINDOW = "background-color:#1E1E2E; color:#FFFFFF;"
STYLE_CARD   = "background-color:#252538;"
STYLE_LABEL  = "color:#AAAAAA; font-size:11px;"
STYLE_HOLE_H = "color:#4DD0E1; font-weight:bold; font-size:13px;"
STYLE_BTN_ADD  = "background-color:#1565C0; color:white; font-weight:bold; font-size:13px; padding:6px;"
STYLE_BTN_INS  = "background-color:#1565C0; color:white; padding:4px;"
STYLE_BTN_LAST = "background-color:#2E7D32; color:white; font-weight:bold; padding:4px;"
STYLE_BTN_DEL  = "background-color:#C62828; color:white; font-size:11px; padding:2px 8px;"
STYLE_DIVIDER  = "background-color:#4DD0E1; min-height:1px; max-height:1px;"
STYLE_INPUT    = "background-color:#2A2A3E; color:white; border:1px solid #555; border-radius:3px; padding:3px;"


def _hole_widgets():
    widgets = []
    for idx, h in enumerate(state["holes"]):
        rows = [
            # Hole header
            ui.HGroup({"Spacing": 6, "Weight": 0}, [
                ui.Label({"Text": f"HOLE {h['number']}",
                          "StyleSheet": STYLE_HOLE_H, "Weight": 0}),
                ui.Label({"Text": "", "Weight": 1}),  # spacer
                ui.Button({"Text": "Delete", "ID": f"del_{idx}",
                           "StyleSheet": STYLE_BTN_DEL, "Weight": 0}),
            ]),
            # PAR / Distance / Strokes
            ui.HGroup({"Spacing": 4, "Weight": 0}, [
                ui.Label({"Text": "PAR",       "StyleSheet": STYLE_LABEL, "Weight": 0}),
                ui.SpinBox({"ID": f"par_{idx}",  "Value": h["par"],
                            "Minimum": 3, "Maximum": 6, "Weight": 0}),
                ui.Label({"Text": "  Dist (yds)", "StyleSheet": STYLE_LABEL, "Weight": 0}),
                ui.SpinBox({"ID": f"dist_{idx}", "Value": h["distance"],
                            "Minimum": 50, "Maximum": 700, "Weight": 0}),
                ui.Label({"Text": "  Strokes",  "StyleSheet": STYLE_LABEL, "Weight": 0}),
                ui.SpinBox({"ID": f"str_{idx}",  "Value": h["strokes"],
                            "Minimum": 1, "Maximum": 15, "Weight": 0}),
            ]),
        ]
        # Stroke buttons
        for s in range(1, h["strokes"] + 1):
            is_last = (s == h["strokes"])
            rows.append(ui.Button({
                "Text": f"Stroke {s}{'  ★' if is_last else ''} → Insert at Playhead",
                "ID":   f"ins_{idx}_{s}",
                "StyleSheet": STYLE_BTN_LAST if is_last else STYLE_BTN_INS,
            }))

        widgets.append(ui.VGroup(
            {"Spacing": 6, "Weight": 0, "StyleSheet": STYLE_CARD},
            rows
        ))
        # Thin separator between holes
        widgets.append(ui.Label({"Text": "", "StyleSheet": STYLE_DIVIDER, "Weight": 0}))
    return widgets


def _save_player(win):
    fld = win.Find("player_name")
    if fld: state["player"] = fld.Text

def _sync_spinboxes(win):
    for i, h in enumerate(state["holes"]):
        for key, fid in (("par", f"par_{i}"), ("distance", f"dist_{i}"), ("strokes", f"str_{i}")):
            fld = win.Find(fid)
            if fld: h[key] = fld.Value


def make_window():
    if _win[0] is not None:
        _save_player(_win[0])
        _win[0].Hide()

    _win_n[0] += 1
    win_id = f"GS{_win_n[0]}"

    body = [
        # Title
        ui.Label({
            "Text": "GOLF SCORECARD",
            "Alignment": {"AlignHCenter": True},
            "StyleSheet": "color:#4DD0E1; font-size:18px; font-weight:bold; padding:8px 0;",
            "Weight": 0,
        }),
        ui.Label({"Text": "", "StyleSheet": STYLE_DIVIDER, "Weight": 0}),
        # Player name
        ui.HGroup({"Spacing": 8, "Weight": 0}, [
            ui.Label({"Text": "Player", "StyleSheet": STYLE_LABEL, "Weight": 0}),
            ui.LineEdit({"ID": "player_name", "Text": state["player"],
                         "PlaceholderText": "Player name",
                         "StyleSheet": STYLE_INPUT}),
        ]),
        # Add Hole button
        ui.Button({"ID": "add_hole", "Text": "+ Add Hole",
                   "StyleSheet": STYLE_BTN_ADD, "Weight": 0}),
    ] + _hole_widgets() + [
        ui.VGap(0),
    ]

    win = disp.AddWindow(
        {"ID": win_id, "WindowTitle": "Golf Scorecard",
         "Geometry": [100, 100, 480, 680],
         "StyleSheet": STYLE_WINDOW},
        [ui.VGroup({"Spacing": 6, "Weight": 1}, body)]
    )
    _win[0] = win

    # Close
    win.On[win_id].Close = lambda ev: disp.ExitLoop()

    # Add Hole
    def on_add_hole(ev):
        _save_player(win)
        state["holes"].append({
            "number":   len(state["holes"]) + 1,
            "par":      4,
            "distance": 350,
            "strokes":  4,
        })
        make_window()

    win.On["add_hole"].Clicked = on_add_hole

    # Delete buttons
    for i in range(len(state["holes"])):
        def make_del(idx):
            def handler(ev):
                _save_player(win)
                _sync_spinboxes(win)
                state["holes"].pop(idx)
                for j, h in enumerate(state["holes"]):
                    h["number"] = j + 1
                make_window()
            return handler
        win.On[f"del_{i}"].Clicked = make_del(i)

    # Insert buttons
    for i, h in enumerate(state["holes"]):
        for s in range(1, h["strokes"] + 1):
            def make_ins(hidx, snum):
                def handler(ev):
                    _save_player(win)
                    _sync_spinboxes(win)
                    insert_scorecard(hidx, snum)
                return handler
            win.On[f"ins_{i}_{s}"].Clicked = make_ins(i, s)

    win.Show()
    return win


# ── Timeline insertion ─────────────────────────────────────────────────────────
def insert_scorecard(hole_idx, stroke_num):
    # Make sure we are on the Edit page
    resolve.OpenPage("edit")

    project = resolve.GetProjectManager().GetCurrentProject()
    if project is None:
        print("[GolfScorecard] ERROR: No active project.")
        return

    timeline = project.GetCurrentTimeline()
    if timeline is None:
        print("[GolfScorecard] ERROR: No active timeline. Create a timeline first.")
        return

    hole          = state["holes"][hole_idx]
    player        = state["player"] or "PLAYER"
    total_strokes = hole["strokes"]
    is_last       = (stroke_num == total_strokes)
    score_before  = cumulative_score_before(hole_idx)
    score_after   = cumulative_score_after(hole_idx)
    comp_name     = f"Scorecard_H{hole['number']}_S{stroke_num}"

    fps = 25.0
    try:
        fps = float(timeline.GetSetting("timelineFrameRate"))
    except Exception:
        pass

    print(f"[GolfScorecard] Inserting {comp_name} | score: {score_before} -> {score_after} | fps: {fps}")

    # Ensure at least 2 video tracks
    if timeline.GetTrackCount("video") < 2:
        timeline.AddTrack("video")
        print("[GolfScorecard] Added video track 2")

    # Insert a Fusion Title clip at the playhead
    inserted = timeline.InsertFusionTitleIntoTimeline(comp_name)
    if inserted is None:
        print("[GolfScorecard] ERROR: InsertFusionTitleIntoTimeline returned None.")
        print("[GolfScorecard] Make sure the Edit page is active and a timeline is open.")
        return

    print(f"[GolfScorecard] Clip inserted: {inserted}")

    comp = inserted.GetFusionCompByIndex(1)
    if comp is None:
        print("[GolfScorecard] ERROR: Could not access Fusion comp on inserted clip.")
        return

    comp.Lock()
    try:
        _build_scorecard_nodes(comp, hole, player, stroke_num, total_strokes,
                               score_before, score_after, is_last, fps)
        print(f"[GolfScorecard] Scorecard nodes built OK")
    except Exception as e:
        print(f"[GolfScorecard] ERROR building nodes: {e}")
    finally:
        comp.Unlock()


# ── Fusion node builder ──────────────────────────────────────────────────────────
def _build_scorecard_nodes(comp, hole, player, stroke_num, total_strokes,
                           score_before, score_after, is_last, fps):
    for node in comp.GetToolList().values():
        node.Delete()

    card_w, card_h     = 0.45, 0.115
    anchor_x, anchor_y = 0.97, 0.93
    cx = anchor_x - card_w / 2
    cy = anchor_y - card_h / 2

    # Background
    bg = comp.AddTool("Background", -2, 2)
    bg.TopLeftRed[0] = 0.102; bg.TopLeftGreen[0] = 0.169
    bg.TopLeftBlue[0] = 0.290; bg.TopLeftAlpha[0] = 1.0

    rect = comp.AddTool("RectangleMask", -2, 1)
    rect.Width[0] = card_w; rect.Height[0] = card_h
    rect.Center[0] = {1: cx, 2: cy}
    rect.CornerRadius[0] = 0.012; rect.SoftEdge[0] = 0.0

    # Border
    bbg = comp.AddTool("Background", -1, 2)
    bbg.TopLeftRed[0] = bbg.TopLeftGreen[0] = bbg.TopLeftBlue[0] = bbg.TopLeftAlpha[0] = 1.0

    brect = comp.AddTool("RectangleMask", -1, 1)
    brect.Width[0] = card_w + 0.005; brect.Height[0] = card_h + 0.007
    brect.Center[0] = {1: cx, 2: cy}
    brect.CornerRadius[0] = 0.014; brect.SoftEdge[0] = 0.0

    lx = anchor_x - card_w + 0.035
    ty = anchor_y - 0.022
    by = anchor_y - card_h + 0.022

    # Hole number + distance
    _txt(comp, str(hole["number"]),       lx, ty - 0.008, size=0.085, bold=True,              nx=0, ny=2)
    _txt(comp, f"{hole['distance']} yds", lx, by,          size=0.030, r=.85, g=.85, b=.85,  nx=0, ny=1)

    # Divider
    dx = anchor_x - card_w + 0.095
    dv = comp.AddTool("RectangleMask", 1, 1)
    dv.Width[0] = 0.0015; dv.Height[0] = card_h * 0.75
    dv.Center[0] = {1: dx, 2: cy}; dv.SoftEdge[0] = 0.0

    # Player name
    nx_ = anchor_x - card_w + 0.19
    _txt(comp, player.upper(), nx_, ty, size=0.048, bold=True, h_align="Left", nx=1, ny=2)

    # Stroke indicators
    for s in range(1, total_strokes + 1):
        act = (s == stroke_num)
        _txt(comp, str(s), nx_ + (s - 1) * 0.038, by,
             size=0.034 if act else 0.030, bold=act,
             r=0.302 if act else 1.0,
             g=0.816 if act else 1.0,
             b=0.882 if act else 1.0,
             h_align="Left", nx=2 + s, ny=1)

    # Score
    ts = _txt(comp, score_before, anchor_x - 0.022, ty - 0.008,
              size=0.060, bold=True, h_align="Right", nx=3, ny=2)
    if is_last:
        _animate_score(ts, score_before, score_after, fps)

    comp.AddTool("MediaOut", 10, 0)


def _txt(comp, text, x, y, size=0.04, bold=False,
         r=1.0, g=1.0, b=1.0, h_align="Center", nx=0, ny=0):
    t = comp.AddTool("TextPlus", nx, ny)
    t.StyledText[0] = text; t.Size[0] = size
    t.Style = "Bold" if bold else "Regular"
    t.HorizontalAnchoring[0] = h_align
    t.Red1[0] = r; t.Green1[0] = g; t.Blue1[0] = b
    t.Center[0] = {1: x, 2: y}; t.VerticalAnchoring[0] = "Center"
    return t


def _animate_score(text_node, score_before, score_after, fps):
    v0, v1 = score_to_int(score_before), score_to_int(score_after)
    if v0 == v1: return
    d = 1 if v1 > v0 else -1
    steps = abs(v1 - v0)
    dur   = min(30, int(fps))
    text_node.StyledText.MakeCubicSpline()
    for i in range(steps + 1):
        frame = int(i * dur / steps)
        v = v0 + d * i
        text_node.StyledText[frame] = "E" if v == 0 else (f"+{v}" if v > 0 else str(v))


# ── Entry point ───────────────────────────────────────────────────────────────
def run():
    make_window()
    disp.RunLoop()
    if _win[0]:
        _win[0].Hide()

if __name__ == "__main__":
    run()
else:
    run()
