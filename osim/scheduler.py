"""Module 1 - CPU Process Scheduling: FCFS, SJF, SRTF, Priority, Round Robin."""
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .logger import get_logger
from .validators import ValidationError, require_int

log = get_logger()


@dataclass
class Process:
    pid: str
    arrival: int
    burst: int
    priority: int = 0  # lower number = higher priority


@dataclass
class ScheduleResult:
    algorithm: str
    gantt: List[Tuple[str, int, int]]          # (pid | "IDLE", start, end)
    metrics: Dict[str, Dict[str, int]]          # per pid: completion, turnaround, waiting, response
    avg_waiting: float = 0.0
    avg_turnaround: float = 0.0
    avg_response: float = 0.0
    cpu_utilization: float = 0.0
    throughput: float = 0.0
    context_switches: int = 0


def load_processes(raw: List[dict]) -> List[Process]:
    """Validate and convert raw dictionaries into Process objects."""
    if not isinstance(raw, list) or not raw:
        raise ValidationError("process list must be a non-empty list")
    procs, seen = [], set()
    for i, p in enumerate(raw):
        if not isinstance(p, dict) or "pid" not in p:
            raise ValidationError(f"process #{i} must be an object with a 'pid'")
        pid = str(p["pid"])
        if pid in seen:
            raise ValidationError(f"duplicate pid {pid}")
        seen.add(pid)
        procs.append(Process(
            pid,
            require_int(p.get("arrival", 0), f"{pid}.arrival", minimum=0),
            require_int(p.get("burst"), f"{pid}.burst", minimum=1),
            require_int(p.get("priority", 0), f"{pid}.priority", minimum=0),
        ))
    return procs


def _merge(gantt):
    out = []
    for pid, s, e in gantt:
        if out and out[-1][0] == pid and out[-1][2] == s:
            out[-1] = (pid, out[-1][1], e)
        else:
            out.append((pid, s, e))
    return out


def _build(name, procs, gantt, completion, first_run) -> ScheduleResult:
    gantt = _merge(gantt)
    metrics = {}
    for p in procs:
        ct = completion[p.pid]
        tat = ct - p.arrival
        metrics[p.pid] = {"arrival": p.arrival, "burst": p.burst, "completion": ct,
                          "turnaround": tat, "waiting": tat - p.burst,
                          "response": first_run[p.pid] - p.arrival}
    n = len(procs)
    end = max(e for _, _, e in gantt)
    start = min(p.arrival for p in procs)
    busy = sum(e - s for pid, s, e in gantt if pid != "IDLE")
    real = [g for g in gantt if g[0] != "IDLE"]
    switches = sum(1 for a, b in zip(real, real[1:]) if a[0] != b[0])
    return ScheduleResult(
        name, gantt, metrics,
        round(sum(m["waiting"] for m in metrics.values()) / n, 2),
        round(sum(m["turnaround"] for m in metrics.values()) / n, 2),
        round(sum(m["response"] for m in metrics.values()) / n, 2),
        round(100.0 * busy / (end - start), 2), round(n / (end - start), 4), switches)


def _nonpreemptive(name, procs, key):
    """Generic non-preemptive scheduler; `key(p)` picks among ready processes."""
    pending = sorted(procs, key=lambda p: (p.arrival, p.pid))
    t, gantt, completion, first = 0, [], {}, {}
    while pending:
        ready = [p for p in pending if p.arrival <= t]
        if not ready:
            nxt = min(p.arrival for p in pending)
            gantt.append(("IDLE", t, nxt))
            t = nxt
            continue
        p = min(ready, key=lambda x: (key(x), x.arrival, x.pid))
        pending.remove(p)
        first[p.pid] = t
        gantt.append((p.pid, t, t + p.burst))
        t += p.burst
        completion[p.pid] = t
    return _build(name, procs, gantt, completion, first)


def fcfs(procs):
    return _nonpreemptive("FCFS", procs, key=lambda p: p.arrival)


def sjf(procs):
    return _nonpreemptive("SJF", procs, key=lambda p: p.burst)


def priority(procs):
    return _nonpreemptive("Priority", procs, key=lambda p: p.priority)


def srtf(procs):
    """Shortest Remaining Time First (preemptive SJF), simulated tick by tick."""
    remaining = {p.pid: p.burst for p in procs}
    by_pid = {p.pid: p for p in procs}
    t, gantt, completion, first = min(p.arrival for p in procs), [], {}, {}
    while remaining:
        ready = [pid for pid in remaining if by_pid[pid].arrival <= t]
        if not ready:
            nxt = min(by_pid[pid].arrival for pid in remaining)
            gantt.append(("IDLE", t, nxt))
            t = nxt
            continue
        pid = min(ready, key=lambda x: (remaining[x], by_pid[x].arrival, x))
        first.setdefault(pid, t)
        gantt.append((pid, t, t + 1))
        remaining[pid] -= 1
        t += 1
        if remaining[pid] == 0:
            del remaining[pid]
            completion[pid] = t
    return _build("SRTF", procs, gantt, completion, first)


def round_robin(procs, quantum: int = 2):
    quantum = require_int(quantum, "time quantum", minimum=1)
    pending = sorted(procs, key=lambda p: (p.arrival, p.pid))
    remaining = {p.pid: p.burst for p in procs}
    t = pending[0].arrival
    queue, gantt, completion, first = [], [], {}, {}
    i = 0

    def admit(upto):
        nonlocal i
        while i < len(pending) and pending[i].arrival <= upto:
            queue.append(pending[i].pid)
            i += 1

    admit(t)
    while queue or i < len(pending):
        if not queue:
            nxt = pending[i].arrival
            gantt.append(("IDLE", t, nxt))
            t = nxt
            admit(t)
            continue
        pid = queue.pop(0)
        first.setdefault(pid, t)
        run = min(quantum, remaining[pid])
        gantt.append((pid, t, t + run))
        t += run
        remaining[pid] -= run
        admit(t)                      # arrivals during the slice go first
        if remaining[pid] > 0:
            queue.append(pid)
        else:
            completion[pid] = t
    return _build(f"RR(q={quantum})", procs, gantt, completion, first)


ALGORITHMS = {"fcfs": fcfs, "sjf": sjf, "srtf": srtf, "priority": priority, "rr": round_robin}


def run(name: str, procs: List[Process], quantum: int = 2) -> ScheduleResult:
    name = name.lower()
    if name not in ALGORITHMS:
        raise ValidationError(f"unknown scheduling algorithm '{name}'. Choose from {sorted(ALGORITHMS)}")
    res = round_robin(procs, quantum) if name == "rr" else ALGORITHMS[name](procs)
    log.info("scheduler %s processes=%d avg_wait=%s avg_tat=%s", res.algorithm, len(procs),
             res.avg_waiting, res.avg_turnaround)
    return res


def run_all(procs: List[Process], quantum: int = 2) -> List[ScheduleResult]:
    return [run(n, procs, quantum) for n in ("fcfs", "sjf", "srtf", "priority", "rr")]


def format_result(res: ScheduleResult) -> str:
    lines = [f"=== CPU Scheduling: {res.algorithm} ===", "Gantt chart:"]
    bar = "|" + "|".join(f" {pid} ".center(max(5, (e - s) * 2)) for pid, s, e in res.gantt) + "|"
    lines.append(bar)
    marks = ""
    for pid, s, e in res.gantt:
        w = max(5, (e - s) * 2) + 1
        marks += str(s).ljust(w)
    marks += str(res.gantt[-1][2])
    lines.append(marks)
    lines.append("")
    lines.append(f"{'PID':<6}{'Arr':>5}{'Burst':>7}{'Compl':>7}{'TAT':>6}{'WT':>6}{'RT':>6}")
    for pid, m in sorted(res.metrics.items()):
        lines.append(f"{pid:<6}{m['arrival']:>5}{m['burst']:>7}{m['completion']:>7}"
                     f"{m['turnaround']:>6}{m['waiting']:>6}{m['response']:>6}")
    lines.append(f"\nAvg waiting={res.avg_waiting}  Avg turnaround={res.avg_turnaround}  "
                 f"Avg response={res.avg_response}")
    lines.append(f"CPU utilization={res.cpu_utilization}%  Throughput={res.throughput} proc/unit  "
                 f"Context switches={res.context_switches}")
    return "\n".join(lines)
