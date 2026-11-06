"""Check the fake HTTP demo and explicitly seeded synthetic bank in a disposable API container.

Run after scripts/seed_core_banking.py, inside the API with fake RAG/LLM/auth.
No provider credentials or model inference are required. Creates a synthetic
queued request and a greeting thread, and reads the synthetic banking database.
"""

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import UUID

from app.agent.core_banking import CoreBanking
from app.agent.tools import AgentTools
from app.contracts import User


def request(path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = Request('http://127.0.0.1:8000' + path, data=data, headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=10) as response:
        assert UUID(response.headers['X-Request-ID']).version == 4
        return response.status, json.load(response)

def main() -> None:
    if any(os.getenv(name, "fake") != "fake" for name in ("RAG_BACKEND", "LLM_BACKEND", "AUTH_BACKEND")):
        raise RuntimeError("Release smoke requires fake RAG, LLM and authentication")
    status, chat = request('/chat', {'message': 'Hello release demo'})
    assert status == 200 and chat['intent'] == 'question' and chat['needs_human'] is False
    status, job = request('/ask/jobs', {'question': 'Annual fee demo?'})
    assert status == 202 and job['position'] >= 1
    for _attempt in range(90):
        status, result = request('/ask/jobs/' + job['job_id'])
        assert status == 200 and result['status'] != 'failed'
        if result['status'] == 'done':
            break
        time.sleep(1)
    else:
        raise AssertionError('Real Compose worker did not complete job within 90 seconds')
    assert result['result']['found'] is True and result['result']['citations']
    status, agent = request('/agent', {'message': 'Hello release demo'})
    assert status == 200 and agent['status'] == 'completed' and agent['pending_action'] is None
    bank = CoreBanking('/app/data/core_banking.db')
    for i in range(1, 4):
        user = User(f'synthetic-user-{i}', 'credit')
        assert len(bank.accounts(user)) == 1
        assert len(AgentTools(user, bank).tra_cuu_giao_dich()) == 5
        foreign = f'SYN-ACC-{(i % 3) + 1:03d}'
        assert AgentTools(user, bank).tra_cuu_giao_dich(foreign) == []
    assert bank.transactions(User('dev', 'public')) == []
    with bank.connect() as connection:
        try:
            connection.execute('CREATE TABLE release_qa_readonly_probe (id INTEGER)')
        except sqlite3.OperationalError as error:
            assert 'readonly' in str(error)
        else:
            raise AssertionError('Core banking accepted a write')
    print(json.dumps({'chat': 'passed', 'http_job_real_worker': 'done_with_citations',
                      'agent_fake_greeting': 'completed_no_tool_execution', 'synthetic_users': 3,
                      'transactions_per_owner': 5, 'foreign_account_rows': 0, 'sqlite_read_only': True,
                      'seed_sha256': hashlib.sha256(Path('/app/data/core_banking.db').read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
