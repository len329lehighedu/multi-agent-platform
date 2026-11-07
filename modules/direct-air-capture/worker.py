"""JSON subprocess and cancellable monitor for DAC simulations."""
import atexit, json, os, subprocess, sys, threading, time, weakref
from pathlib import Path

TIMEOUT_SECONDS = 20
_jobs = weakref.WeakSet()


class WorkerJob:
    def __init__(self, payload, on_done, timeout=TIMEOUT_SECONDS):
        self.payload, self.on_done, self.timeout = payload, on_done, timeout
        self.process = None; self.cancelled = threading.Event(); self.lock = threading.Lock(); self.thread = None
        _jobs.add(self)
    def start(self):
        self.thread = threading.Thread(target=self._run, name="dac-simulation-monitor", daemon=True); self.thread.start(); return self
    def _run(self):
        started = time.perf_counter()
        env = os.environ.copy()
        for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS"): env[key] = "1"
        message = None
        try:
            with self.lock:
                if self.cancelled.is_set(): return
                self.process = subprocess.Popen([sys.executable, str(Path(__file__).resolve())], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                process = self.process
            try: out, err = process.communicate(json.dumps(self.payload, allow_nan=False), timeout=self.timeout)
            except subprocess.TimeoutExpired:
                process.kill(); process.communicate(); raise ValueError(f"Simulation exceeded the {self.timeout:g}-second timeout.")
            if self.cancelled.is_set(): return
            if process.returncode: raise ValueError("Simulation worker failed. " + err[-500:])
            message = json.loads(out)
            if not message.get("ok"): raise ValueError(message.get("error", "Simulation failed."))
            message["result"]["worker_seconds"] = time.perf_counter()-started
        except Exception as exc: message = dict(ok=False, error=str(exc))
        finally:
            if self.process is not None:
                if self.process.poll() is None: self.process.kill(); self.process.wait(timeout=2)
                for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
                    if stream is not None: stream.close()
        if not self.cancelled.is_set(): self.on_done(message)
    def cancel(self):
        self.cancelled.set()
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
                try: self.process.wait(timeout=.5)
                except subprocess.TimeoutExpired: self.process.kill(); self.process.wait(timeout=2)


def _cleanup():
    for job in list(_jobs): job.cancel()
atexit.register(_cleanup)


def main():
    try:
        from engine import simulate
        payload = json.load(sys.stdin)
        print(json.dumps(dict(ok=True, result=simulate(payload["config"])), allow_nan=False))
    except Exception as exc: print(json.dumps(dict(ok=False, error=str(exc))))
if __name__ == "__main__": main()
