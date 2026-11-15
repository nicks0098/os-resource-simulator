import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from osim import memory as m
from osim.validators import ValidationError

TEXTBOOK = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
BELADY = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]


class MemoryTests(unittest.TestCase):
    def test_textbook_fault_counts(self):
        self.assertEqual(m.fifo(TEXTBOOK, 3).faults, 15)
        self.assertEqual(m.lru(TEXTBOOK, 3).faults, 12)
        self.assertEqual(m.optimal(TEXTBOOK, 3).faults, 9)

    def test_beladys_anomaly(self):
        self.assertEqual(m.fifo(BELADY, 3).faults, 9)
        self.assertEqual(m.fifo(BELADY, 4).faults, 10)

    def test_lru_has_no_anomaly(self):
        self.assertLessEqual(m.lru(BELADY, 4).faults, m.lru(BELADY, 3).faults)

    def test_optimal_is_lower_bound(self):
        for f in range(1, 6):
            self.assertLessEqual(m.optimal(TEXTBOOK, f).faults, m.lru(TEXTBOOK, f).faults)
            self.assertLessEqual(m.optimal(TEXTBOOK, f).faults, m.fifo(TEXTBOOK, f).faults)

    def test_hits_plus_faults_equals_length(self):
        r = m.lru(TEXTBOOK, 3)
        self.assertEqual(r.hits + r.faults, len(TEXTBOOK))

    def test_boundary_single_frame_all_distinct_and_repeat(self):
        self.assertEqual(m.fifo([1, 2, 3], 1).faults, 3)
        self.assertEqual(m.fifo([5, 5, 5, 5], 1).faults, 1)

    def test_invalid_inputs(self):
        for bad in ([], [1, -2], ["a"], [1.5]):
            with self.assertRaises(ValidationError):
                m.fifo(bad, 3)
        with self.assertRaises(ValidationError):
            m.fifo([1, 2], 0)
        with self.assertRaises(ValidationError):
            m.run_page("clock", [1], 1)

    def test_string_input_accepted(self):
        self.assertEqual(m.fifo("1, 2, 3", 3).faults, 3)

    # allocation
    def test_allocation_strategies(self):
        parts, reqs = [100, 500, 200, 300, 600], [212, 417, 112, 426]
        self.assertEqual(m.allocate("first", parts, reqs).unallocated, [426])
        best = m.allocate("best", parts, reqs)
        self.assertEqual(best.unallocated, [])
        self.assertEqual(best.internal_fragmentation, 433)
        self.assertEqual(m.allocate("worst", parts, reqs).assignments[0], 4)

    def test_allocation_invalid(self):
        with self.assertRaises(ValidationError):
            m.allocate("random", [10], [5])
        with self.assertRaises(ValidationError):
            m.allocate("first", [10, -5], [5])

    def test_request_larger_than_all_partitions(self):
        self.assertEqual(m.allocate("best", [10, 20], [50]).unallocated, [50])


if __name__ == "__main__":
    unittest.main()
