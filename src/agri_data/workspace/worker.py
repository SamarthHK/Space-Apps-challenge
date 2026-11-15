import argparse
import threading
from uuid import uuid4

from agri_data.api.data import DataSettings
from .errors import WorkspaceUnavailable
from .fields import FieldStore
from .jobs import JobStore
from .settings import WorkspaceSettings
from .store import WorkspaceStore


def main():
    parser = argparse.ArgumentParser(description="Durable shared-workspace import/export worker; no model execution")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job, then exit")
    args = parser.parse_args()
    store = WorkspaceStore(WorkspaceSettings.from_env())
    fields = FieldStore(store, DataSettings.from_env())
    if not fields.ready():
        parser.exit(2, "Provision workspace storage and configure authorized canonical project writes first.\n")
    jobs = JobStore(fields)
    identifier = "worker_" + uuid4().hex
    stop = threading.Event()

    def heartbeat():
        while not stop.wait(5):
            try:
                jobs.heartbeat(identifier)
            except WorkspaceUnavailable:
                pass

    jobs.heartbeat(identifier)
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        while True:
            try:
                worked = jobs.run_once(identifier)
            except WorkspaceUnavailable:
                worked = False
            if args.once:
                break
            if not worked:
                stop.wait(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        thread.join(timeout=12)
        try:
            jobs.remove_worker(identifier)
        except WorkspaceUnavailable:
            pass


if __name__ == "__main__":
    main()
