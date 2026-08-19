import subprocess
import tempfile
import threading
import queue
import sys
import os
import time

INPUT_PATCH = """
import builtins

_real_input = builtins.input

def input(prompt=""):
    print("__INPUT__" + prompt, flush=True)
    return _real_input("")

builtins.input = input
"""

class PythonSession:

    def __init__(self):
        self.process = None
        self.temp_file = None

        self.stdout_queue = queue.Queue()
        self.stderr_queue = queue.Queue()

        self.stdout_thread = None
        self.stderr_thread = None

        self.accumulated_stdout = ""
        self.accumulated_stderr = ""

        self.start_time = None
        self.timeout = 10

    def start(self, code):
        temp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        )

        temp.write(INPUT_PATCH)
        temp.write("\n")
        temp.write(code)
        temp.close()

        self.temp_file = temp.name

        self.process = subprocess.Popen(
            [sys.executable, "-u", self.temp_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        self.start_time = time.time()

        self.stdout_thread = threading.Thread(
            target=self._reader,
            args=(self.process.stdout, self.stdout_queue),
            daemon=True
        )

        self.stderr_thread = threading.Thread(
            target=self._reader,
            args=(self.process.stderr, self.stderr_queue),
            daemon=True
        )

        self.stdout_thread.start()
        self.stderr_thread.start()

    def _reader(self, stream, q):
        try:
            while True:
                ch = stream.read(1)
                if not ch:
                    break
                q.put(ch)
        except Exception:
            pass

    def send_input(self, text):
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(text + "\n")
                self.process.stdin.flush()
            except BrokenPipeError:
                pass

    def get_stdout(self):
        while not self.stdout_queue.empty():
            self.accumulated_stdout += self.stdout_queue.get()
        return self.accumulated_stdout

    def get_stderr(self):
        while not self.stderr_queue.empty():
            self.accumulated_stderr += self.stderr_queue.get()
        return self.accumulated_stderr

    def clear_accumulated(self):
        """Clears the accumulated output (useful after prompt extraction)."""
        self.accumulated_stdout = ""

    def running(self):
        if self.process is None:
            return False
        return self.process.poll() is None

    def stop(self):
        if self.process:
            try:
                self.process.kill()
                self.process.wait(timeout=1)
            except Exception:
                pass

        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except Exception:
                pass

        self.process = None

    def timed_out(self):
        if self.process is None:
            return False
        return (time.time() - self.start_time) > self.timeout