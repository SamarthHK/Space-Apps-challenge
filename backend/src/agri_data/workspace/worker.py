import argparse
import threading
from uuid import uuid4

from agri_data.api.data import DataSettings
from .accounts import AccountStore
from .errors import WorkspaceUnavailable
from .fields import FieldStore
from .jobs import ACCOUNT_PROTOCOL, JobStore
from .settings import AccountSettings, WorkspaceSettings
from .store import WorkspaceStore


class AccountWorker:
    def __init__(self, accounts):
        self.accounts = accounts

    def heartbeat(self, worker_id):
        with self.accounts.workspace.session() as connection:
            connection.execute(
                "INSERT INTO workspace_workers(worker_id,workspace_id,project_ids,protocol,canonical_schema) "
                "VALUES (%s,%s,'{}',%s,%s) ON CONFLICT(worker_id) DO UPDATE SET "
                "heartbeat_at=clock_timestamp(),canonical_schema=EXCLUDED.canonical_schema,protocol=EXCLUDED.protocol",
                (worker_id, self.accounts.deployment_id, ACCOUNT_PROTOCOL, self.accounts.data_settings.schema),
            )

    def remove_worker(self, worker_id):
        with self.accounts.workspace.session() as connection:
            connection.execute("DELETE FROM workspace_workers WHERE worker_id=%s AND workspace_id=%s",
                               (worker_id, self.accounts.deployment_id))

    def run_once(self, worker_id):
        with self.accounts.workspace.session() as connection:
            account = connection.execute(
                "SELECT a.user_id,a.deployment_id,a.workspace_id,a.canonical_schema,a.project_id "
                "FROM workspace_accounts a JOIN workspace_jobs j ON j.workspace_id=a.workspace_id "
                "WHERE a.active AND a.deployment_id=%s AND a.canonical_schema=%s "
                "AND j.project_ids <@ ARRAY[a.project_id] AND "
                "((j.status='queued' AND j.available_at<=clock_timestamp()) OR "
                "(j.status='running' AND j.lease_until<clock_timestamp())) "
                "ORDER BY j.created_at,j.job_id LIMIT 1",
                (self.accounts.deployment_id, self.accounts.data_settings.schema),
            ).fetchone()
        if account is None:
            return False
        return JobStore(self.accounts.scoped_fields(account)).run_once(worker_id)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Durable workspace import/export worker; no model execution")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job, then exit")
    args = parser.parse_args(argv)
    store = WorkspaceStore(WorkspaceSettings.from_env())
    data_settings = DataSettings.from_env()
    accounts = AccountStore(store, data_settings, AccountSettings.from_env())
    fields = FieldStore(store, data_settings)
    private = accounts.settings.mode == "accounts"
    if not (accounts.ready() if private else fields.ready()):
        parser.exit(2, "Provision workspace storage and configure authorized canonical project writes first.\n")
    jobs = AccountWorker(accounts) if private else JobStore(fields)
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
