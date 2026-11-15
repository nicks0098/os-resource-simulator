# Project Report - OS Resource Management Simulator

## 1. Problem statement
An operating system must share a few scarce resources (CPU, memory, devices, disk) among many competing
processes. This project builds one integrated Python-and-Bash application that simulates how an OS makes these
decisions, so that different policies can be run on identical input and compared with measurable results.

## 2. Design
**Modules.** `scheduler` (CPU), `memory` (paging and contiguous allocation), `deadlock` (avoidance and
detection), `storage` (disk-arm scheduling), `analysis` (comparison engine), `validators`, `logger`,
`bash_bridge`. `main.py` is the single entry point (menu and CLI).

**Workflow.** User input (menu or JSON) -> validation -> algorithm -> result object (trace + metrics) -> formatted
terminal output + saved trace -> analysis engine reuses the same results for tables, charts and observations ->
every step is logged. See the diagram in `README.md`.

**Data design.** JSON datasets in `data/`; each algorithm returns a dataclass (`ScheduleResult`, `PageResult`,
`AllocationResult`, `SafetyResult`, `DiskResult`) so results are reusable and testable.

**Python-Bash integration.** Python calls `system_info.sh` (reads `/proc`, `ps`, `df`) and `log_report.sh`
(awk/grep analytics over the activity log) through `bash_bridge.run_script`, which handles missing bash/script and
timeouts. In the other direction, `run_all.sh` drives tests, the simulator and reports from the shell.

## 3. Implementation summary
* **CPU scheduling** - FCFS, SJF, SRTF, Priority, RR. Metrics: waiting, turnaround, response time, CPU
  utilization, throughput, context switches; idle gaps are modelled.
* **Memory** - FIFO / LRU / Optimal page replacement with a per-reference trace; First/Best/Worst-fit contiguous
  allocation with internal fragmentation and unallocated requests.
* **Deadlock** - Banker's safety algorithm, request handling (claim check, availability check, trial allocation and
  rollback if unsafe) and a detection algorithm.
* **Storage** - FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK with total head movement and average seek.

## 4. Analysis and results
**CPU scheduling (5 processes, `data/processes.json`)**

| Algorithm | Avg WT | Avg TAT | Avg RT | Context switches |
|---|---|---|---|---|
| FCFS | 11.0 | 16.6 | 11.0 | 4 |
| SJF | 7.8 | 13.4 | 7.8 | 4 |
| SRTF | 6.4 | 12.0 | 3.8 | 6 |
| Priority | 10.2 | 15.8 | 10.2 | 4 |
| RR (q=4) | 13.0 | 18.6 | 6.4 | 8 |

SRTF minimises waiting time at the cost of more context switches and possible starvation of long jobs. Round
Robin has the worst waiting time here but a good response time (6.4 vs 11.0 for FCFS), which is why it suits
interactive systems. FCFS shows the convoy effect.

**Page replacement (20-reference textbook string, 3 frames):** FIFO 15, LRU 12, Optimal 9 faults. Optimal is a
theoretical lower bound; LRU approximates it well. On the classic string `1 2 3 4 1 2 5 1 2 3 4 5`, FIFO has 9
faults with 3 frames but **10 with 4 frames** - Belady's anomaly - while LRU never shows it (`outputs/charts/belady_anomaly.png`).

**Allocation (partitions 100/500/200/300/600, requests 212/417/112/426):** best-fit allocates all four requests
(internal fragmentation 433 KB); first-fit and worst-fit fail to place the 426 KB request.

**Deadlock:** the sample system is safe with sequence P1 -> P3 -> P4 -> P0 -> P2. After granting P1 `[1,0,2]`, P4's
`[3,3,0]` is denied (insufficient resources) and P0's `[0,2,0]` is denied (would be unsafe), showing why avoidance
is stricter than simply checking availability. The detection scenario reports P1-P4 deadlocked.

**Disk (head 53, queue 98 183 37 122 14 124 65 67, 200 cylinders, moving down):** FCFS 640, SSTF 236, SCAN 236,
C-SCAN 386, LOOK **208**, C-LOOK 326. Reordering requests cuts head movement by up to ~67 %; LOOK beats SCAN
because it turns around at the last request rather than the disk edge.

## 5. Testing and reliability
47 automated tests cover valid, invalid and boundary inputs (see README). Validation raises `ValidationError`
with a clear message; the menu and CLI catch it, log it and continue (CLI exits with code 2). A last-resort handler
keeps the menu alive on unexpected errors. Missing/corrupt files, EOF on input and missing Bash are handled. One
real bug was found by the boundary tests - a disk request exactly at the head position caused SCAN to reverse
needlessly - and fixed (requests at the head are now served first at zero cost).

## 6. Limitations and future work
Simulation is single-CPU and time is in abstract units; no I/O bursts, multilevel queues or file systems. Possible
extensions: multilevel feedback queue, Clock/LFU page replacement, buddy allocator, resource-allocation-graph
visualisation, and a web dashboard.

## 7. Originality statement
The code, datasets, tests, charts and documentation were written for this capstone. The textbook datasets used
(page reference string, Banker's example, disk queue) are standard teaching examples so results can be verified
against known answers.
