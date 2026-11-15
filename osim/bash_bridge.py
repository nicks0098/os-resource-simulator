"""Python -> Bash integration. Runs the helper scripts in /scripts safely."""
import os
import shutil
import subprocess

from .logger import get_logger

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
log = get_logger()


def run_script(name: str, *args: str, timeout: int = 20) -> str:
    """Run scripts/<name> with bash and return stdout. Never raises; returns an
    explanatory message if bash or the script is unavailable."""
    path = os.path.join(SCRIPTS, name)
    bash = shutil.which("bash")
    if bash is None:
        log.error("bash not found, cannot run %s", name)
        return "[bash not available on this system]"
    if not os.path.isfile(path):
        log.error("script missing: %s", path)
        return f"[script not found: {name}]"
    try:
        res = subprocess.run([bash, path, *map(str, args)], capture_output=True,
                             text=True, timeout=timeout, cwd=ROOT)
    except subprocess.TimeoutExpired:
        log.error("script timeout: %s", name)
        return f"[script timed out: {name}]"
    if res.returncode != 0:
        log.warning("script %s exited with %s: %s", name, res.returncode, res.stderr.strip())
        return f"[script error {res.returncode}] {res.stderr.strip()}"
    log.info("bash script %s ok", name)
    return res.stdout
