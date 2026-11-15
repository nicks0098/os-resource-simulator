"""Module 3 - Deadlock: Banker's algorithm (avoidance) and deadlock detection."""
from dataclasses import dataclass
from typing import List, Optional

from .logger import get_logger
from .validators import ValidationError, require_int_list, require_matrix

log = get_logger()


@dataclass
class SafetyResult:
    safe: bool
    sequence: List[str]
    steps: List[str]
    need: List[List[int]]


class BankersAlgorithm:
    def __init__(self, allocation, maximum, available):
        self.alloc = require_matrix(allocation, "allocation")
        self.max = require_matrix(maximum, "maximum", rows=len(self.alloc), cols=len(self.alloc[0]))
        self.avail = require_int_list(available, "available", minimum=0)
        if len(self.avail) != len(self.alloc[0]):
            raise ValidationError("available must have one entry per resource type")
        self.n, self.m = len(self.alloc), len(self.avail)
        for i in range(self.n):
            for j in range(self.m):
                if self.alloc[i][j] > self.max[i][j]:
                    raise ValidationError(f"P{i}: allocation exceeds maximum claim for resource {j}")
        self.need = [[self.max[i][j] - self.alloc[i][j] for j in range(self.m)] for i in range(self.n)]

    def safety(self) -> SafetyResult:
        work, finish, seq, steps = list(self.avail), [False] * self.n, [], []
        progress = True
        while progress:
            progress = False
            for i in range(self.n):
                if not finish[i] and all(self.need[i][j] <= work[j] for j in range(self.m)):
                    steps.append(f"P{i}: need {self.need[i]} <= work {work} -> runs, releases {self.alloc[i]}")
                    work = [work[j] + self.alloc[i][j] for j in range(self.m)]
                    finish[i] = True
                    seq.append(f"P{i}")
                    progress = True
        safe = all(finish)
        log.info("banker safety safe=%s sequence=%s", safe, seq)
        return SafetyResult(safe, seq if safe else [], steps, self.need)

    def request(self, pid: int, req) -> (bool, str):
        """Try to grant `req` to process `pid`; state is only changed if granted."""
        if not isinstance(pid, int) or not 0 <= pid < self.n:
            raise ValidationError(f"process id must be between 0 and {self.n - 1}")
        req = require_int_list(req, "request", minimum=0)
        if len(req) != self.m:
            raise ValidationError(f"request must have {self.m} entries")
        if any(req[j] > self.need[pid][j] for j in range(self.m)):
            msg = f"DENIED: P{pid} exceeded its maximum claim"
        elif any(req[j] > self.avail[j] for j in range(self.m)):
            msg = f"DENIED: resources not available, P{pid} must wait"
        else:
            saved = (list(self.avail), [r[:] for r in self.alloc], [r[:] for r in self.need])
            for j in range(self.m):
                self.avail[j] -= req[j]
                self.alloc[pid][j] += req[j]
                self.need[pid][j] -= req[j]
            res = self.safety()
            if res.safe:
                msg = f"GRANTED: safe sequence {' -> '.join(res.sequence)}"
                log.info("banker request P%d %s granted", pid, req)
                return True, msg
            self.avail, self.alloc, self.need = saved      # roll back
            msg = f"DENIED: granting would leave the system in an UNSAFE state"
        log.warning("banker request P%d %s %s", pid, req, msg)
        return False, msg


def detect_deadlock(allocation, request, available):
    """Deadlock detection: returns the list of deadlocked process names."""
    alloc = require_matrix(allocation, "allocation")
    req = require_matrix(request, "request", rows=len(alloc), cols=len(alloc[0]))
    work = require_int_list(available, "available", minimum=0)
    n, m = len(alloc), len(work)
    finish = [all(a == 0 for a in alloc[i]) for i in range(n)]
    changed = True
    while changed:
        changed = False
        for i in range(n):
            if not finish[i] and all(req[i][j] <= work[j] for j in range(m)):
                work = [work[j] + alloc[i][j] for j in range(m)]
                finish[i] = changed = True
    dead = [f"P{i}" for i in range(n) if not finish[i]]
    log.info("deadlock detection deadlocked=%s", dead)
    return dead


def format_safety(res: SafetyResult, bank: BankersAlgorithm) -> str:
    lines = ["=== Banker's Algorithm: Safety Check ===", "Need matrix (Max - Allocation):"]
    for i, row in enumerate(res.need):
        lines.append(f"  P{i}: {row}")
    lines += [f"  {s}" for s in res.steps]
    lines.append(f"Result: SAFE state, safe sequence = {' -> '.join(res.sequence)}" if res.safe
                 else "Result: UNSAFE state - deadlock possible")
    return "\n".join(lines)
