"""Module 4 - Storage: disk-arm scheduling (FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK)."""
from dataclasses import dataclass
from typing import List

from .logger import get_logger
from .validators import ValidationError, require_int, require_int_list

log = get_logger()


@dataclass
class DiskResult:
    algorithm: str
    path: List[int]
    total_movement: int
    average_seek: float


def _split(reqs, head):
    """Requests at the head position cost nothing and are served first."""
    at = [r for r in reqs if r == head]
    lo = sorted(r for r in reqs if r < head)
    hi = sorted(r for r in reqs if r > head)
    return at, lo, hi


def _result(name, start, path):
    full = [start] + path
    total = sum(abs(a - b) for a, b in zip(full, full[1:]))
    return DiskResult(name, full, total, round(total / max(1, len(path)), 2))


def _check(requests, head, disk_size):
    disk_size = require_int(disk_size, "disk size", minimum=2)
    head = require_int(head, "head position", minimum=0, maximum=disk_size - 1)
    reqs = require_int_list(requests, "requests", minimum=0, maximum=disk_size - 1)
    return reqs, head, disk_size


def fcfs(requests, head, disk_size=200):
    reqs, head, _ = _check(requests, head, disk_size)
    return _result("FCFS", head, reqs)


def sstf(requests, head, disk_size=200):
    reqs, head, _ = _check(requests, head, disk_size)
    todo, cur, path = list(reqs), head, []
    while todo:
        nxt = min(todo, key=lambda r: (abs(r - cur), r))
        todo.remove(nxt)
        path.append(nxt)
        cur = nxt
    return _result("SSTF", head, path)


def scan(requests, head, disk_size=200, direction="up"):
    reqs, head, disk_size = _check(requests, head, disk_size)
    at, lo, hi = _split(reqs, head)
    if direction == "up":
        path = at + hi + ([disk_size - 1] if lo else []) + lo[::-1]
    else:
        path = at + lo[::-1] + ([0] if hi else []) + hi
    return _result(f"SCAN({direction})", head, path)


def cscan(requests, head, disk_size=200, direction="up"):
    reqs, head, disk_size = _check(requests, head, disk_size)
    at, lo, hi = _split(reqs, head)
    if direction == "up":
        path = at + hi + ([disk_size - 1, 0] if lo else []) + lo
    else:
        path = at + lo[::-1] + ([0, disk_size - 1] if hi else []) + hi[::-1]
    return _result(f"C-SCAN({direction})", head, path)


def look(requests, head, disk_size=200, direction="up"):
    reqs, head, _ = _check(requests, head, disk_size)
    at, lo, hi = _split(reqs, head)
    path = at + (hi + lo[::-1] if direction == "up" else lo[::-1] + hi)
    return _result(f"LOOK({direction})", head, path)


def clook(requests, head, disk_size=200, direction="up"):
    reqs, head, _ = _check(requests, head, disk_size)
    at, lo, hi = _split(reqs, head)
    path = at + (hi + lo if direction == "up" else lo[::-1] + hi[::-1])
    return _result(f"C-LOOK({direction})", head, path)


DISK_ALGOS = {"fcfs": fcfs, "sstf": sstf, "scan": scan, "cscan": cscan, "look": look, "clook": clook}


def run(name, requests, head, disk_size=200, direction="up") -> DiskResult:
    name = name.lower()
    if name not in DISK_ALGOS:
        raise ValidationError(f"unknown disk algorithm '{name}'. Choose from {sorted(DISK_ALGOS)}")
    if direction not in ("up", "down"):
        raise ValidationError("direction must be 'up' or 'down'")
    fn = DISK_ALGOS[name]
    res = fn(requests, head, disk_size) if name in ("fcfs", "sstf") else fn(requests, head, disk_size, direction)
    log.info("disk %s head=%s movement=%s", res.algorithm, head, res.total_movement)
    return res


def run_all(requests, head, disk_size=200, direction="up") -> List[DiskResult]:
    return [run(n, requests, head, disk_size, direction) for n in DISK_ALGOS]


def format_disk(res: DiskResult) -> str:
    return (f"=== Disk Scheduling: {res.algorithm} ===\nHead path: {' -> '.join(map(str, res.path))}\n"
            f"Total head movement={res.total_movement} cylinders  Average seek={res.average_seek}")
