import os, subprocess, sys, tempfile, unittest, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from osim.bash_bridge import run_script
from osim.validators import ValidationError
from osim import analysis


def cli(*args, stdin=None):
    return subprocess.run([sys.executable, os.path.join(ROOT, "main.py"), *args], capture_output=True,
                          text=True, input=stdin, cwd=ROOT, timeout=120)


class IntegrationTests(unittest.TestCase):
    def test_cli_each_module(self):
        for args in (["schedule", "--algo", "rr", "--quantum", "3"], ["memory", "--algo", "lru"],
                     ["deadlock"], ["disk", "--algo", "scan"]):
            r = cli(*args)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(r.stdout.strip())

    def test_cli_invalid_input_returns_error_code(self):
        r = cli("memory", "--refs", "1 2 x", "--frames", "3")
        self.assertEqual(r.returncode, 2)
        self.assertIn("Error", r.stderr)

    def test_cli_missing_and_corrupt_file(self):
        self.assertEqual(cli("disk", "--input", "/no/such/file.json").returncode, 2)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{not json")
        self.assertEqual(cli("deadlock", "--input", f.name).returncode, 2)
        os.unlink(f.name)

    def test_menu_survives_bad_input_and_exits(self):
        r = cli("menu", stdin="99\nabc\n4\n\n-5\n0\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("not a valid option", r.stdout)
        self.assertIn("Invalid input", r.stdout)
        self.assertIn("Goodbye", r.stdout)

    def test_menu_eof_is_graceful(self):
        self.assertEqual(cli("menu", stdin="").returncode, 0)

    def test_bash_integration(self):
        self.assertIn("Live System Information", run_script("system_info.sh"))
        self.assertIn("not found", run_script("missing.sh"))

    def test_analysis_creates_artifacts(self):
        analysis.full_report()
        for f in ("scheduling_gantt.png", "page_faults.png", "disk_head_movement.png"):
            self.assertTrue(os.path.getsize(os.path.join(analysis.CHARTS, f)) > 1000)

    def test_log_is_written(self):
        cli("disk")
        log = open(os.path.join(ROOT, "logs", "activity.log")).read()
        self.assertIn("|INFO|storage|", log)


if __name__ == "__main__":
    unittest.main()
