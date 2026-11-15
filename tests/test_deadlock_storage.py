import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from osim import deadlock as d, storage as st
from osim.validators import ValidationError

ALLOC = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
MAX = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
Q = [98, 183, 37, 122, 14, 124, 65, 67]


class DeadlockTests(unittest.TestCase):
    def bank(self):
        return d.BankersAlgorithm(ALLOC, MAX, [3, 3, 2])

    def test_safe_sequence(self):
        r = self.bank().safety()
        self.assertTrue(r.safe)
        self.assertEqual(r.sequence, ["P1", "P3", "P4", "P0", "P2"])

    def test_need_matrix(self):
        self.assertEqual(self.bank().need[0], [7, 4, 3])

    def test_request_granted(self):
        self.assertTrue(self.bank().request(1, [1, 0, 2])[0])

    def test_request_exceeds_available(self):
        b = self.bank()
        b.request(1, [1, 0, 2])                 # available becomes [2, 3, 0]
        ok, msg = b.request(4, [3, 3, 0])       # 3 > 2 of resource A
        self.assertFalse(ok)
        self.assertIn("not available", msg)

    def test_request_within_available_but_unsafe_on_fresh_state(self):
        ok, msg = self.bank().request(4, [3, 3, 0])
        self.assertFalse(ok)
        self.assertIn("UNSAFE", msg)

    def test_request_leading_to_unsafe_state_rolls_back(self):
        b = self.bank()
        b.request(1, [1, 0, 2])
        before = (list(b.avail), [r[:] for r in b.alloc])
        ok, msg = b.request(0, [0, 2, 0])
        self.assertFalse(ok)
        self.assertIn("UNSAFE", msg)
        self.assertEqual(before, (b.avail, b.alloc))

    def test_request_exceeds_claim(self):
        self.assertIn("maximum claim", self.bank().request(1, [9, 0, 0])[1])

    def test_unsafe_state_detected(self):
        b = d.BankersAlgorithm([[1, 0], [0, 1]], [[2, 2], [2, 2]], [0, 0])
        self.assertFalse(b.safety().safe)

    def test_detection(self):
        dead = d.detect_deadlock([[0, 1, 0], [2, 0, 0], [3, 0, 3], [2, 1, 1], [0, 0, 2]],
                                 [[0, 0, 0], [2, 0, 2], [0, 0, 1], [1, 0, 0], [0, 0, 2]], [0, 0, 0])
        self.assertEqual(dead, ["P1", "P2", "P3", "P4"])
        self.assertEqual(d.detect_deadlock([[0], [0]], [[0], [0]], [0]), [])

    def test_invalid_inputs(self):
        with self.assertRaises(ValidationError):
            d.BankersAlgorithm(ALLOC, MAX, [1, 2])                   # wrong width
        with self.assertRaises(ValidationError):
            d.BankersAlgorithm([[5]], [[3]], [1])                    # alloc > max
        with self.assertRaises(ValidationError):
            self.bank().request(9, [0, 0, 0])                        # bad pid
        with self.assertRaises(ValidationError):
            self.bank().request(0, [1, 1])                           # bad vector
        with self.assertRaises(ValidationError):
            d.BankersAlgorithm([[1, 2], [3]], [[2, 2], [3, 3]], [0, 0])  # ragged


class StorageTests(unittest.TestCase):
    def test_textbook_totals(self):
        self.assertEqual(st.fcfs(Q, 53).total_movement, 640)
        self.assertEqual(st.sstf(Q, 53).total_movement, 236)
        self.assertEqual(st.scan(Q, 53, 200, "down").total_movement, 236)
        self.assertEqual(st.look(Q, 53, 200, "down").total_movement, 208)
        self.assertEqual(st.cscan(Q, 53, 200, "down").total_movement, 386)

    def test_look_never_worse_than_scan(self):
        for direction in ("up", "down"):
            self.assertLessEqual(st.look(Q, 53, 200, direction).total_movement,
                                 st.scan(Q, 53, 200, direction).total_movement)

    def test_boundary_head_and_requests_at_edges(self):
        self.assertEqual(st.fcfs([0, 199], 0, 200).total_movement, 199)  # 0 -> 0 -> 199
        self.assertEqual(st.sstf([5], 5, 200).total_movement, 0)
        self.assertEqual(st.scan([0, 199], 199, 200, "down").total_movement, 199)

    def test_invalid_inputs(self):
        with self.assertRaises(ValidationError):
            st.fcfs([250], 10, 200)       # beyond disk
        with self.assertRaises(ValidationError):
            st.fcfs([5], 200, 200)        # head out of range
        with self.assertRaises(ValidationError):
            st.fcfs([], 5, 200)
        with self.assertRaises(ValidationError):
            st.run("elevator", [1], 0)
        with self.assertRaises(ValidationError):
            st.run("scan", [1], 0, 200, "sideways")


if __name__ == "__main__":
    unittest.main()
