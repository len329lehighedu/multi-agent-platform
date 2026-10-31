"""JSON-only isolated training and bounded subprocess lifecycle."""
import atexit
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import weakref

TIMEOUT_SECONDS=120
_jobs=weakref.WeakSet()


class WorkerJob:
    """One job per owning Document; callback runs in monitor, never touches UI."""
    def __init__(self,payload,on_done,timeout=TIMEOUT_SECONDS):
        self.payload=payload; self.on_done=on_done; self.timeout=timeout
        self.process=None; self.cancelled=threading.Event(); self.lock=threading.Lock()
        self.thread=None
        _jobs.add(self)

    def start(self):
        self.thread=threading.Thread(target=self._run,name='neural-fit-monitor',daemon=True)
        self.thread.start()
        return self

    def _run(self):
        started=time.perf_counter()
        env=os.environ.copy()
        for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
            env[key]='1'
        try:
            with self.lock:
                if self.cancelled.is_set(): return
                self.process=subprocess.Popen([sys.executable,str(Path(__file__).resolve())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
                process=self.process
            try:
                out,err=process.communicate(json.dumps(self.payload,allow_nan=False),timeout=self.timeout)
            except subprocess.TimeoutExpired:
                process.kill();process.communicate()
                raise ValueError(f"Training exceeded the {self.timeout:g}-second operational timeout.")
            if self.cancelled.is_set(): return
            if process.returncode:
                raise ValueError('Training worker failed. '+err[-500:])
            message=json.loads(out)
            if not message.get('ok'):
                raise ValueError(message.get('error','Training failed.'))
            message['result']['worker_seconds']=time.perf_counter()-started
        except Exception as exc:
            message=dict(ok=False,error=str(exc))
        finally:
            if self.process is not None:
                if self.process.poll() is None:
                    self.process.kill();self.process.wait(timeout=2)
                for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
                    if stream is not None: stream.close()
        if not self.cancelled.is_set(): self.on_done(message)

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            process=self.process
            if process is not None and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=.5)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=2)


def _cleanup():
    for job in list(_jobs): job.cancel()


atexit.register(_cleanup)


def main():
    try:
        # Standalone script import: only this module directory is on sys.path.
        from engine import parse_csv,prepare_data,fit_model
        payload=json.load(sys.stdin)
        table=parse_csv(payload['csv'])
        data=prepare_data(table,payload['features'],payload['target'])
        result=fit_model(data,payload['config'])
        print(json.dumps(dict(ok=True,result=result),allow_nan=False))
    except Exception as exc:
        print(json.dumps(dict(ok=False,error=str(exc))))


if __name__=='__main__': main()
