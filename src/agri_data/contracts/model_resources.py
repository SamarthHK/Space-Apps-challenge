"""Measured admission and cooperative stopping for owned, sequential CPU experiments."""

import os
import subprocess
import threading
import time

import psutil

from .storage_proof import require


GIB = 1024 ** 3


def snapshot():
    memory = psutil.virtual_memory()
    result = {"available_ram_bytes": memory.available, "process_rss_bytes": psutil.Process().memory_info().rss,
              "cpu_threads": 2, "device": "cpu", "gpu_free_mib": None}
    try:
        process = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=10)
        if process.returncode == 0:
            result["gpu_free_mib"] = [int(value.strip()) for value in process.stdout.splitlines()]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return result


def admit(measured_increment_bytes, telemetry=None, reserve_gib=6, margin=1.25):
    require(measured_increment_bytes >= 0 and reserve_gib >= 6 and margin >= 1.25,
            "Resource admission cannot weaken the shared-machine reserve")
    telemetry = telemetry or snapshot()
    budget = int(measured_increment_bytes * margin)
    require(telemetry["available_ram_bytes"] - budget >= reserve_gib * GIB,
            "Insufficient free RAM for the measured job plus shared-machine reserve")
    return {"snapshot": telemetry, "increment_budget_bytes": budget,
            "ram_reserve_gib": reserve_gib, "margin": margin,
            "gpu_allocation_bytes": 0, "vram_reserve_gib_if_gpu_used": 3}


class ResourceMonitor:
    def __init__(self, reserve_gib=6):
        self.reserve = reserve_gib * GIB
        self.stopped = threading.Event()
        self.process = psutil.Process()
        self.start_rss = self.process.memory_info().rss
        self.peak_rss = self.start_rss
        self.minimum_free = psutil.virtual_memory().available
        self.reserve_breached = False
        self.started = time.monotonic()
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def _read(self):
        self.peak_rss = max(self.peak_rss, self.process.memory_info().rss)
        self.minimum_free = min(self.minimum_free, psutil.virtual_memory().available)
        self.reserve_breached |= self.minimum_free < self.reserve

    def _sample(self):
        while not self.stopped.wait(0.1):
            self._read()

    def __enter__(self):
        self._read()
        self.check()
        self.thread.start()
        return self

    def check(self):
        self._read()
        require(not self.reserve_breached, "Shared-machine RAM reserve was breached; stop this owned experiment")

    def after_iteration(self, info):
        self._read()
        return not self.reserve_breached

    def __exit__(self, *_):
        self.stopped.set()
        self.thread.join()
        self._read()

    def report(self):
        return {"elapsed_seconds": time.monotonic() - self.started, "pid": os.getpid(),
                "start_rss_bytes": self.start_rss, "peak_rss_bytes": self.peak_rss,
                "incremental_peak_bytes": max(0, self.peak_rss - self.start_rss),
                "minimum_free_ram_bytes": self.minimum_free, "reserve_breached": self.reserve_breached,
                "device": "cpu", "cpu_threads": 2, "gpu_allocated_bytes": 0}
