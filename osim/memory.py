"""Module 2 - Memory Management: page replacement (FIFO/LRU/Optimal) and
contiguous allocation (First/Best/Worst fit)."""
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .logger import get_logger
from .validators import ValidationError, require_int, require_int_list

log = get_logger()


@dataclass
class PageResult:
    algorithm: str
    frames: int
    faults: int
    hits: int
    trace: List[dict] = field(default_factory=list)   # per reference: page, frames, fault

    @property
    def fault_rate(self) -> float:
        total = self.faults + self.hits
        return round(100.0 * self.faults / total, 2)


def _simulate(name, refs, frames, choose_victim) -> PageResult:
    refs = require_int_list(refs, "reference string", minimum=0)
    frames = require_int(frames, "frame count", minimum=1, maximum=64)
    memory: List[int] = []
    meta: Dict = {"order": deque(), "last_used": {}}
    faults = hits = 0
    trace = []
    for idx, page in enumerate(refs):
        fault = page not in memory
        if fault:
            faults += 1
            if len(memory) >= frames:
                victim = choose_victim(memory, refs, idx, meta)
                memory[memory.index(victim)] = page
                meta["order"].remove(victim)
            else:
                memory.append(page)
            meta["order"].append(page)
        else:
            hits += 1
        meta["last_used"][page] = idx
        trace.append({"ref": page, "frames": list(memory), "fault": fault})
    log.info("page replacement %s frames=%d faults=%d", name, frames, faults)
    return PageResult(name, frames, faults, hits, trace)


def fifo(refs, frames):
    return _simulate("FIFO", refs, frames, lambda mem, r, i, m: m["order"][0])


def lru(refs, frames):
    return _simulate("LRU", refs, frames, lambda mem, r, i, m: min(mem, key=lambda p: m["last_used"][p]))


def optimal(refs, frames):
    def victim(mem, r, i, m):
        future = r[i + 1:]
        # evict the page whose next use is farthest in the future (never used = infinity)
        return max(mem, key=lambda p: future.index(p) if p in future else len(future) + 1)
    return _simulate("Optimal", refs, frames, victim)


PAGE_ALGOS = {"fifo": fifo, "lru": lru, "optimal": optimal}


def run_page(name, refs, frames) -> PageResult:
    if name.lower() not in PAGE_ALGOS:
        raise ValidationError(f"unknown page algorithm '{name}'. Choose from {sorted(PAGE_ALGOS)}")
    return PAGE_ALGOS[name.lower()](refs, frames)


def format_page(res: PageResult) -> str:
    lines = [f"=== Page Replacement: {res.algorithm} ({res.frames} frames) ===",
             f"{'Ref':>4} | {'Frames':<{res.frames * 4 + 2}}| Result"]
    for t in res.trace:
        fr = " ".join(f"{p:>2}" for p in t["frames"])
        lines.append(f"{t['ref']:>4} | {fr:<{res.frames * 4 + 1}}| {'FAULT' if t['fault'] else 'hit'}")
    lines.append(f"Faults={res.faults} Hits={res.hits} Fault rate={res.fault_rate}%")
    return "\n".join(lines)


# ---------------------------------------------------------------- contiguous allocation
@dataclass
class AllocationResult:
    strategy: str
    assignments: Dict[int, Optional[int]]   # process size -> partition index (None = not allocated)
    internal_fragmentation: int
    external_free: int
    unallocated: List[int]


def allocate(strategy: str, partitions, requests) -> AllocationResult:
    partitions = require_int_list(partitions, "partitions", minimum=1)
    requests = require_int_list(requests, "requests", minimum=1)
    strategy = strategy.lower()
    if strategy not in ("first", "best", "worst"):
        raise ValidationError("strategy must be first, best or worst")
    free = list(partitions)
    used = [False] * len(free)
    assign, frag, unalloc = {}, 0, []
    for n, req in enumerate(requests):
        cands = [i for i, s in enumerate(free) if not used[i] and s >= req]
        if not cands:
            assign[n] = None
            unalloc.append(req)
            continue
        if strategy == "first":
            pick = cands[0]
        elif strategy == "best":
            pick = min(cands, key=lambda i: free[i])
        else:
            pick = max(cands, key=lambda i: free[i])
        used[pick] = True
        assign[n] = pick
        frag += free[pick] - req
    ext = sum(s for i, s in enumerate(free) if not used[i])
    log.info("allocation %s partitions=%d requests=%d unallocated=%d", strategy, len(free), len(requests), len(unalloc))
    return AllocationResult(strategy, assign, frag, ext, unalloc)


def format_allocation(res: AllocationResult, partitions, requests) -> str:
    lines = [f"=== Contiguous Allocation: {res.strategy.title()}-fit ===",
             f"Partitions: {list(partitions)}", f"{'Request':<10}{'Size':>6}  Partition"]
    for n, part in res.assignments.items():
        where = f"#{part} ({partitions[part]} KB)" if part is not None else "NOT ALLOCATED"
        lines.append(f"P{n + 1:<9}{requests[n]:>6}  {where}")
    lines.append(f"Internal fragmentation={res.internal_fragmentation} KB  "
                 f"Free (unused partitions)={res.external_free} KB  Unallocated={res.unallocated}")
    return "\n".join(lines)
