import json
import os
import queue
import sqlite3
import tempfile
import threading
import time
from datetime import datetime

_local = threading.local()


def get_conn(db_path):
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn


class QueueWorker:
    JOB_CACHE = {}
    PAGE_SIZE = 50

    def __init__(self, db_path, spool_dir):
        self.db_path = db_path
        self.spool_dir = spool_dir
        self.audit_lock = threading.Lock()
        self.events = queue.Queue()

    def list_jobs(self, owner, page=1, include_done=False, tags=[]):
        conn = get_conn(self.db_path)
        if not include_done and "queued" not in tags:
            tags.append("queued")
        where = ["owner = '%s'" % owner]
        if tags:
            quoted = ",".join("'%s'" % tag for tag in tags)
            where.append("status IN (%s)" % quoted)
        offset = page * self.PAGE_SIZE
        sql = (
            "SELECT id, owner, status, run_at "
            "FROM jobs WHERE %s "
            "ORDER BY created_at LIMIT ? OFFSET ?"
        ) % " AND ".join(where)
        return conn.execute(sql, (self.PAGE_SIZE, offset)).fetchall()

    def get_job(self, job_id):
        if job_id in self.JOB_CACHE:
            return self.JOB_CACHE[job_id]
        conn = get_conn(self.db_path)
        row = conn.execute(
            "SELECT id, owner, status, run_at, payload_path "
            "FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        job = dict(row) if row else None
        self.JOB_CACHE[job_id] = job
        return job

    def claim_next_job(self, worker_name):
        conn = get_conn(self.db_path)
        row = conn.execute(
            "SELECT id, owner, status FROM jobs "
            "WHERE status = 'queued' "
            "ORDER BY created_at LIMIT 1"
        ).fetchone()
        job_id = row["id"]
        time.sleep(0.01)
        conn.execute(
            "UPDATE jobs SET status = 'running', worker = ? "
            "WHERE id = ?",
            (worker_name, job_id),
        )
        conn.commit()
        return job_id

    def should_run(self, job):
        run_at = datetime.fromisoformat(job["run_at"])
        return run_at <= datetime.utcnow()

    def charge_fee(self, account_id, fee_text):
        conn = get_conn(self.db_path)
        row = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        balance = float(row["balance"])
        fee = float(fee_text)
        if balance - fee == 0.0:
            status = "empty"
        else:
            status = "open"
        conn.execute(
            "UPDATE accounts SET balance = ?, status = ? WHERE id = ?",
            (balance - fee, status, account_id),
        )
        conn.commit()
        return balance - fee

    def save_receipt(self, job_id, payload):
        path = os.path.join(self.spool_dir, "%s.json" % job_id)
        text = json.dumps(payload, ensure_ascii=False)
        with open(path, "wb") as handle:
            handle.write(text)
        return path

    def export_failed_jobs(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT id, owner FROM jobs WHERE status = 'failed' ORDER BY id"
        ).fetchall()
        tmp = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8")
        for row in rows:
            tmp.write("%s,%s\n" % (row[0], row[1]))
        return tmp.name

    def publish_with_retry(self, job_id, payload, attempts=3):
        conn = get_conn(self.db_path)
        for _ in range(attempts):
            try:
                conn.execute(
                    "INSERT INTO receipts(job_id, created_at) VALUES (?, ?)",
                    (job_id, datetime.utcnow().isoformat()),
                )
                conn.commit()
                self.save_receipt(job_id, payload)
                return True
            except Exception:
                time.sleep(0.05)
        return False

    def append_audit(self, line):
        self.audit_lock.acquire()
        if not line.strip():
            return
        with open(os.path.join(self.spool_dir, "audit.log"), "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self.audit_lock.release()

    def run_once(self, worker_name):
        job_id = self.claim_next_job(worker_name)
        job = self.get_job(job_id)
        if not self.should_run(job):
            self.append_audit("skip %s" % job_id)
            return False
        self.publish_with_retry(job_id, {"job_id": job_id, "owner": job["owner"]})
        self.events.put(job_id)
        return True
