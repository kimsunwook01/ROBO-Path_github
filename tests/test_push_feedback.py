"""
push_feedback.py 진입점에 대한 통합 테스트.

push_feedback.py 는 Unity 서브프로세스로 호출되는 CLI 스크립트이므로,
실제 동작 검증을 위해 subprocess 로 별도 프로세스를 띄워 종료 코드와
로그 출력을 확인한다.

정합화 메모(2026-06-19):
- push_feedback.py 의 로깅은 StreamHandler(sys.stdout) 로 구성되어 모든 로그가
  STDOUT 으로 나간다. 과거 테스트는 메시지를 stderr 에서 찾아 항상 실패했으므로,
  stdout+stderr 를 합쳐서(스트림 변경에도 견고하게) 검사한다.
- DISCOVERY 페이로드는 더 이상 "무시"되지 않고 정식 처리된다(Spec C).
  좌표가 없으면 'DISCOVERY payload missing coordinates' 를 남기고 정상 종료(0)한다.
- FEEDBACK/DISCOVERY 가 아닌 미지(unknown) 타입만 'Ignored unknown payload type'
  으로 무시된다(과거 'Ignored non-feedback payload type' 메시지는 폐기됨).
- push_feedback.py 는 `from src...` 절대 임포트를 쓰므로, 서브프로세스가 프로젝트
  루트를 PYTHONPATH 로 인식해야 한다. 아래 헬퍼가 cwd/PYTHONPATH 를 주입해
  호출 환경과 무관하게 동작하도록 한다.
"""
import os
import sys
import json
import subprocess

import pytest

# 이 테스트 파일(tests/) 기준 프로젝트 루트
_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_SCRIPT = os.path.join("src", "infrastructure", "bridge", "push_feedback.py")

# 해피패스는 실제 Supabase 쓰기를 수반하므로 기본적으로 건너뛰고,
# 명시적으로 옵트인(ROBOPATH_RUN_DB_TESTS=1)했을 때만 실행한다.
_RUN_DB_TESTS = os.getenv("ROBOPATH_RUN_DB_TESTS", "").lower() in ("1", "true", "yes")


def run_push_feedback(payload_arg: str) -> subprocess.CompletedProcess:
    """push_feedback.py 를 별도 프로세스로 실행한다.

    - cwd 를 프로젝트 루트로 고정하고 PYTHONPATH 에 루트를 주입해
      `import src...` 가 호출 환경과 무관하게 항상 동작하도록 한다.
    - 현재 pytest 를 실행 중인 인터프리터(sys.executable)를 그대로 사용한다.
    """
    env = {**os.environ, "PYTHONPATH": _ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")}
    return subprocess.run(
        [sys.executable, _SCRIPT, payload_arg],
        capture_output=True, text=True, cwd=_ROOT, env=env,
    )


def _combined(result: subprocess.CompletedProcess) -> str:
    """로그가 stdout 으로 나가지만, 스트림 변경에 견고하도록 합쳐서 검사."""
    return (result.stdout or "") + (result.stderr or "")


def test_push_feedback_invalid_json():
    """잘못된 JSON 이면 파싱 에러를 남기고 비정상 종료(1)."""
    result = run_push_feedback("invalid_json")
    assert result.returncode == 1
    assert "Failed to parse JSON" in _combined(result)


def test_push_feedback_handles_discovery():
    """DISCOVERY 는 무시되지 않고 처리된다(Spec C).

    좌표가 없는 빈 데이터면 'missing coordinates' 를 남기고 정상 종료(0)한다.
    과거에는 DISCOVERY 를 무시했으나 리팩터링으로 정식 처리 경로가 생겼다.
    """
    payload = json.dumps({"type": "DISCOVERY", "data": {}})
    result = run_push_feedback(payload)
    assert result.returncode == 0
    out = _combined(result)
    assert "DISCOVERY payload missing coordinates" in out
    assert "Ignored" not in out  # 더 이상 무시되지 않음을 명시적으로 고정


def test_push_feedback_ignore_unknown_type():
    """FEEDBACK/DISCOVERY 가 아닌 미지의 타입만 무시하고 정상 종료(0)한다."""
    payload = json.dumps({"type": "SOMETHING_ELSE", "data": {}})
    result = run_push_feedback(payload)
    assert result.returncode == 0
    assert "Ignored unknown payload type" in _combined(result)


def test_push_feedback_missing_fields():
    """FEEDBACK 인데 필수 필드가 빠지면 에러를 남기고 비정상 종료(1)."""
    payload = json.dumps({"type": "FEEDBACK", "data": {"from_node_id": "123"}})
    result = run_push_feedback(payload)
    assert result.returncode == 1
    assert "Missing required fields" in _combined(result)


@pytest.mark.skipif(
    not _RUN_DB_TESTS,
    reason="실 Supabase 쓰기를 수반하므로 ROBOPATH_RUN_DB_TESTS=1 일 때만 실행",
)
def test_push_feedback_happy_path():
    """필수 필드를 갖춘 FEEDBACK 은 정상 종료(0)하고 mission_log 적재를 시도한다.

    실제 Supabase 연결이 필요하므로 옵트인 플래그가 있을 때만 실행한다.
    DB 삽입 실패는 스크립트 내부에서 잡아 로깅만 하므로 종료 코드는 0 이다.
    """
    payload = json.dumps({
        "type": "FEEDBACK",
        "data": {
            "from_node_id": "node_a",
            "to_node_id": "node_b",
            "platform": "wheeled",
            "L": 0.2,
            "S": 0.8,
            "E": 1.0,
        },
    })
    result = run_push_feedback(payload)
    assert result.returncode == 0
    out = _combined(result)
    assert ("Inserted mission_log" in out) or ("Failed to insert mission_log" in out)
