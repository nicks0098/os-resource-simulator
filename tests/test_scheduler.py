import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from osim import scheduler as s
from osim.validators import ValidationError

CLASSIC = [{"pid": "P1", "arrival": 0, "burst": 8}, {"pid": "P2", "arrival": 1, "burst": 4},
           {"pid": "P3", "arrival": 2, "burst": 9}, {"pid": "P4", "arrival": 3, "burst": 5}]


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.procs = s.load_processes(CLASSIC)

    # ---- valid
    def test_fcfs_known_values(self):
        r = s.fcfs(self.procs)
        self.assertEqual(r.avg_waiting, 8.75)
        self.assertEqual(r.avg_turnaround, 15.25)

    def test_sjf_known_values(self):
        self.assertEqual(s.sjf(self.procs).avg_waiting, 7.75)

    def test_srtf_known_values(self):
        self.assertEqual(s.srtf(self.procs).avg_waiting, 6.5)

    def test_round_robin_quantum_4(self):
        r = s.round_robin(self.procs, 4)
        self.assertEqual(r.metrics["P2"]["completion"], 8)
        self.assertEqual(r.avg_waiting, 11.75)

    def test_priority_order(self):
        procs = s.load_processes([{"pid": "A", "arrival": 0, "burst": 3, "priority": 2},
                                  {"pid": "B", "arrival": 0, "burst": 3, "priority": 1}])
        self.assertEqual(s.priority(procs).gantt[0][0], "B")

    def test_turnaround_identity(self):
        for r in s.run_all(self.procs, 3):
            for m in r.metrics.values():
                self.assertEqual(m["turnaround"], m["waiting"] + m["burst"])

    # ---- boundary
    def test_single_process(self):
        r = s.fcfs(s.load_processes([{"pid": "X", "arrival": 0, "burst": 1}]))
        self.assertEqual((r.avg_waiting, r.cpu_utilization), (0, 100.0))

    def test_idle_gap_when_late_arrival(self):
        r = s.fcfs(s.load_processes([{"pid": "X", "arrival": 5, "burst": 2}]))
        self.assertEqual(r.metrics["X"]["completion"], 7)
        r = s.fcfs(s.load_processes([{"pid": "A", "arrival": 0, "burst": 1}, {"pid": "B", "arrival": 4, "burst": 1}]))
        self.assertIn("IDLE", [g[0] for g in r.gantt])
        self.assertLess(r.cpu_utilization, 100)

    def test_quantum_larger_than_bursts_equals_fcfs(self):
        self.assertEqual(s.round_robin(self.procs, 100).avg_waiting, s.fcfs(self.procs).avg_waiting)

    # ---- invalid
    def test_zero_burst_rejected(self):
        with self.assertRaises(ValidationError):
            s.load_processes([{"pid": "P", "arrival": 0, "burst": 0}])

    def test_negative_arrival_rejected(self):
        with self.assertRaises(ValidationError):
            s.load_processes([{"pid": "P", "arrival": -1, "burst": 2}])

    def test_duplicate_pid_rejected(self):
        with self.assertRaises(ValidationError):
            s.load_processes([{"pid": "P", "burst": 1}, {"pid": "P", "burst": 2}])

    def test_empty_and_non_numeric(self):
        with self.assertRaises(ValidationError):
            s.load_processes([])
        with self.assertRaises(ValidationError):
            s.load_processes([{"pid": "P", "burst": "abc"}])

    def test_bad_quantum_and_algorithm(self):
        with self.assertRaises(ValidationError):
            s.round_robin(self.procs, 0)
        with self.assertRaises(ValidationError):
            s.run("nope", self.procs)


if __name__ == "__main__":
    unittest.main()
