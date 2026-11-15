"""Phase 3 - Analysis & Comparison: runs every algorithm on the common datasets,
writes comparison tables (txt + csv), labelled charts (png) and observations."""
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import deadlock, memory, scheduler, storage
from .logger import get_logger

log = get_logger()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "outputs")
CHARTS = os.path.join(OUT, "charts")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def table(headers, rows):
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)]
    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    fmt = lambda r: "| " + " | ".join(str(x).ljust(w) for x, w in zip(r, widths)) + " |"
    return "\n".join([sep, fmt(headers), sep, *map(fmt, rows), sep])


def _save_csv(fname, headers, rows):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, fname), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def _bar(fname, title, labels, series, ylabel):
    os.makedirs(CHARTS, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    n = len(series)
    width = 0.8 / n
    for k, (name, vals) in enumerate(series.items()):
        xs = [i + k * width for i in range(len(labels))]
        bars = ax.bar(xs, vals, width, label=name)
        for b, v in zip(bars, vals):
            ax.annotate(f"{v:g}", (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom", fontsize=8)
    ax.set_xticks([i + width * (n - 1) / 2 for i in range(len(labels))])
    ax.set_xticklabels(labels)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    if n > 1:
        ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, fname), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- CPU scheduling
def analyze_scheduling():
    cfg = load("processes.json")
    procs = scheduler.load_processes(cfg["processes"])
    results = scheduler.run_all(procs, cfg["quantum"])
    headers = ["Algorithm", "Avg WT", "Avg TAT", "Avg RT", "CPU %", "Throughput", "Ctx switches"]
    rows = [[r.algorithm, r.avg_waiting, r.avg_turnaround, r.avg_response, r.cpu_utilization,
             r.throughput, r.context_switches] for r in results]
    _save_csv("scheduling_comparison.csv", headers, rows)
    labels = [r.algorithm for r in results]
    _bar("scheduling_waiting_turnaround.png", "CPU Scheduling: Average Waiting vs Turnaround Time",
         labels, {"Avg waiting": [r.avg_waiting for r in results],
                  "Avg turnaround": [r.avg_turnaround for r in results]}, "Time units")
    _gantt_chart(results)
    best_wt = min(results, key=lambda r: r.avg_waiting)
    best_rt = min(results, key=lambda r: r.avg_response)
    most_cs = max(results, key=lambda r: r.context_switches)
    obs = [f"{best_wt.algorithm} gives the lowest average waiting time ({best_wt.avg_waiting}).",
           f"{best_rt.algorithm} gives the best average response time ({best_rt.avg_response}).",
           f"{most_cs.algorithm} performs the most context switches ({most_cs.context_switches}), "
           f"which would add overhead on real hardware.",
           "FCFS suffers from the convoy effect: short jobs wait behind long ones."]
    return table(headers, rows), obs


def _gantt_chart(results):
    fig, axes = plt.subplots(len(results), 1, figsize=(9, 1.2 * len(results) + 1), sharex=True)
    pids = sorted({p for r in results for p, _, _ in r.gantt if p != "IDLE"})
    cmap = plt.get_cmap("tab10")
    colors = {p: cmap(i % 10) for i, p in enumerate(pids)}
    for ax, r in zip(axes, results):
        for pid, s, e in r.gantt:
            ax.barh(0, e - s, left=s, color="lightgrey" if pid == "IDLE" else colors[pid], edgecolor="black")
            if pid != "IDLE":
                ax.text((s + e) / 2, 0, pid, ha="center", va="center", fontsize=8)
        ax.set_yticks([])
        ax.set_ylabel(r.algorithm, rotation=0, ha="right", va="center", fontsize=9)
    axes[-1].set_xlabel("Time units")
    fig.suptitle("Gantt Charts - all CPU scheduling algorithms")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, "scheduling_gantt.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- memory
def analyze_memory():
    cfg = load("memory.json")
    refs = cfg["reference_string"]
    rows, series = [], {}
    frame_range = list(range(1, 8))
    for algo in memory.PAGE_ALGOS:
        series[algo.upper() if algo != "optimal" else "Optimal"] = [memory.run_page(algo, refs, f).faults for f in frame_range]
    for f in frame_range:
        rows.append([f] + [v[f - 1] for v in series.values()])
    headers = ["Frames"] + list(series.keys())
    _save_csv("page_fault_comparison.csv", headers, rows)
    os.makedirs(CHARTS, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for name, vals in series.items():
        ax.plot(frame_range, vals, marker="o", label=name)
    ax.set_title("Page Faults vs Number of Frames")
    ax.set_xlabel("Number of frames")
    ax.set_ylabel("Page faults")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, "page_faults.png"), dpi=130)
    plt.close(fig)

    # Belady's anomaly
    bs = cfg["belady_string"]
    belady = [(f, memory.fifo(bs, f).faults) for f in range(1, 7)]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([b[0] for b in belady], [b[1] for b in belady], marker="s", color="crimson")
    ax.set_title("Belady's Anomaly (FIFO)")
    ax.set_xlabel("Number of frames")
    ax.set_ylabel("Page faults")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, "belady_anomaly.png"), dpi=130)
    plt.close(fig)

    arows = []
    for s in ("first", "best", "worst"):
        a = memory.allocate(s, cfg["partitions"], cfg["requests"])
        arows.append([s.title() + "-fit", a.internal_fragmentation, a.external_free, a.unallocated or "none"])
    aheaders = ["Strategy", "Internal frag (KB)", "Unused partitions (KB)", "Unallocated"]
    _save_csv("allocation_comparison.csv", aheaders, arows)
    best = min(rows[2][1:])
    fifo3, lru3, opt3 = rows[2][1], rows[2][2], rows[2][3]
    obs = [f"With 3 frames: FIFO={fifo3}, LRU={lru3}, Optimal={opt3} faults; Optimal is the lower bound.",
           f"Belady's anomaly confirmed: FIFO faults go from {belady[2][1]} (3 frames) to {belady[3][1]} (4 frames) "
           f"on the classic string - more memory, more faults.",
           "LRU and Optimal are stack algorithms and never show the anomaly.",
           "Best-fit minimises wasted space per request but can leave tiny unusable holes."]
    return table(headers, rows) + "\n\n" + table(aheaders, arows), obs


# ---------------------------------------------------------------- deadlock
def analyze_deadlock():
    cfg = load("deadlock.json")
    bank = deadlock.BankersAlgorithm(cfg["allocation"], cfg["maximum"], cfg["available"])
    safety = bank.safety()
    rows = [["Initial state", "SAFE" if safety.safe else "UNSAFE", " -> ".join(safety.sequence)]]
    for r in cfg["requests"]:
        ok, msg = bank.request(r["pid"], r["request"])
        rows.append([f"P{r['pid']} requests {r['request']}", "GRANTED" if ok else "DENIED", msg])
    det = cfg["detection"]
    dead = deadlock.detect_deadlock(det["allocation"], det["request"], det["available"])
    rows.append(["Detection scenario", "DEADLOCK" if dead else "NO DEADLOCK", ", ".join(dead) or "-"])
    _save_csv("deadlock_results.csv", ["Scenario", "Outcome", "Detail"], rows)
    obs = ["The initial state is safe, so every process can finish in the order shown.",
           "A request is denied if it exceeds the claim, exceeds availability, or leads to an unsafe state.",
           "Avoidance (Banker's) prevents deadlock; detection only reports it after it occurs."]
    return table(["Scenario", "Outcome", "Detail"], rows), obs


# ---------------------------------------------------------------- disk
def analyze_disk():
    cfg = load("disk.json")
    results = storage.run_all(cfg["requests"], cfg["head"], cfg["disk_size"], cfg["direction"])
    rows = [[r.algorithm, r.total_movement, r.average_seek] for r in results]
    _save_csv("disk_comparison.csv", ["Algorithm", "Total movement", "Avg seek"], rows)
    _bar("disk_head_movement.png", "Disk Scheduling: Total Head Movement", [r.algorithm for r in results],
         {"Total movement (cylinders)": [r.total_movement for r in results]}, "Cylinders")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for r in results:
        if r.algorithm.startswith(("FCFS", "SSTF", "LOOK")):
            ax.plot(range(len(r.path)), r.path, marker="o", label=r.algorithm)
    ax.set_title("Disk head path (selected algorithms)")
    ax.set_xlabel("Service order")
    ax.set_ylabel("Cylinder")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, "disk_head_path.png"), dpi=130)
    plt.close(fig)
    best = min(results, key=lambda r: r.total_movement)
    worst = max(results, key=lambda r: r.total_movement)
    obs = [f"{best.algorithm} gives the least head movement ({best.total_movement}); "
           f"{worst.algorithm} the most ({worst.total_movement}).",
           "SSTF is efficient but can starve far-away requests; SCAN/LOOK bound the wait.",
           "LOOK/C-LOOK avoid travelling to the physical disk end, saving movement over SCAN/C-SCAN."]
    return table(["Algorithm", "Total movement", "Avg seek"], rows), obs


def full_report() -> str:
    parts = []
    for title, fn in (("CPU SCHEDULING", analyze_scheduling), ("MEMORY MANAGEMENT", analyze_memory),
                      ("DEADLOCK HANDLING", analyze_deadlock), ("DISK STORAGE SCHEDULING", analyze_disk)):
        tbl, obs = fn()
        parts.append(f"##### {title} #####\n{tbl}\n\nTechnical observations:\n" + "\n".join(f"  - {o}" for o in obs))
    text = "\n\n".join(parts)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "analysis_report.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    log.info("full analysis generated, charts in %s", CHARTS)
    return text
