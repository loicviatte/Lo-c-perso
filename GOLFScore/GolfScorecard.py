"""
Golf Scorecard Plugin for DaVinci Resolve 20.3
Run from: Workspace > Scripts > Edit > GolfScorecard  (Edit folder recommended)
"""

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


# ── Timeline insertion ─────────────────────────────────────────────────────────
def insert_scorecard(hole_idx, stroke_num):
    # ─ 1. Diagnostics ──────────────────────────────────────
    try:
        page = resolve.GetCurrentPage()
        print(f"[GS] Current page: '{page}'")
    except Exception as e:
        print(f"[GS] GetCurrentPage error: {e}")

    # ─ 2. Switch to Edit page and re-fetch refs ───────────
    resolve.OpenPage("edit")
    time.sleep(0.4)   # allow DR to finish switching

    project  = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline() if project else None

    try:
        page2 = resolve.GetCurrentPage()
        print(f"[GS] Page after switch: '{page2}'")
    except Exception:
        pass

    if timeline is None:
        print("[GS] ERROR: No active timeline after page switch.")
        return

    hole          = state["holes"][hole_idx]
    player        = state["player"] or "PLAYER"
    total_strokes = hole["strokes"]
    is_last       = (stroke_num == total_strokes)
    score_before  = cumulative_score_before(hole_idx)
    score_after   = cumulative_score_after(hole_idx)

    fps = 25.0
    try: fps = float(timeline.GetSetting("timelineFrameRate"))
    except Exception: pass

    print(f"[GS] Insert H{hole['number']} S{stroke_num} | {score_before}->{score_after} | fps={fps}")

    if timeline.GetTrackCount("video") < 2:
        timeline.AddTrack("video")
        print("[GS] Added video track 2")

    # ─ 3. Insert clip ───────────────────────────────────
    item, comp = _try_insert(timeline)
    if comp is None:
        print("[GS] ERROR: Could not insert Fusion clip. See errors above.")
        return

    # ─ 4. Build scorecard nodes ────────────────────────
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


def _try_insert(timeline):
    """Try every known method. Returns (item, comp) or (None, None)."""
    # A — InsertFusionTitleIntoTimeline
    for name in ["Fusion Title", "Blank Fusion Title", ""]:
        try:
            item = timeline.InsertFusionTitleIntoTimeline(name)
            print(f"[GS] InsertFusionTitle('{name}') = {item}")
            if item:
                comp = item.GetFusionCompByIndex(1)
                if comp: return item, comp
        except Exception as e:
            print(f"[GS] InsertFusionTitle('{name}') exception: {e}")

    # B — InsertFusionGeneratorIntoTimeline
    for name in ["Fusion Generator", ""]:
        try:
            item = timeline.InsertFusionGeneratorIntoTimeline(name)
            print(f"[GS] InsertFusionGenerator('{name}') = {item}")
            if item:
                comp = item.GetFusionCompByIndex(1)
                if comp: return item, comp
        except Exception as e:
            print(f"[GS] InsertFusionGenerator('{name}') exception: {e}")

    # C — InsertGeneratorIntoTimeline + AddFusionComp
    for name in ["Solid Color", "Color", "BG", "Background"]:
        try:
            item = timeline.InsertGeneratorIntoTimeline(name)
            print(f"[GS] InsertGenerator('{name}') = {item}")
            if item:
                comp = item.AddFusionComp()
                print(f"[GS]   AddFusionComp() = {comp}")
                if comp: return item, comp
                comp = item.GetFusionCompByIndex(1)
                if comp: return item, comp
        except Exception as e:
            print(f"[GS] InsertGenerator('{name}') exception: {e}")

    return None, None


# ── Fusion node builder ──────────────────────────────────────────────────────────
def _build_scorecard_nodes(comp, hole, player, stroke_num, total_strokes,
                           score_before, score_after, is_last, fps):
    for node in comp.GetToolList().values():
        node.Delete()

    cw, ch       = 0.45, 0.115
    ax, ay       = 0.97, 0.93
    cx, cy       = ax - cw/2, ay - ch/2

    base = comp.AddTool("Background")
    base.TopLeftRed[0]=base.TopLeftGreen[0]=base.TopLeftBlue[0]=base.TopLeftAlpha[0]=0.0

    bbg = comp.AddTool("Background")
    bbg.TopLeftRed[0]=bbg.TopLeftGreen[0]=bbg.TopLeftBlue[0]=bbg.TopLeftAlpha[0]=1.0
    bm = comp.AddTool("RectangleMask")
    bm.Width[0]=cw+0.006; bm.Height[0]=ch+0.008
    bm.Center[0]={1:cx,2:cy}; bm.CornerRadius[0]=0.014; bm.SoftEdge[0]=0.0
    bbg.EffectMask = bm

    cbg = comp.AddTool("Background")
    cbg.TopLeftRed[0]=0.102; cbg.TopLeftGreen[0]=0.169
    cbg.TopLeftBlue[0]=0.290; cbg.TopLeftAlpha[0]=1.0
    cm = comp.AddTool("RectangleMask")
    cm.Width[0]=cw; cm.Height[0]=ch
    cm.Center[0]={1:cx,2:cy}; cm.CornerRadius[0]=0.012; cm.SoftEdge[0]=0.0
    cbg.EffectMask = cm

    m0 = comp.AddTool("Merge")
    m0.Background=base; m0.Foreground=bbg
    m1 = comp.AddTool("Merge")
    m1.Background=m0;   m1.Foreground=cbg

    dx = ax-cw+0.095
    dbg = comp.AddTool("Background")
    dbg.TopLeftRed[0]=dbg.TopLeftGreen[0]=dbg.TopLeftBlue[0]=dbg.TopLeftAlpha[0]=1.0
    dm = comp.AddTool("RectangleMask")
    dm.Width[0]=0.0015; dm.Height[0]=ch*0.75
    dm.Center[0]={1:dx,2:cy}; dm.SoftEdge[0]=0.0
    dbg.EffectMask=dm
    m2=comp.AddTool("Merge"); m2.Background=m1; m2.Foreground=dbg

    lx=ax-cw+0.035; ty=ay-0.022; by=ay-ch+0.022
    nx_=ax-cw+0.19

    texts = [
        _txt(comp, str(hole["number"]),       lx,  ty-0.008, size=0.085, bold=True),
        _txt(comp, f"{hole['distance']} yds", lx,  by,        size=0.030, r=.85,g=.85,b=.85),
        _txt(comp, player.upper(),            nx_, ty,         size=0.048, bold=True, ha="Left"),
    ]
    for s in range(1, total_strokes+1):
        a=(s==stroke_num)
        texts.append(_txt(comp, str(s), nx_+(s-1)*0.038, by,
                          size=0.034 if a else 0.030, bold=a,
                          r=0.302 if a else 1.0,
                          g=0.816 if a else 1.0,
                          b=0.882 if a else 1.0, ha="Left"))
    ts=_txt(comp, score_before, ax-0.022, ty-0.008, size=0.060, bold=True, ha="Right")
    if is_last: _animate(ts, score_before, score_after, fps)
    texts.append(ts)

    cur=m2
    for t in texts:
        mx=comp.AddTool("Merge"); mx.Background=cur; mx.Foreground=t; cur=mx

    out=comp.AddTool("MediaOut")
    out.Input=cur


def _txt(comp, text, x, y, size=0.04, bold=False,
         r=1.0, g=1.0, b=1.0, ha="Center"):
    t=comp.AddTool("TextPlus")
    t.StyledText[0]=text; t.Size[0]=size
    t.Style="Bold" if bold else "Regular"
    t.HorizontalAnchoring[0]=ha
    t.Red1[0]=r; t.Green1[0]=g; t.Blue1[0]=b
    t.Center[0]={1:x,2:y}; t.VerticalAnchoring[0]="Center"
    return t

def _animate(tn, before, after, fps):
    v0,v1=score_to_int(before),score_to_int(after)
    if v0==v1: return
    d=1 if v1>v0 else -1; steps=abs(v1-v0); dur=min(30,int(fps))
    tn.StyledText.MakeCubicSpline()
    for i in range(steps+1):
        v=v0+d*i
        tn.StyledText[int(i*dur/steps)]="E" if v==0 else (f"+{v}" if v>0 else str(v))


# ── Entry point ───────────────────────────────────────────────────────────────
def run():
    make_window()
    disp.RunLoop()
    if _win[0]: _win[0].Hide()

if __name__ == "__main__": run()
else: run()
