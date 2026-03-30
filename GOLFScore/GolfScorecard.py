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


# ── UI styles ───────────────────────────────────────────────────────────────
STYLE_WINDOW   = "background-color:#1E1E2E; color:#FFFFFF;"
STYLE_CARD     = "background-color:#252538;"
STYLE_LABEL    = "color:#AAAAAA; font-size:11px;"
STYLE_HOLE_H   = "color:#4DD0E1; font-weight:bold; font-size:13px;"
STYLE_BTN_ADD  = "background-color:#1565C0; color:white; font-weight:bold; font-size:13px; padding:6px;"
STYLE_BTN_INS  = "background-color:#1565C0; color:white; padding:4px;"
STYLE_BTN_LAST = "background-color:#2E7D32; color:white; font-weight:bold; padding:4px;"
STYLE_BTN_DEL  = "background-color:#C62828; color:white; font-size:11px; padding:2px 8px;"
STYLE_DIVIDER  = "background-color:#4DD0E1; min-height:1px; max-height:1px;"
STYLE_INPUT    = "background-color:#2A2A3E; color:white; border:1px solid #555; border-radius:3px; padding:3px;"


# ── UI builder ───────────────────────────────────────────────────────────────
def _hole_widgets():
    widgets = []
    for idx, h in enumerate(state["holes"]):
        rows = [
            ui.HGroup({"Spacing": 6, "Weight": 0}, [
                ui.Label({"Text": f"HOLE {h['number']}",
                          "StyleSheet": STYLE_HOLE_H, "Weight": 0}),
                ui.Label({"Text": "", "Weight": 1}),
                ui.Button({"Text": "Delete", "ID": f"del_{idx}",
                           "StyleSheet": STYLE_BTN_DEL, "Weight": 0}),
            ]),
            ui.HGroup({"Spacing": 4, "Weight": 0}, [
                ui.Label({"Text": "PAR",         "StyleSheet": STYLE_LABEL, "Weight": 0}),
                ui.SpinBox({"ID": f"par_{idx}",  "Value": h["par"],
                            "Minimum": 3, "Maximum": 6, "Weight": 0}),
                ui.Label({"Text": "  Dist (yds)","StyleSheet": STYLE_LABEL, "Weight": 0}),
                ui.SpinBox({"ID": f"dist_{idx}", "Value": h["distance"],
                            "Minimum": 50, "Maximum": 700, "Weight": 0}),
                ui.Label({"Text": "  Strokes",  "StyleSheet": STYLE_LABEL, "Weight": 0}),
                ui.SpinBox({"ID": f"str_{idx}",  "Value": h["strokes"],
                            "Minimum": 1, "Maximum": 15, "Weight": 0}),
            ]),
        ]
        for s in range(1, h["strokes"] + 1):
            is_last = (s == h["strokes"])
            rows.append(ui.Button({
                "Text": f"Stroke {s}{'  \u2605' if is_last else ''} \u2192 Insert at Playhead",
                "ID":   f"ins_{idx}_{s}",
                "StyleSheet": STYLE_BTN_LAST if is_last else STYLE_BTN_INS,
            }))
        widgets.append(ui.VGroup(
            {"Spacing": 6, "Weight": 0, "StyleSheet": STYLE_CARD}, rows))
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
        ui.Label({
            "Text": "GOLF SCORECARD",
            "Alignment": {"AlignHCenter": True},
            "StyleSheet": "color:#4DD0E1; font-size:18px; font-weight:bold; padding:8px 0;",
            "Weight": 0,
        }),
        ui.Label({"Text": "", "StyleSheet": STYLE_DIVIDER, "Weight": 0}),
        ui.HGroup({"Spacing": 8, "Weight": 0}, [
            ui.Label({"Text": "Player", "StyleSheet": STYLE_LABEL, "Weight": 0}),
            ui.LineEdit({"ID": "player_name", "Text": state["player"],
                         "PlaceholderText": "Player name",
                         "StyleSheet": STYLE_INPUT}),
        ]),
        ui.Button({"ID": "add_hole", "Text": "+ Add Hole",
                   "StyleSheet": STYLE_BTN_ADD, "Weight": 0}),
    ] + _hole_widgets() + [ui.VGap(0)]

    win = disp.AddWindow(
        {"ID": win_id, "WindowTitle": "Golf Scorecard",
         "Geometry": [100, 100, 480, 680], "StyleSheet": STYLE_WINDOW},
        [ui.VGroup({"Spacing": 6, "Weight": 1}, body)]
    )
    _win[0] = win

    win.On[win_id].Close = lambda ev: disp.ExitLoop()

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
def _try_insert(timeline):
    """
    Try every known method to insert a blank Fusion-capable clip.
    Returns (TimelineItem, comp) or (None, None).
    """
    # --- Method A: InsertFusionTitleIntoTimeline ---
    for name in ["Fusion Title", ""]:
        try:
            item = timeline.InsertFusionTitleIntoTimeline(name)
            if item is not None:
                comp = item.GetFusionCompByIndex(1)
                if comp:
                    print(f"[GS] OK via InsertFusionTitleIntoTimeline('{name}')")
                    return item, comp
        except Exception as e:
            print(f"[GS] InsertFusionTitleIntoTimeline('{name}'): {e}")

    # --- Method B: InsertFusionGeneratorIntoTimeline ---
    for name in ["Fusion Generator", ""]:
        try:
            item = timeline.InsertFusionGeneratorIntoTimeline(name)
            if item is not None:
                comp = item.GetFusionCompByIndex(1)
                if comp:
                    print(f"[GS] OK via InsertFusionGeneratorIntoTimeline('{name}')")
                    return item, comp
        except Exception as e:
            print(f"[GS] InsertFusionGeneratorIntoTimeline('{name}'): {e}")

    # --- Method C: standard generator + AddFusionComp ---
    for name in ["Solid Color", "Color", "BG", "Background"]:
        try:
            item = timeline.InsertGeneratorIntoTimeline(name)
            if item is not None:
                print(f"[GS] InsertGeneratorIntoTimeline('{name}') OK, adding FusionComp...")
                comp = item.AddFusionComp()
                if comp:
                    print(f"[GS] OK via InsertGeneratorIntoTimeline + AddFusionComp")
                    return item, comp
                # comp already exists at index 1?
                comp = item.GetFusionCompByIndex(1)
                if comp:
                    print(f"[GS] OK via InsertGeneratorIntoTimeline + GetFusionCompByIndex")
                    return item, comp
        except Exception as e:
            print(f"[GS] InsertGeneratorIntoTimeline('{name}'): {e}")

    return None, None


def insert_scorecard(hole_idx, stroke_num):
    project  = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline() if project else None
    if timeline is None:
        print("[GS] ERROR: No active timeline. Open a timeline on the Edit page first.")
        return

    hole          = state["holes"][hole_idx]
    player        = state["player"] or "PLAYER"
    total_strokes = hole["strokes"]
    is_last       = (stroke_num == total_strokes)
    score_before  = cumulative_score_before(hole_idx)
    score_after   = cumulative_score_after(hole_idx)

    fps = 25.0
    try:
        fps = float(timeline.GetSetting("timelineFrameRate"))
    except Exception:
        pass

    print(f"[GS] Insert H{hole['number']} S{stroke_num} | {score_before}->{score_after} | fps={fps}")

    if timeline.GetTrackCount("video") < 2:
        timeline.AddTrack("video")
        print("[GS] Added video track 2")

    item, comp = _try_insert(timeline)
    if comp is None:
        print("[GS] ERROR: Could not insert a Fusion clip.")
        print("[GS] Make sure you are on the Edit page with an active timeline.")
        return

    comp.Lock()
    try:
        _build_scorecard_nodes(comp, hole, player, stroke_num, total_strokes,
                               score_before, score_after, is_last, fps)
        print("[GS] Scorecard built OK.")
    except Exception as e:
        print(f"[GS] ERROR building nodes: {e}")
        import traceback; traceback.print_exc()
    finally:
        comp.Unlock()


# ── Fusion node builder ──────────────────────────────────────────────────────────
def _build_scorecard_nodes(comp, hole, player, stroke_num, total_strokes,
                           score_before, score_after, is_last, fps):
    # Clear existing nodes
    for node in comp.GetToolList().values():
        node.Delete()

    # Layout constants (normalised 0..1, origin bottom-left)
    card_w, card_h     = 0.45,  0.115
    anchor_x, anchor_y = 0.97,  0.93
    cx = anchor_x - card_w / 2
    cy = anchor_y - card_h / 2

    # ---- Transparent base -----------------------------------------------
    base = comp.AddTool("Background", -6, 0)
    base.TopLeftRed[0] = base.TopLeftGreen[0] = base.TopLeftBlue[0] = 0.0
    base.TopLeftAlpha[0] = 0.0          # fully transparent

    # ---- White border background + mask ---------------------------------
    border_bg = comp.AddTool("Background", -4, 2)
    border_bg.TopLeftRed[0] = border_bg.TopLeftGreen[0] = border_bg.TopLeftBlue[0] = 1.0
    border_bg.TopLeftAlpha[0] = 1.0

    border_mask = comp.AddTool("RectangleMask", -4, 3)
    border_mask.Width[0]        = card_w + 0.006
    border_mask.Height[0]       = card_h + 0.008
    border_mask.Center[0]       = {1: cx, 2: cy}
    border_mask.CornerRadius[0] = 0.014
    border_mask.SoftEdge[0]     = 0.0
    border_bg.EffectMask        = border_mask   # apply mask

    # ---- Navy card background + mask ------------------------------------
    card_bg = comp.AddTool("Background", -4, 1)
    card_bg.TopLeftRed[0]   = 0.102
    card_bg.TopLeftGreen[0] = 0.169
    card_bg.TopLeftBlue[0]  = 0.290
    card_bg.TopLeftAlpha[0] = 1.0

    card_mask = comp.AddTool("RectangleMask", -4, 0)
    card_mask.Width[0]        = card_w
    card_mask.Height[0]       = card_h
    card_mask.Center[0]       = {1: cx, 2: cy}
    card_mask.CornerRadius[0] = 0.012
    card_mask.SoftEdge[0]     = 0.0
    card_bg.EffectMask        = card_mask

    # ---- Merge: base ← border ← card -----------------------------------
    m0 = comp.AddTool("Merge", -2, 2)
    m0.Background = base
    m0.Foreground  = border_bg

    m1 = comp.AddTool("Merge", -2, 1)
    m1.Background = m0
    m1.Foreground  = card_bg

    # ---- Divider line ---------------------------------------------------
    div_x   = anchor_x - card_w + 0.095
    div_bg  = comp.AddTool("Background", -2, 3)
    div_bg.TopLeftRed[0] = div_bg.TopLeftGreen[0] = div_bg.TopLeftBlue[0] = div_bg.TopLeftAlpha[0] = 1.0
    div_mask = comp.AddTool("RectangleMask", -2, 4)
    div_mask.Width[0]  = 0.0015
    div_mask.Height[0] = card_h * 0.75
    div_mask.Center[0] = {1: div_x, 2: cy}
    div_mask.SoftEdge[0] = 0.0
    div_bg.EffectMask  = div_mask

    m2 = comp.AddTool("Merge", 0, 1)
    m2.Background = m1
    m2.Foreground  = div_bg

    # ---- Text nodes -----------------------------------------------------
    lx = anchor_x - card_w + 0.035
    ty = anchor_y - 0.022
    by = anchor_y - card_h + 0.022

    texts = [
        _make_text(comp, str(hole["number"]),       lx,   ty - 0.008, size=0.085, bold=True),
        _make_text(comp, f"{hole['distance']} yds", lx,   by,          size=0.030, r=.85,g=.85,b=.85),
    ]

    name_x = anchor_x - card_w + 0.19
    texts.append(_make_text(comp, player.upper(), name_x, ty, size=0.048, bold=True, h_align="Left"))

    for s in range(1, total_strokes + 1):
        act = (s == stroke_num)
        texts.append(_make_text(
            comp, str(s), name_x + (s - 1) * 0.038, by,
            size=0.034 if act else 0.030, bold=act,
            r=0.302 if act else 1.0,
            g=0.816 if act else 1.0,
            b=0.882 if act else 1.0,
            h_align="Left",
        ))

    t_score = _make_text(comp, score_before, anchor_x - 0.022, ty - 0.008,
                         size=0.060, bold=True, h_align="Right")
    if is_last:
        _animate_score(t_score, score_before, score_after, fps)
    texts.append(t_score)

    # ---- Merge all text layers on top -----------------------------------
    current = m2
    for t in texts:
        mx = comp.AddTool("Merge", 0, 0)
        mx.Background = current
        mx.Foreground  = t
        current = mx

    # ---- MediaOut -------------------------------------------------------
    out = comp.AddTool("MediaOut", 4, 0)
    out.Input = current


def _make_text(comp, text, x, y, size=0.04, bold=False,
               r=1.0, g=1.0, b=1.0, h_align="Center"):
    t = comp.AddTool("TextPlus")
    t.StyledText[0]          = text
    t.Size[0]                = size
    t.Style                  = "Bold" if bold else "Regular"
    t.HorizontalAnchoring[0] = h_align
    t.Red1[0]  = r
    t.Green1[0]= g
    t.Blue1[0] = b
    t.Center[0] = {1: x, 2: y}
    t.VerticalAnchoring[0] = "Center"
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
    if _win[0]: _win[0].Hide()

if __name__ == "__main__":
    run()
else:
    run()
