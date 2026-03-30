"""
Golf Scorecard Plugin for DaVinci Resolve 20.3
Run from: Workspace > Scripts > Edit > GolfScorecard  (or Utility/)
"""

import os
import sys
import time

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

# Fusion title template path — written before each insert
TEMPLATE_DIR = os.path.expanduser(
    "~/Library/Application Support/Blackmagic Design/"
    "DaVinci Resolve/Fusion/Templates/Edit/Titles/GolfScorecard"
)
TEMPLATE_PATH = os.path.join(TEMPLATE_DIR, "GolfScorecard.setting")

# ── Score helpers ──────────────────────────────────────────────────────────
def calc_score_str(st, pt):
    d = st - pt
    if d == 0: return "E"
    return f"+{d}" if d > 0 else str(d)

def cumulative_score_before(i):
    return calc_score_str(
        sum(h["strokes"] for h in state["holes"][:i]),
        sum(h["par"]     for h in state["holes"][:i]))

def cumulative_score_after(i):
    return calc_score_str(
        sum(h["strokes"] for h in state["holes"][:i+1]),
        sum(h["par"]     for h in state["holes"][:i+1]))

def score_to_int(s):
    if s == "E": return 0
    return int(s.replace("+", ""))


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
                ui.Label({"Text": f"HOLE {h['number']}", "StyleSheet": STYLE_HOLE_H, "Weight": 0}),
                ui.Label({"Text": "", "Weight": 1}),
                ui.Button({"Text": "Delete", "ID": f"del_{idx}", "StyleSheet": STYLE_BTN_DEL, "Weight": 0}),
            ]),
            ui.HGroup({"Spacing": 4, "Weight": 0}, [
                ui.Label({"Text": "PAR",          "StyleSheet": STYLE_LABEL, "Weight": 0}),
                ui.SpinBox({"ID": f"par_{idx}",   "Value": h["par"],      "Minimum": 3,  "Maximum": 6,   "Weight": 0}),
                ui.Label({"Text": "  Dist (yds)", "StyleSheet": STYLE_LABEL, "Weight": 0}),
                ui.SpinBox({"ID": f"dist_{idx}",  "Value": h["distance"], "Minimum": 50, "Maximum": 700, "Weight": 0}),
                ui.Label({"Text": "  Strokes",    "StyleSheet": STYLE_LABEL, "Weight": 0}),
                ui.SpinBox({"ID": f"str_{idx}",   "Value": h["strokes"],  "Minimum": 1,  "Maximum": 15,  "Weight": 0}),
            ]),
        ]
        for s in range(1, h["strokes"] + 1):
            il = (s == h["strokes"])
            rows.append(ui.Button({
                "Text": f"Stroke {s}{'  \u2605' if il else ''} \u2192 Insert at Playhead",
                "ID":   f"ins_{idx}_{s}",
                "StyleSheet": STYLE_BTN_LAST if il else STYLE_BTN_INS,
            }))
        widgets.append(ui.VGroup({"Spacing": 6, "Weight": 0, "StyleSheet": STYLE_CARD}, rows))
        widgets.append(ui.Label({"Text": "", "StyleSheet": STYLE_DIVIDER, "Weight": 0}))
    return widgets


def _save_player(win):
    f = win.Find("player_name")
    if f: state["player"] = f.Text

def _sync(win):
    for i, h in enumerate(state["holes"]):
        for key, fid in (("par",f"par_{i}"),("distance",f"dist_{i}"),("strokes",f"str_{i}")):
            f = win.Find(fid)
            if f: h[key] = f.Value


def make_window():
    if _win[0]:
        _save_player(_win[0])
        _win[0].Hide()
    _win_n[0] += 1
    wid = f"GS{_win_n[0]}"

    body = [
        ui.Label({"Text": "GOLF SCORECARD", "Alignment": {"AlignHCenter": True},
                  "StyleSheet": "color:#4DD0E1; font-size:18px; font-weight:bold; padding:8px 0;", "Weight": 0}),
        ui.Label({"Text": "", "StyleSheet": STYLE_DIVIDER, "Weight": 0}),
        ui.HGroup({"Spacing": 8, "Weight": 0}, [
            ui.Label({"Text": "Player", "StyleSheet": STYLE_LABEL, "Weight": 0}),
            ui.LineEdit({"ID": "player_name", "Text": state["player"],
                         "PlaceholderText": "Player name", "StyleSheet": STYLE_INPUT}),
        ]),
        ui.Button({"ID": "add_hole", "Text": "+ Add Hole",
                   "StyleSheet": STYLE_BTN_ADD, "Weight": 0}),
    ] + _hole_widgets() + [ui.VGap(0)]

    win = disp.AddWindow(
        {"ID": wid, "WindowTitle": "Golf Scorecard",
         "Geometry": [100, 100, 480, 680], "StyleSheet": STYLE_WINDOW},
        [ui.VGroup({"Spacing": 6, "Weight": 1}, body)]
    )
    _win[0] = win
    win.On[wid].Close = lambda ev: disp.ExitLoop()

    def on_add(ev):
        _save_player(win)
        state["holes"].append({"number": len(state["holes"])+1, "par": 4, "distance": 350, "strokes": 4})
        make_window()
    win.On["add_hole"].Clicked = on_add

    for i in range(len(state["holes"])):
        def mk_del(idx):
            def h(ev):
                _save_player(win); _sync(win)
                state["holes"].pop(idx)
                for j, hh in enumerate(state["holes"]): hh["number"] = j+1
                make_window()
            return h
        win.On[f"del_{i}"].Clicked = mk_del(i)

    for i, h in enumerate(state["holes"]):
        for s in range(1, h["strokes"]+1):
            def mk_ins(hi, sn):
                def h(ev):
                    _save_player(win); _sync(win)
                    insert_scorecard(hi, sn)
                return h
            win.On[f"ins_{i}_{s}"].Clicked = mk_ins(i, s)

    win.Show()
    return win


# ── Fusion .setting file generator ───────────────────────────────────────────
def _s_bg(name, r, g, b, a, mask=None):
    mline = f"""
				EffectMask = Input {{
					SourceOp = "{mask}",
					Source = "Mask",
				}},""" if mask else ""
    return (f"\t\t{name} = Background {{\n"
            f"\t\t\tNameSet = true,\n"
            f"\t\t\tInputs = {{\n"
            f"\t\t\t\tTopLeftRed   = Input {{ Value = {r}, }},\n"
            f"\t\t\t\tTopLeftGreen = Input {{ Value = {g}, }},\n"
            f"\t\t\t\tTopLeftBlue  = Input {{ Value = {b}, }},\n"
            f"\t\t\t\tTopLeftAlpha = Input {{ Value = {a}, }},{mline}\n"
            f"\t\t\t}},\n"
            f"\t\t}}")

def _s_rect(name, w, h, cx, cy, corner=0.0):
    return (f"\t\t{name} = RectangleMask {{\n"
            f"\t\t\tNameSet = true,\n"
            f"\t\t\tInputs = {{\n"
            f"\t\t\t\tWidth        = Input {{ Value = {w}, }},\n"
            f"\t\t\t\tHeight       = Input {{ Value = {h}, }},\n"
            f"\t\t\t\tCenter       = Input {{ Value = {{ {cx}, {cy} }}, }},\n"
            f"\t\t\t\tCornerRadius = Input {{ Value = {corner}, }},\n"
            f"\t\t\t\tSoftEdge     = Input {{ Value = 0, }},\n"
            f"\t\t\t}},\n"
            f"\t\t}}")

def _s_text(name, text, x, y, size, bold, r, g, b, ha=1):
    # ha: 0=Left  1=Center  2=Right
    style = "Bold" if bold else "Regular"
    txt = text.replace("\\", "\\\\").replace('"', '\\"')
    return (f"\t\t{name} = TextPlus {{\n"
            f"\t\t\tNameSet = true,\n"
            f"\t\t\tInputs = {{\n"
            f"\t\t\t\tUseFrameFormatSettings = Input {{ Value = 1, }},\n"
            f"\t\t\t\tStyledText          = Input {{ Value = \"{txt}\", }},\n"
            f"\t\t\t\tSize                = Input {{ Value = {size}, }},\n"
            f"\t\t\t\tStyle               = Input {{ Value = \"{style}\", }},\n"
            f"\t\t\t\tHorizontalAnchoring = Input {{ Value = {ha}, }},\n"
            f"\t\t\t\tVerticalAnchoring   = Input {{ Value = 1, }},\n"
            f"\t\t\t\tCenter              = Input {{ Value = {{ {x}, {y} }}, }},\n"
            f"\t\t\t\tRed1   = Input {{ Value = {r}, }},\n"
            f"\t\t\t\tGreen1 = Input {{ Value = {g}, }},\n"
            f"\t\t\t\tBlue1  = Input {{ Value = {b}, }},\n"
            f"\t\t\t}},\n"
            f"\t\t}}")

def _s_merge(name, bg, fg):
    return (f"\t\t{name} = Merge {{\n"
            f"\t\t\tNameSet = true,\n"
            f"\t\t\tInputs = {{\n"
            f"\t\t\t\tBackground = Input {{ SourceOp = \"{bg}\", Source = \"Output\", }},\n"
            f"\t\t\t\tForeground = Input {{ SourceOp = \"{fg}\", Source = \"Output\", }},\n"
            f"\t\t\t}},\n"
            f"\t\t}}")

def _s_out(src):
    return (f"\t\tMediaOut1 = MediaOutput {{\n"
            f"\t\t\tNameSet = true,\n"
            f"\t\t\tInputs = {{\n"
            f"\t\t\t\tInput = Input {{ SourceOp = \"{src}\", Source = \"Output\", }},\n"
            f"\t\t\t}},\n"
            f"\t\t}}")


def generate_scorecard_setting(hole, player, stroke_num, total_strokes, score):
    """Return a complete Fusion .setting file string for the scorecard."""
    cw, ch = 0.45, 0.115
    ax, ay = 0.97, 0.93
    cx, cy = ax - cw/2, ay - ch/2
    lx  = ax - cw + 0.035
    ty  = ay - 0.022
    by  = ay - ch + 0.022
    nx_ = ax - cw + 0.19
    dx  = ax - cw + 0.095

    parts = []

    # Backgrounds & masks
    parts += [
        _s_bg("BaseBG", 0, 0, 0, 0),
        _s_rect("BorderMask", round(cw+0.006, 6), round(ch+0.008, 6), round(cx, 6), round(cy, 6), 0.014),
        _s_bg("BorderBG", 1, 1, 1, 1, "BorderMask"),
        _s_rect("CardMask",   round(cw, 6),       round(ch, 6),       round(cx, 6), round(cy, 6), 0.012),
        _s_bg("CardBG", 0.102, 0.169, 0.290, 1, "CardMask"),
        _s_rect("DivMask", 0.0015, round(ch*0.75, 6), round(dx, 6), round(cy, 6)),
        _s_bg("DivBG", 1, 1, 1, 1, "DivMask"),
    ]

    # Layer merges: base → border → card → divider
    parts += [
        _s_merge("M1", "BaseBG", "BorderBG"),
        _s_merge("M2", "M1", "CardBG"),
        _s_merge("M3", "M2", "DivBG"),
    ]

    # Text nodes
    parts.append(_s_text("HoleNum",   str(hole["number"]),           round(lx, 6),  round(ty-0.008, 6), 0.085, True,  1,    1,    1,    0))
    parts.append(_s_text("DistTxt",   f"{hole['distance']} yds",     round(lx, 6),  round(by, 6),       0.030, False, 0.85, 0.85, 0.85, 0))
    parts.append(_s_text("PlayerTxt", (player or "PLAYER").upper(),  round(nx_, 6), round(ty, 6),       0.048, True,  1,    1,    1,    0))

    stroke_names = []
    for s in range(1, total_strokes + 1):
        act = (s == stroke_num)
        sname = f"S{s}T"
        r, g, b = (0.302, 0.816, 0.882) if act else (1.0, 1.0, 1.0)
        sz = 0.034 if act else 0.030
        parts.append(_s_text(sname, str(s), round(nx_+(s-1)*0.038, 6), round(by, 6), sz, act, r, g, b, 0))
        stroke_names.append(sname)

    parts.append(_s_text("ScoreTxt", score, round(ax-0.022, 6), round(ty-0.008, 6), 0.060, True, 1, 1, 1, 2))

    # Merge all text layers onto M3
    cur = "M3"
    for i, tname in enumerate(["HoleNum", "DistTxt", "PlayerTxt"] + stroke_names + ["ScoreTxt"]):
        mname = f"MT{i+1}"
        parts.append(_s_merge(mname, cur, tname))
        cur = mname

    parts.append(_s_out(cur))

    tool_block = ",\n".join(parts)
    return "{\n\tTools = ordered() {\n" + tool_block + "\n\t},\n}\n"


def write_scorecard_template(hole, player, stroke_num, total_strokes, score):
    """Write the .setting template and return True on success."""
    try:
        os.makedirs(TEMPLATE_DIR, exist_ok=True)
        content = generate_scorecard_setting(hole, player, stroke_num, total_strokes, score)
        with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[GS] Template written → {TEMPLATE_PATH}")
        return True
    except Exception as e:
        print(f"[GS] ERROR writing template: {e}")
        return False


# ── Timeline insertion ────────────────────────────────────────────────────────
def insert_scorecard(hole_idx, stroke_num):
    hole          = state["holes"][hole_idx]
    player        = state["player"] or "PLAYER"
    total_strokes = hole["strokes"]
    is_last       = (stroke_num == total_strokes)
    score_before  = cumulative_score_before(hole_idx)
    score_after   = cumulative_score_after(hole_idx)
    # Static score shown in the template (animation added later for last stroke)
    static_score  = score_after if is_last else score_before

    # 1. Generate .setting template with all nodes pre-built
    if not write_scorecard_template(hole, player, stroke_num, total_strokes, static_score):
        print("[GS] Aborting: could not write template.")
        return

    # 2. Switch to Edit page and wait
    print(f"[GS] Switching to Edit page…")
    resolve.OpenPage("edit")
    time.sleep(0.6)

    # 3. Re-fetch refs after page switch
    pm       = resolve.GetProjectManager()
    project  = pm.GetCurrentProject() if pm else None
    timeline = project.GetCurrentTimeline() if project else None

    try:
        page = resolve.GetCurrentPage()
        print(f"[GS] Active page: '{page}'")
    except Exception:
        pass

    if not timeline:
        print("[GS] ERROR: No active timeline.")
        return

    fps = 25.0
    try: fps = float(timeline.GetSetting("timelineFrameRate"))
    except Exception: pass

    print(f"[GS] Timeline: '{timeline.GetName()}' | fps={fps}")
    print(f"[GS] Video tracks: {timeline.GetTrackCount('video')}")
    print(f"[GS] Hole={hole['number']} Stroke={stroke_num}/{total_strokes} Score: {score_before}→{score_after}")

    # Ensure at least 2 video tracks so we can put overlay on track 2
    while timeline.GetTrackCount("video") < 2:
        timeline.AddTrack("video")
        print("[GS] Added video track")

    # 4. Insert Fusion title using our pre-written template
    item = None
    try:
        item = timeline.InsertFusionTitleIntoTimeline("GolfScorecard")
        print(f"[GS] InsertFusionTitle('GolfScorecard') → {item}")
    except Exception as e:
        print(f"[GS] InsertFusionTitle exception: {e}")

    # 5. If template insert failed, try all fallbacks (post-modify comp)
    if item is None:
        print("[GS] Template insert returned None — trying fallbacks…")
        item, comp = _try_fallbacks(timeline)
        if comp is not None:
            comp.Lock()
            try:
                _build_scorecard_nodes(comp, hole, player, stroke_num, total_strokes,
                                       score_before, score_after, is_last, fps)
                print("[GS] Scorecard built via fallback node API.")
            except Exception as e:
                print(f"[GS] ERROR building nodes: {e}")
                import traceback; traceback.print_exc()
            finally:
                comp.Unlock()
            return
        print("[GS] ERROR: All insert methods failed. Check console for details.")
        return

    # 6. Template insert succeeded — optionally add score animation on last stroke
    if is_last:
        try:
            comp = item.GetFusionCompByIndex(1)
            if comp:
                ts = comp.FindTool("ScoreTxt")
                if ts:
                    comp.Lock()
                    try:
                        _animate(ts, score_before, score_after, fps)
                        print("[GS] Score animation applied.")
                    finally:
                        comp.Unlock()
        except Exception as e:
            print(f"[GS] Animation warning (non-fatal): {e}")

    print("[GS] Scorecard inserted successfully.")


def _try_fallbacks(timeline):
    """Try every known insert method. Returns (item, comp) or (None, None)."""
    # A — Fusion Title variants
    for name in ("Fusion Title", "Blank Fusion Title", ""):
        try:
            item = timeline.InsertFusionTitleIntoTimeline(name)
            print(f"[GS]   InsertFusionTitle('{name}') → {item}")
            if item:
                comp = item.GetFusionCompByIndex(1)
                if comp: return item, comp
        except Exception as e:
            print(f"[GS]   InsertFusionTitle('{name}') error: {e}")

    # B — Fusion Generator
    for name in ("Fusion Generator", ""):
        try:
            item = timeline.InsertFusionGeneratorIntoTimeline(name)
            print(f"[GS]   InsertFusionGenerator('{name}') → {item}")
            if item:
                comp = item.GetFusionCompByIndex(1)
                if comp: return item, comp
        except Exception as e:
            print(f"[GS]   InsertFusionGenerator('{name}') error: {e}")

    # C — Standard generator + AddFusionComp
    for name in ("Solid Color", "Color", "BG", "Background", ""):
        try:
            item = timeline.InsertGeneratorIntoTimeline(name)
            print(f"[GS]   InsertGenerator('{name}') → {item}")
            if item:
                comp = item.AddFusionComp()
                print(f"[GS]     AddFusionComp() → {comp}")
                if comp: return item, comp
                comp = item.GetFusionCompByIndex(1)
                if comp: return item, comp
        except Exception as e:
            print(f"[GS]   InsertGenerator('{name}') error: {e}")

    return None, None


# ── Fusion node builder (used by fallback path) ───────────────────────────────
def _build_scorecard_nodes(comp, hole, player, stroke_num, total_strokes,
                           score_before, score_after, is_last, fps):
    for node in list(comp.GetToolList().values()):
        node.Delete()

    cw, ch = 0.45, 0.115
    ax, ay = 0.97, 0.93
    cx, cy = ax - cw/2, ay - ch/2

    base = comp.AddTool("Background")
    base.TopLeftRed[0] = base.TopLeftGreen[0] = base.TopLeftBlue[0] = base.TopLeftAlpha[0] = 0.0

    bm = comp.AddTool("RectangleMask")
    bm.Width[0] = cw+0.006; bm.Height[0] = ch+0.008
    bm.Center[0] = {1: cx, 2: cy}; bm.CornerRadius[0] = 0.014; bm.SoftEdge[0] = 0.0
    bbg = comp.AddTool("Background")
    bbg.TopLeftRed[0] = bbg.TopLeftGreen[0] = bbg.TopLeftBlue[0] = bbg.TopLeftAlpha[0] = 1.0
    bbg.EffectMask = bm

    cm = comp.AddTool("RectangleMask")
    cm.Width[0] = cw; cm.Height[0] = ch
    cm.Center[0] = {1: cx, 2: cy}; cm.CornerRadius[0] = 0.012; cm.SoftEdge[0] = 0.0
    cbg = comp.AddTool("Background")
    cbg.TopLeftRed[0] = 0.102; cbg.TopLeftGreen[0] = 0.169
    cbg.TopLeftBlue[0] = 0.290; cbg.TopLeftAlpha[0] = 1.0
    cbg.EffectMask = cm

    m0 = comp.AddTool("Merge"); m0.Background = base; m0.Foreground = bbg
    m1 = comp.AddTool("Merge"); m1.Background = m0;   m1.Foreground = cbg

    dx = ax - cw + 0.095
    dm = comp.AddTool("RectangleMask")
    dm.Width[0] = 0.0015; dm.Height[0] = ch*0.75
    dm.Center[0] = {1: dx, 2: cy}; dm.SoftEdge[0] = 0.0
    dbg = comp.AddTool("Background")
    dbg.TopLeftRed[0] = dbg.TopLeftGreen[0] = dbg.TopLeftBlue[0] = dbg.TopLeftAlpha[0] = 1.0
    dbg.EffectMask = dm
    m2 = comp.AddTool("Merge"); m2.Background = m1; m2.Foreground = dbg

    lx = ax - cw + 0.035; ty = ay - 0.022; by = ay - ch + 0.022
    nx_ = ax - cw + 0.19

    def txt(text, x, y, size=0.04, bold=False, r=1.0, g=1.0, b=1.0, ha="Center"):
        t = comp.AddTool("TextPlus")
        t.StyledText[0] = text; t.Size[0] = size
        t.Style = "Bold" if bold else "Regular"
        t.HorizontalAnchoring[0] = ha
        t.Red1[0] = r; t.Green1[0] = g; t.Blue1[0] = b
        t.Center[0] = {1: x, 2: y}; t.VerticalAnchoring[0] = "Center"
        return t

    score = score_after if is_last else score_before
    texts = [
        txt(str(hole["number"]),          lx,  ty-0.008, 0.085, True),
        txt(f"{hole['distance']} yds",    lx,  by,        0.030, False, 0.85, 0.85, 0.85),
        txt((player or "PLAYER").upper(), nx_, ty,        0.048, True,  ha="Left"),
    ]
    for s in range(1, total_strokes+1):
        act = (s == stroke_num)
        texts.append(txt(str(s), nx_+(s-1)*0.038, by,
                         0.034 if act else 0.030, act,
                         0.302 if act else 1.0,
                         0.816 if act else 1.0,
                         0.882 if act else 1.0, "Left"))
    ts = txt(score, ax-0.022, ty-0.008, 0.060, True, ha="Right")
    if is_last: _animate(ts, score_before, score_after, fps)
    texts.append(ts)

    cur = m2
    for t in texts:
        mx = comp.AddTool("Merge"); mx.Background = cur; mx.Foreground = t; cur = mx

    out = comp.AddTool("MediaOut")
    out.Input = cur


def _animate(tn, before, after, fps):
    v0, v1 = score_to_int(before), score_to_int(after)
    if v0 == v1: return
    d = 1 if v1 > v0 else -1
    steps = abs(v1 - v0)
    dur   = min(30, int(fps))
    try:
        tn.StyledText.MakeCubicSpline()
        for i in range(steps + 1):
            v = v0 + d * i
            frame = int(i * dur / steps)
            tn.StyledText[frame] = "E" if v == 0 else (f"+{v}" if v > 0 else str(v))
    except Exception as e:
        print(f"[GS] Animation keyframe error: {e}")


# ── Entry point ────────────────────────────────────────────────────────────────
def run():
    make_window()
    disp.RunLoop()
    if _win[0]: _win[0].Hide()

if __name__ == "__main__": run()
else: run()
