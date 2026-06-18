"""
일회성 스모크 테스트: Unity 의 SubprocessTelemetrySink 호출을 그대로 재현한다.
(cwd=프로젝트 루트, PYTHONPATH=루트, FEEDBACK 페이로드를 argv 로 전달)

실행:
    python scripts/smoke_push_feedback.py
    # 또는 conda 환경 python 명시:
    & "$env:USERPROFILE\anaconda3\envs\robopath\python.exe" scripts/smoke_push_feedback.py

주의: 존재하지 않는 노드(node_a/node_b)를 쓰므로 mission_logs 에 더미 행 1개가
      생길 수 있다. 연결 확인용이며, 신경 쓰이면 Supabase 에서 지우면 된다.
      실제 노드로 바꾸려면 아래 payload 의 from/to_node_id 를 교체.
"""
import os
import sys
import json
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPT = os.path.join("src", "infrastructure", "bridge", "push_feedback.py")

payload = {
    "type": "FEEDBACK",
    "data": {
        "from_node_id": "node_a",
        "to_node_id": "node_b",
        "platform": "wheeled",
        "L": 0.2,
        "S": 0.8,
        "E": 1.0,
        "battery_pct": 77,
    },
}

env = {**os.environ, "PYTHONPATH": ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")}

print(f"[smoke] python      : {sys.executable}")
print(f"[smoke] cwd (root)  : {ROOT}")
print(f"[smoke] payload     : {json.dumps(payload, ensure_ascii=False)}")
print("-" * 60)

result = subprocess.run(
    [sys.executable, SCRIPT, json.dumps(payload)],
    cwd=ROOT, env=env, capture_output=True, text=True,
)

print("returncode:", result.returncode)
print("--- STDOUT ---")
print(result.stdout.strip() or "(empty)")
print("--- STDERR ---")
print(result.stderr.strip() or "(empty)")
