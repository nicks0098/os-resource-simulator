#!/usr/bin/env python3
"""OSim - OS Resource Management Simulator (entry point).

Interactive menu:      python3 main.py
Non-interactive mode:  python3 main.py schedule --algo rr --quantum 4
                       python3 main.py all         (full demo + analysis)
"""
import argparse
import json
import os
import sys

from osim import analysis, deadlock, memory, scheduler, storage
from osim.bash_bridge import run_script
from osim.logger import get_logger
from osim.validators import ValidationError, require_int, require_int_list

log = get_logger()
ROOT = os.path.dirname(os.path.abspath(__file__))
TRACES = os.path.join(ROOT, "outputs", "traces")

BANNER = r"""
  ___  ____  _
 / _ \/ ___|(_)_ __ ___
| | | \___ \| | '_ ` _ \    OS Resource Management Simulator
| |_| |___) | | | | | | |   CPU | Memory | Deadlock | Storage
 \___/|____/|_|_| |_| |_|
"""


# ------------------------------------------------------------------ helpers
def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValidationError(f"file not found: {path}")
    except json.JSONDecodeError as e:
        raise ValidationError(f"invalid JSON in {path}: {e}")


def data_path(name):
    return os.path.join(ROOT, "data", name)


def ask(prompt, default=None):
    try:
        val = input(f"{prompt}" + (f" [{default}]" if default is not None else "") + ": ").strip()
    except EOFError:
        raise KeyboardInterrupt
    return val if val else (str(default) if default is not None else "")


def save_trace(name, text):
    os.makedirs(TRACES, exist_ok=True)
    with open(os.path.join(TRACES, name), "w", encoding="utf-8") as f:
        f.write(text + "\n")


# ------------------------------------------------------------------ actions
def do_schedule(algo, quantum, input_file):
    cfg = read_json(input_file or data_path("processes.json"))
    procs = scheduler.load_processes(cfg["processes"] if isinstance(cfg, dict) else cfg)
    q = quantum or (cfg.get("quantum", 2) if isinstance(cfg, dict) else 2)
    results = scheduler.run_all(procs, q) if algo == "all" else [scheduler.run(algo, procs, q)]
    text = "\n\n".join(scheduler.format_result(r) for r in results)
    print(text)
    save_trace(f"scheduling_{algo}.txt", text)


def do_memory(algo, frames, refs, input_file):
    cfg = read_json(input_file or data_path("memory.json"))
    refs = refs or cfg["reference_string"]
    frames = frames or cfg["frames"]
    names = list(memory.PAGE_ALGOS) if algo == "all" else [algo]
    text = "\n\n".join(memory.format_page(memory.run_page(n, refs, frames)) for n in names)
    for s in ("first", "best", "worst"):
        text += "\n\n" + memory.format_allocation(memory.allocate(s, cfg["partitions"], cfg["requests"]),
                                                  cfg["partitions"], cfg["requests"])
    print(text)
    save_trace(f"memory_{algo}.txt", text)


def do_deadlock(input_file):
    cfg = read_json(input_file or data_path("deadlock.json"))
    bank = deadlock.BankersAlgorithm(cfg["allocation"], cfg["maximum"], cfg["available"])
    out = [deadlock.format_safety(bank.safety(), bank)]
    for r in cfg.get("requests", []):
        ok, msg = bank.request(r["pid"], r["request"])
        out.append(f"Request P{r['pid']} {r['request']}: {msg}")
    det = cfg.get("detection")
    if det:
        dead = deadlock.detect_deadlock(det["allocation"], det["request"], det["available"])
        out.append("Deadlock detection: " + (f"DEADLOCK among {', '.join(dead)}" if dead else "no deadlock"))
    text = "\n".join(out)
    print(text)
    save_trace("deadlock.txt", text)


def do_disk(algo, input_file):
    cfg = read_json(input_file or data_path("disk.json"))
    names = list(storage.DISK_ALGOS) if algo == "all" else [algo]
    text = "\n\n".join(storage.format_disk(storage.run(n, cfg["requests"], cfg["head"], cfg["disk_size"],
                                                        cfg.get("direction", "up"))) for n in names)
    print(text)
    save_trace(f"disk_{algo}.txt", text)


def do_analysis():
    text = analysis.full_report()
    print(text)
    save_trace("analysis_report.txt", text)
    print(f"\nCharts saved to {os.path.join('outputs', 'charts')}/ and CSV tables to outputs/")


def do_sysinfo():
    print(run_script("system_info.sh"))


def do_logreport():
    print(run_script("log_report.sh"))


# ------------------------------------------------------------------ interactive menu
def menu_schedule():
    print("Enter processes as 'pid arrival burst priority' one per line (blank line to finish).")
    print("Press Enter immediately to use data/processes.json.")
    rows = []
    while True:
        line = ask("process")
        if not line:
            break
        parts = line.split()
        if len(parts) not in (3, 4):
            print("  ! expected: pid arrival burst [priority]")
            continue
        rows.append({"pid": parts[0], "arrival": parts[1], "burst": parts[2],
                     "priority": parts[3] if len(parts) == 4 else 0})
    algo = ask("Algorithm (fcfs/sjf/srtf/priority/rr/all)", "all").lower()
    q = require_int(ask("Time quantum (for RR)", 4), "time quantum", minimum=1)
    if rows:
        procs = scheduler.load_processes(rows)
        results = scheduler.run_all(procs, q) if algo == "all" else [scheduler.run(algo, procs, q)]
        print("\n\n".join(scheduler.format_result(r) for r in results))
    else:
        do_schedule(algo, q, None)


def menu_memory():
    refs = ask("Reference string (space/comma separated)", "7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1")
    frames = require_int(ask("Number of frames", 3), "frames", minimum=1, maximum=64)
    algo = ask("Algorithm (fifo/lru/optimal/all)", "all").lower()
    refs = require_int_list(refs, "reference string", minimum=0)
    do_memory(algo, frames, refs, None)


def menu_deadlock():
    do_deadlock(None)
    if ask("Try your own resource request on the sample system? (y/n)", "n").lower() == "y":
        cfg = read_json(data_path("deadlock.json"))
        bank = deadlock.BankersAlgorithm(cfg["allocation"], cfg["maximum"], cfg["available"])
        pid = require_int(ask("Process id (0-4)"), "process id", 0, bank.n - 1)
        req = require_int_list(ask("Request vector, e.g. '1 0 2'"), "request", minimum=0)
        print(bank.request(pid, req)[1])


def menu_disk():
    reqs = ask("Request queue", "98 183 37 122 14 124 65 67")
    head = require_int(ask("Head position", 53), "head", minimum=0)
    size = require_int(ask("Disk size (cylinders)", 200), "disk size", minimum=2)
    algo = ask("Algorithm (fcfs/sstf/scan/cscan/look/clook/all)", "all").lower()
    direction = ask("Direction (up/down)", "down").lower()
    names = list(storage.DISK_ALGOS) if algo == "all" else [algo]
    print("\n\n".join(storage.format_disk(storage.run(n, reqs, head, size, direction)) for n in names))


MENU = [("1", "CPU Process Scheduling", menu_schedule),
        ("2", "Memory Management (paging + allocation)", menu_memory),
        ("3", "Deadlock (Banker's + detection)", menu_deadlock),
        ("4", "Disk / Storage Scheduling", menu_disk),
        ("5", "Run full analysis & generate charts", do_analysis),
        ("6", "Live system information (Bash)", do_sysinfo),
        ("7", "Activity log summary (Bash)", do_logreport),
        ("0", "Exit", None)]


def interactive():
    print(BANNER)
    log.info("interactive session started")
    while True:
        print("\n" + "=" * 52 + "\n MAIN MENU\n" + "=" * 52)
        for key, label, _ in MENU:
            print(f"  [{key}] {label}")
        try:
            choice = ask("Select option")
        except KeyboardInterrupt:
            print("\nGoodbye.")
            return 0
        if choice == "0":
            print("Goodbye.")
            log.info("interactive session ended")
            return 0
        action = next((fn for k, _, fn in MENU if k == choice), None)
        if action is None:
            print(f"  ! '{choice}' is not a valid option, choose 0-7.")
            log.warning("invalid menu choice %r", choice)
            continue
        try:
            print()
            action()
        except ValidationError as e:
            print(f"  ! Invalid input: {e}")
            log.error("validation error: %s", e)
        except KeyboardInterrupt:
            print("\nGoodbye.")
            return 0
        except Exception as e:  # last-resort guard so the menu never crashes
            print(f"  ! Unexpected error: {e}")
            log.exception("unexpected error")


# ------------------------------------------------------------------ CLI
def build_parser():
    p = argparse.ArgumentParser(description="OS Resource Management Simulator")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("schedule", help="CPU scheduling")
    s.add_argument("--algo", default="all", choices=["fcfs", "sjf", "srtf", "priority", "rr", "all"])
    s.add_argument("--quantum", type=int)
    s.add_argument("--input")
    m = sub.add_parser("memory", help="page replacement + contiguous allocation")
    m.add_argument("--algo", default="all", choices=["fifo", "lru", "optimal", "all"])
    m.add_argument("--frames", type=int)
    m.add_argument("--refs", help="e.g. '7 0 1 2 0 3'")
    m.add_argument("--input")
    d = sub.add_parser("deadlock", help="Banker's algorithm + detection")
    d.add_argument("--input")
    k = sub.add_parser("disk", help="disk scheduling")
    k.add_argument("--algo", default="all", choices=list(storage.DISK_ALGOS) + ["all"])
    k.add_argument("--input")
    sub.add_parser("analyze", help="compare algorithms, write tables and charts")
    sub.add_parser("sysinfo", help="live system info via Bash")
    sub.add_parser("logreport", help="summarise activity log via Bash")
    sub.add_parser("all", help="run every module then the analysis")
    sub.add_parser("menu", help="interactive menu (default)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.cmd in (None, "menu"):
            return interactive()
        if args.cmd == "schedule":
            do_schedule(args.algo, args.quantum, args.input)
        elif args.cmd == "memory":
            do_memory(args.algo, args.frames, args.refs, args.input)
        elif args.cmd == "deadlock":
            do_deadlock(args.input)
        elif args.cmd == "disk":
            do_disk(args.algo, args.input)
        elif args.cmd == "analyze":
            do_analysis()
        elif args.cmd == "sysinfo":
            do_sysinfo()
        elif args.cmd == "logreport":
            do_logreport()
        elif args.cmd == "all":
            do_schedule("all", None, None)
            do_memory("all", None, None, None)
            do_deadlock(None)
            do_disk("all", None)
            do_analysis()
        return 0
    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        log.error("validation error: %s", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
