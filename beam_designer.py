"""Tkinter desktop implementation of the Beam Designer specification."""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Callable, Iterable


@dataclass(frozen=True)
class Section:
    name: str
    ix: float
    sx: float
    weight: float | None = None


MATERIALS = {
    "steel": {
        "name": "Steel W-shapes", "e": 29000.0, "fb": 30.0,
        "sections": [
            Section("W8x10", 30.8, 7.81, 10), Section("W10x12", 53.8, 10.9, 12),
            Section("W12x26", 204, 33.4, 26), Section("W14x22", 199, 29.0, 22),
            Section("W16x26", 301, 38.4, 26), Section("W18x35", 510, 57.6, 35),
            Section("W21x44", 843, 81.6, 44), Section("W24x55", 1350, 114, 55),
        ],
    },
    "wood": {
        "name": "Douglas Fir-Larch No. 2", "e": 1600.0, "fb": 0.900,
        "sections": [Section("2x8", 47.63, 13.14), Section("2x10", 98.93, 21.39), Section("2x12", 177.98, 31.64)],
    },
}


def number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def load_error(kind: str, load: dict[str, object]) -> str:
    magnitude = number(load.get("magnitude"))
    if magnitude is None or magnitude < 0:
        return "Enter a nonnegative load magnitude."
    if kind == "point":
        position = number(load.get("position"))
        return "" if position is not None and position >= 0 else "Enter a valid nonnegative position."
    start, end = number(load.get("start")), number(load.get("end"))
    if start is None or end is None or start < 0 or end < 0:
        return "Enter valid nonnegative start and end positions."
    return "" if end > start else "End position must be greater than start position."


def effective_loads(state: dict) -> tuple[list[dict], list[dict]]:
    points, uniforms = [], []
    for load in state["point_loads"]:
        magnitude, position = number(load["magnitude"]), number(load["position"])
        if magnitude is not None and magnitude >= 0 and position is not None and position >= 0:
            points.append({"magnitude": magnitude, "position": clamp(position, 0, state["span"])})
    for load in state["uniform_loads"]:
        if load_error("uniform", load):
            continue
        start = clamp(float(load["start"]), 0, state["span"])
        end = clamp(float(load["end"]), 0, state["span"])
        if end > start:
            uniforms.append({"magnitude": float(load["magnitude"]), "start": start, "end": end})
    return points, uniforms


def reactions(loads: tuple[list[dict], list[dict]], support: str, span: float) -> dict:
    points, uniforms = loads
    point_total = sum(x["magnitude"] for x in points)
    uniform_total = sum(x["magnitude"] * (x["end"] - x["start"]) for x in uniforms)
    point_moment = sum(x["magnitude"] * x["position"] for x in points)
    uniform_moment = sum(x["magnitude"] * (x["end"] - x["start"]) * (x["start"] + x["end"]) / 2 for x in uniforms)
    total, moment = point_total + uniform_total, point_moment + uniform_moment
    if support == "cantilever":
        return {"a": total, "b": None, "fixed": moment}
    b = moment / span
    return {"a": total - b, "b": b, "fixed": 0.0}


def shear_at(x: float, side: str, analysis: dict) -> float:
    value = analysis["reactions"]["a"]
    for load in analysis["loads"][0]:
        if load["position"] < x or load["position"] == x and side == "right":
            value -= load["magnitude"]
    for load in analysis["loads"][1]:
        value -= load["magnitude"] * max(0.0, min(x, load["end"]) - load["start"])
    return value


def moment_at(x: float, analysis: dict) -> float:
    value = -analysis["reactions"]["fixed"] if analysis["support"] == "cantilever" else 0.0
    value += analysis["reactions"]["a"] * x
    for load in analysis["loads"][0]:
        value -= load["magnitude"] * max(0.0, x - load["position"])
    for load in analysis["loads"][1]:
        end = min(x, load["end"])
        length = max(0.0, end - load["start"])
        value -= load["magnitude"] * length * (x - (load["start"] + end) / 2)
    return value


def breakpoints(analysis: dict) -> list[float]:
    values = {0.0, analysis["span"]}
    for load in analysis["loads"][0]:
        values.add(load["position"])
    for load in analysis["loads"][1]:
        values.update((load["start"], load["end"]))
    return sorted(values)


def max_by_abs(values: Iterable[dict]) -> dict:
    return max(values, key=lambda item: abs(item["value"]))


def bisect_root(function: Callable[[float], float], low: float, high: float) -> float:
    low_value = function(low)
    for _ in range(60):
        middle = (low + high) / 2
        middle_value = function(middle)
        if middle_value == 0:
            return middle
        if low_value * middle_value > 0:
            low, low_value = middle, middle_value
        else:
            high = middle
    return (low + high) / 2


def maximum_shear(analysis: dict, points: list[float]) -> dict:
    candidates = []
    for x in points:
        if x == 0:
            candidates.append({"x": x, "value": shear_at(x, "right", analysis)})
        elif x == analysis["span"]:
            candidates.append({"x": x, "value": shear_at(x, "left", analysis)})
        else:
            candidates.extend(({"x": x, "value": shear_at(x, "left", analysis)}, {"x": x, "value": shear_at(x, "right", analysis)}))
    return max_by_abs(candidates)


def maximum_moment(analysis: dict, points: list[float]) -> dict:
    candidates = [{"x": x, "value": moment_at(x, analysis)} for x in points]
    for low, high in zip(points, points[1:]):
        shear_low, shear_high = shear_at(low, "right", analysis), shear_at(high, "left", analysis)
        if shear_low and shear_high and shear_low * shear_high < 0:
            root = bisect_root(lambda x: shear_at(x, "right", analysis), low, high)
            candidates.append({"x": root, "value": moment_at(root, analysis)})
    return max_by_abs(candidates)


def first_integral(x: float, analysis: dict) -> float:
    result = -analysis["reactions"]["fixed"] * x + analysis["reactions"]["a"] * x**2 / 2
    for load in analysis["loads"][0]:
        result -= load["magnitude"] * max(0.0, x - load["position"])**2 / 2
    for load in analysis["loads"][1]:
        result -= load["magnitude"] * max(0.0, x - load["start"])**3 / 6
        result += load["magnitude"] * max(0.0, x - load["end"])**3 / 6
    return result


def second_integral(x: float, analysis: dict) -> float:
    result = -analysis["reactions"]["fixed"] * x**2 / 2 + analysis["reactions"]["a"] * x**3 / 6
    for load in analysis["loads"][0]:
        result -= load["magnitude"] * max(0.0, x - load["position"])**3 / 6
    for load in analysis["loads"][1]:
        result -= load["magnitude"] * max(0.0, x - load["start"])**4 / 24
        result += load["magnitude"] * max(0.0, x - load["end"])**4 / 24
    return result


def deflection_shape(x: float, analysis: dict) -> float:
    shape = second_integral(x, analysis)
    return shape - x / analysis["span"] * second_integral(analysis["span"], analysis) if analysis["support"] == "simple" else shape


def slope_numerator(x: float, analysis: dict) -> float:
    slope = first_integral(x, analysis)
    return slope - second_integral(analysis["span"], analysis) / analysis["span"] if analysis["support"] == "simple" else slope


def maximum_deflection_shape(analysis: dict) -> dict:
    stations = sorted({round(min(i * 0.1, analysis["span"]), 10) for i in range(math.ceil(analysis["span"] / 0.1) + 1)} | set(breakpoints(analysis)))
    candidates = [{"x": x, "value": deflection_shape(x, analysis)} for x in stations]
    for low, high in zip(stations, stations[1:]):
        slope_low, slope_high = slope_numerator(low, analysis), slope_numerator(high, analysis)
        if slope_low and slope_high and slope_low * slope_high < 0:
            root = bisect_root(lambda x: slope_numerator(x, analysis), low, high)
            candidates.append({"x": root, "value": deflection_shape(root, analysis)})
    return max_by_abs(candidates)


def analyze(state: dict) -> dict:
    loads = effective_loads(state)
    result = {"support": state["support"], "span": state["span"], "loads": loads,
              "reactions": reactions(loads, state["support"], state["span"])}
    points = breakpoints(result)
    result["max_shear"], result["max_moment"] = maximum_shear(result, points), maximum_moment(result, points)
    result["maximum_shape"] = maximum_deflection_shape(result)
    material = MATERIALS[state["material"]]
    section = next(s for s in material["sections"] if s.name == state["section"])
    result["max_deflection"] = {"x": result["maximum_shape"]["x"], "value": -1728 * result["maximum_shape"]["value"] / (material["e"] * section.ix)}
    result["checks"] = checks(state, result, section)
    passing = []
    for candidate in material["sections"]:
        candidate_checks = checks(state, result, candidate)
        if candidate_checks["bending"]["passes"] and candidate_checks["deflection"]["passes"]:
            passing.append((candidate, candidate_checks))
    if state["material"] == "steel":
        passing.sort(key=lambda item: (item[0].weight, -item[0].ix))
    result["recommendation"] = passing[0] if passing else None
    return result


def checks(state: dict, analysis: dict, section: Section) -> dict:
    material = MATERIALS[state["material"]]
    bending = abs(analysis["max_moment"]["value"]) * 12 / section.sx
    deflection = abs(-1728 * analysis["maximum_shape"]["value"] / (material["e"] * section.ix))
    allowable_deflection = state["span"] * 12 / state["deflection_limit"]
    return {
        "bending": {"actual": bending, "allowable": material["fb"], "ratio": bending / material["fb"], "passes": bending <= material["fb"]},
        "deflection": {"actual": deflection, "allowable": allowable_deflection, "ratio": deflection / allowable_deflection, "passes": deflection <= allowable_deflection},
    }


class BeamDesigner(tk.Tk):
    BLUE, PALE, INK, WOOD, GOLD = "#002e5d", "#e9f1f8", "#172635", "#432819", "#d3ae79"

    def __init__(self) -> None:
        super().__init__()
        self.title("Beam Designer | Tkinter Live Analysis")
        self.geometry("1440x940")
        self.minsize(1160, 760)
        self.configure(bg=self.PALE)
        self.state = {"support": "simple", "span": 20.0, "material": "steel", "section": "W12x26", "deflection_limit": 360.0,
                      "point_loads": [], "uniform_loads": [{"id": 1, "magnitude": 1.0, "start": 0.0, "end": 20.0}]}
        self.load_id = 2
        self.vars: dict[str, tk.Variable] = {}
        self.load_widgets: list[tuple[str, dict, list[tk.StringVar], tk.Label]] = []
        self.crosshair_x: float | None = None
        self.build_style()
        self.build_ui()
        self.refresh()

    def build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=self.PALE)
        style.configure("Card.TFrame", background="white", relief="solid", borderwidth=1)
        style.configure("TLabel", background=self.PALE, foreground=self.INK, font=("Georgia", 10))
        style.configure("Title.TLabel", background=self.BLUE, foreground="white", font=("Georgia", 20, "bold"))
        style.configure("Head.TLabel", background="white", foreground=self.BLUE, font=("Georgia", 13, "bold"))
        style.configure("TButton", font=("Georgia", 10), padding=5)
        style.configure("Accent.TButton", background=self.BLUE, foreground="white")
        style.configure("TCombobox", padding=3)

    def build_ui(self) -> None:
        header = tk.Frame(self, bg=self.BLUE, height=72, padx=20, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="BEAM DESIGNER", bg=self.BLUE, fg="white", font=("Georgia", 21, "bold")).pack(side="left")
        tk.Label(header, text="BRIGHAM YOUNG UNIVERSITY  •  LIVE ANALYSIS", bg=self.BLUE, fg="#b9d3e8", font=("Georgia", 10)).pack(side="right", pady=9)
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)
        self.left = ttk.Frame(outer, style="Card.TFrame", padding=14, width=360)
        self.left.pack(side="left", fill="y", padx=(0, 14))
        self.left.pack_propagate(False)
        right = ttk.Frame(outer, style="Card.TFrame", padding=12)
        right.pack(side="left", fill="both", expand=True)
        self.build_controls()
        self.canvas = tk.Canvas(right, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.draw())
        self.canvas.bind("<Motion>", self.inspect)
        self.canvas.bind("<Leave>", lambda _event: self.clear_inspection())

    def label(self, parent: tk.Widget, text: str) -> None:
        ttk.Label(parent, text=text, style="Head.TLabel").pack(anchor="w", pady=(8, 5))

    def build_controls(self) -> None:
        self.label(self.left, "BEAM SETUP")
        form = ttk.Frame(self.left, style="Card.TFrame")
        form.pack(fill="x")
        self.vars["support"] = tk.StringVar(value="Simply supported")
        self.vars["material"] = tk.StringVar(value="Steel W-shapes")
        self.vars["section"] = tk.StringVar(value="W12x26")
        self.vars["limit"] = tk.StringVar(value="L/360")
        self.add_combo(form, "Support", "support", ["Simply supported", "Cantilever"], self.on_setup)
        self.vars["span"] = tk.DoubleVar(value=20)
        ttk.Label(form, text="Span (ft)").pack(anchor="w")
        span_row = ttk.Frame(form)
        span_row.pack(fill="x", pady=(0, 5))
        ttk.Scale(span_row, from_=4, to=40, variable=self.vars["span"], command=lambda _v: self.on_setup()).pack(side="left", fill="x", expand=True)
        ttk.Entry(span_row, textvariable=self.vars["span"], width=7).pack(side="right", padx=(6, 0))
        self.add_combo(form, "Material", "material", ["Steel W-shapes", "Douglas Fir-Larch No. 2"], self.on_material)
        self.add_combo(form, "Section", "section", [], self.on_setup)
        self.add_combo(form, "Deflection limit", "limit", ["L/240", "L/360"], self.on_setup)
        self.label(self.left, "LOADS")
        self.load_frame = ttk.Frame(self.left, style="Card.TFrame")
        self.load_frame.pack(fill="both", expand=True)
        buttons = ttk.Frame(self.left)
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="+ Point load", command=lambda: self.add_load("point")).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(buttons, text="+ Uniform load", command=lambda: self.add_load("uniform")).pack(side="left", fill="x", expand=True)
        self.status = tk.Label(self.left, text="", bg=self.PALE, fg="#a33a36", justify="left", anchor="w", wraplength=320, font=("Georgia", 9))
        self.status.pack(fill="x")

    def add_combo(self, parent: tk.Widget, text: str, key: str, values: list[str], callback: Callable) -> None:
        ttk.Label(parent, text=text).pack(anchor="w")
        combo = ttk.Combobox(parent, textvariable=self.vars[key], values=values, state="readonly")
        combo.pack(fill="x", pady=(0, 5))
        combo.bind("<<ComboboxSelected>>", lambda _event: callback())
        self.vars[key + "_widget"] = combo

    def on_material(self) -> None:
        key = "steel" if self.vars["material"].get() == "Steel W-shapes" else "wood"
        sections = [s.name for s in MATERIALS[key]["sections"]]
        self.vars["section_widget"]["values"] = sections
        self.vars["section"].set(sections[0] if self.vars["section"].get() not in sections else self.vars["section"].get())
        self.on_setup()

    def on_setup(self) -> None:
        span = number(self.vars["span"].get()) or 20.0
        self.state["span"] = clamp(round(span * 4) / 4, 4, 40)
        self.state["support"] = "cantilever" if self.vars["support"].get() == "Cantilever" else "simple"
        self.state["material"] = "steel" if self.vars["material"].get() == "Steel W-shapes" else "wood"
        self.state["section"] = self.vars["section"].get()
        self.state["deflection_limit"] = 240.0 if self.vars["limit"].get() == "L/240" else 360.0
        for load in self.state["uniform_loads"]:
            if load["start"] == 0 and load["end"] in (20, self.state["span"]):
                load["end"] = self.state["span"]
        self.refresh()

    def add_load(self, kind: str) -> None:
        if kind == "point":
            self.state["point_loads"].append({"id": self.load_id, "magnitude": 0.0, "position": self.state["span"] / 2})
        else:
            self.state["uniform_loads"].append({"id": self.load_id, "magnitude": 0.0, "start": 0.0, "end": self.state["span"]})
        self.load_id += 1
        self.refresh()

    def remove_load(self, kind: str, load: dict) -> None:
        key = "point_loads" if kind == "point" else "uniform_loads"
        self.state[key].remove(load)
        self.refresh()

    def render_loads(self) -> None:
        for child in self.load_frame.winfo_children():
            child.destroy()
        self.load_widgets.clear()
        all_loads = [("point", load) for load in self.state["point_loads"]] + [("uniform", load) for load in self.state["uniform_loads"]]
        if not all_loads:
            ttk.Label(self.load_frame, text="No loads. Add one below.").pack(anchor="w")
        for kind, load in all_loads:
            card = tk.Frame(self.load_frame, bg="white", highlightbackground="#cbd7e1", highlightthickness=1, padx=7, pady=6)
            card.pack(fill="x", pady=3)
            title = "Point load" if kind == "point" else "Uniform load"
            tk.Label(card, text=title, bg="white", fg=self.BLUE, font=("Georgia", 10, "bold")).grid(row=0, column=0, sticky="w")
            tk.Button(card, text="Remove", command=lambda k=kind, l=load: self.remove_load(k, l), bg="white", relief="flat", fg="#a33a36").grid(row=0, column=3, sticky="e")
            fields = [("Magnitude (k)", "magnitude")] if kind == "point" else [("Magnitude (k/ft)", "magnitude"), ("Start (ft)", "start"), ("End (ft)", "end")]
            if kind == "point": fields.append(("Position (ft)", "position"))
            for index, (text, key) in enumerate(fields):
                tk.Label(card, text=text, bg="white", fg=self.INK, font=("Georgia", 8)).grid(row=1, column=index, sticky="w", padx=(0, 4))
                variable = tk.StringVar(value=str(load[key]))
                entry = ttk.Entry(card, textvariable=variable, width=9)
                entry.grid(row=2, column=index, sticky="ew", padx=(0, 4))
                variable.trace_add("write", lambda *_args, l=load, k=key, v=variable: self.load_changed(l, k, v.get()))
            error = tk.Label(card, text="", bg="white", fg="#a33a36", font=("Georgia", 8), anchor="w")
            error.grid(row=3, column=0, columnspan=4, sticky="w")
            for index in range(4): card.grid_columnconfigure(index, weight=1)
            self.load_widgets.append((kind, load, [variable], error))

    def load_changed(self, load: dict, key: str, value: str) -> None:
        parsed = number(value)
        load[key] = value if parsed is None else parsed
        for kind, current, _variables, error in self.load_widgets:
            if current is load:
                error.config(text=load_error(kind, load))
        self.refresh(rebuild_loads=False)

    def refresh(self, rebuild_loads: bool = True) -> None:
        if rebuild_loads:
            self.render_loads()
        try:
            self.analysis = analyze(self.state)
        except (KeyError, StopIteration):
            return
        self.status.config(text="")
        self.draw()

    def inspect(self, event: tk.Event) -> None:
        if not hasattr(self, "analysis"):
            return
        self.crosshair_x = float(event.x)
        self.draw()

    def clear_inspection(self) -> None:
        self.crosshair_x = None
        self.draw()

    def draw(self) -> None:
        if not hasattr(self, "analysis") or not self.canvas.winfo_exists(): return
        c = self.canvas
        c.delete("all")
        width = max(760, c.winfo_width())
        left, right = 70, width - 28
        span = self.state["span"]
        x_at = lambda x: left + clamp(x, 0, span) / span * (right - left)
        c.create_text(20, 22, text="BEAM RESPONSE", anchor="w", fill=self.BLUE, font=("Georgia", 15, "bold"))
        c.create_text(width - 20, 22, text=f"{self.state['span']:.2f} ft span", anchor="e", fill="#607181", font=("Georgia", 10))
        beam_y = 94
        c.create_line(left, beam_y, right, beam_y, fill=self.WOOD, width=9)
        for kind, load in [("point", x) for x in self.state["point_loads"]] + [("uniform", x) for x in self.state["uniform_loads"]]:
            if load_error(kind, load): continue
            if kind == "point":
                x = x_at(float(load["position"])); c.create_line(x, 45, x, beam_y - 6, fill="#a33a36", width=2, arrow=tk.LAST)
                c.create_text(x, 35, text=f"{float(load['magnitude']):g} k", fill="#a33a36", font=("Georgia", 9, "bold"))
            else:
                start, end = x_at(float(load["start"])), x_at(float(load["end"]))
                c.create_line(start, 45, end, 45, fill="#174e7a", width=2)
                count = max(2, int((end - start) / 42))
                for i in range(count + 1):
                    x = start + (end - start) * i / count
                    c.create_line(x, 45, x, beam_y - 8, fill="#174e7a", arrow=tk.LAST)
                c.create_text((start + end) / 2, 32, text=f"{float(load['magnitude']):g} k/ft", fill="#174e7a", font=("Georgia", 9, "bold"))
        if self.state["support"] == "cantilever":
            c.create_line(left, beam_y - 28, left, beam_y + 28, fill=self.WOOD, width=8)
            c.create_text(left, beam_y + 43, text="fixed", fill=self.INK, font=("Georgia", 9))
        else:
            c.create_polygon(left, beam_y + 6, left - 18, beam_y + 30, left + 18, beam_y + 30, fill=self.BLUE)
            c.create_oval(right - 17, beam_y + 7, right + 17, beam_y + 27, fill=self.BLUE)
        self.draw_diagram(c, "Shear V (k)", 165, "shear", "#174e7a", x_at, left, right)
        self.draw_diagram(c, "Moment M (kip-ft)", 300, "moment", "#23774b", x_at, left, right)
        self.draw_diagram(c, "Deflection y (in)", 435, "deflection", "#a45b08", x_at, left, right)
        y = 575
        c.create_text(20, y, text="DESIGN CHECKS", anchor="w", fill=self.BLUE, font=("Georgia", 13, "bold"))
        self.draw_check(c, 20, y + 22, "Bending", self.analysis["checks"]["bending"], "ksi")
        self.draw_check(c, width / 2, y + 22, "Deflection", self.analysis["checks"]["deflection"], "in")
        rec = self.analysis["recommendation"]
        text = "No section passes both checks." if rec is None else f"Lightest passing section: {rec[0].name}"
        c.create_text(20, y + 126, text=text, anchor="w", fill=self.INK, font=("Georgia", 11, "bold"))
        if rec:
            recommendation_id = c.create_text(width - 20, y + 126, text="Use recommendation", anchor="e", fill=self.BLUE, font=("Georgia", 10, "underline"))
            c.tag_bind(recommendation_id, "<Button-1>", lambda _e: self.use_recommendation(rec[0].name))
        c.create_text(20, y + 164, text="PASS means only that the simplified bending and deflection checks in this app pass; it is not a complete or code-compliant design.", anchor="w", fill="#a33a36", font=("Georgia", 9))
        if self.crosshair_x is not None and left <= self.crosshair_x <= right:
            c.create_line(self.crosshair_x, 145, self.crosshair_x, 555, fill="#a33a36", dash=(3, 3))

    def draw_diagram(self, c: tk.Canvas, title: str, top: float, kind: str, color: str, x_at: Callable, left: float, right: float) -> None:
        c.create_text(20, top + 42, text=title, anchor="w", fill=self.INK, font=("Georgia", 10, "bold"))
        baseline = top + 45
        c.create_line(left, baseline, right, baseline, fill="#cbd7e1")
        samples = [i / 100 * self.state["span"] for i in range(101)]
        if kind == "shear": values = [shear_at(x, "right", self.analysis) for x in samples]
        elif kind == "moment": values = [moment_at(x, self.analysis) for x in samples]
        else: values = [-1728 * deflection_shape(x, self.analysis) / (MATERIALS[self.state["material"]]["e"] * next(s for s in MATERIALS[self.state["material"]]["sections"] if s.name == self.state["section"]).ix) for x in samples]
        maximum = max(1e-9, max(abs(v) for v in values))
        scale = 34 / maximum
        coords = []
        for x, value in zip(samples, values): coords.extend((x_at(x), baseline - value * scale))
        c.create_line(*coords, fill=color, width=2, smooth=True)
        max_item = self.analysis["max_shear"] if kind == "shear" else self.analysis["max_moment"] if kind == "moment" else self.analysis["max_deflection"]
        c.create_text(x_at(max_item["x"]), baseline - max_item["value"] * scale - 10, text=f"{abs(max_item['value']):.3g}", fill=color, font=("Georgia", 9, "bold"))

    def draw_check(self, c: tk.Canvas, x: float, y: float, name: str, check: dict, unit: str) -> None:
        width = 250
        c.create_rectangle(x, y, x + width, y + 92, fill="#f8fbfd", outline="#cbd7e1")
        c.create_text(x + 12, y + 15, text=name, anchor="w", fill=self.BLUE, font=("Georgia", 11, "bold"))
        c.create_text(x + 12, y + 38, text=f"{check['actual']:.3f} {unit} / {check['allowable']:.3f} {unit}", anchor="w", fill=self.INK, font=("Georgia", 9))
        ratio = min(1.0, check["ratio"]); fill = "#23774b" if check["ratio"] < .7 else "#a45b08" if check["ratio"] <= 1 else "#a33a36"
        c.create_rectangle(x + 12, y + 57, x + 170, y + 67, fill="#e4e9ed", outline="")
        c.create_rectangle(x + 12, y + 57, x + 12 + 158 * ratio, y + 67, fill=fill, outline="")
        c.create_text(x + 238, y + 62, text="PASS" if check["passes"] else "FAIL", anchor="e", fill=fill, font=("Georgia", 10, "bold"))

    def use_recommendation(self, name: str) -> None:
        self.vars["section"].set(name)
        self.on_setup()


if __name__ == "__main__":
    BeamDesigner().mainloop()
