#!/bin/bash
#
# 헤드리스(배치모드) Unity 시뮬레이터 실행 스크립트.
#
# 사용처:
#   - launchd(com.robopath.simulator)가 이 스크립트를 foreground 로 실행하여
#     Unity 프로세스를 직접 supervise/재시작한다.
#   - 수동 실행도 가능: `bash scripts/run_simulator.sh`  (Ctrl+C 로 종료)
#
# 중요:
#   - 가이드 §6.1 의 원본은 끝에 `&`(백그라운드)를 붙였으나, launchd 가 프로세스를
#     추적/재시작하려면 포그라운드여야 하므로 여기서는 `exec` 로 Unity 를 포그라운드
#     실행한다. (수동으로 백그라운드가 필요하면 `bash run_simulator.sh &` 처럼 호출부에서 처리)
#   - 경로 하드코딩 금지 원칙(가이드 §5.3)에 따라 $HOME / 환경변수 기반으로 동적 처리한다.
#
set -euo pipefail

# 프로젝트 루트 (ROBOPATH_ROOT 로 override 가능)
PROJECT_ROOT="${ROBOPATH_ROOT:-$HOME/ROBO-Path_project}"

# 실제 Unity 프로젝트 폴더 (Assets/ ProjectSettings/ 가 있는 위치)
# 주의: 저장소 구조상 Unity 프로젝트는 Unity/ROBO-Path-Simulator 하위에 있다.
PROJECT_PATH="$PROJECT_ROOT/Unity/ROBO-Path-Simulator"

# Unity 에디터 바이너리 (UNITY_BIN 로 override 가능). 가이드 §4 기준 6000.4.11f1.
UNITY_BIN="${UNITY_BIN:-/Applications/Unity/Hub/Editor/6000.4.11f1/Unity.app/Contents/MacOS/Unity}"

# 피드백 서브프로세스(push_feedback.py)가 사용할 robopath python 절대경로.
# SubprocessTelemetrySink.cs 는 ROBOPATH_PYTHON 을 1순위로 읽는다. 그 안의 conda 자동추정은
# Windows 기준(USERPROFILE/python.exe)이라 Mac 에선 항상 'python' 폴백으로 떨어져
# 배치모드에서 그 python 을 못 찾는다. 따라서 여기서 명시한다.
# (경로 하드코딩 금지 원칙에 따라 $HOME 기반; 외부에서 ROBOPATH_PYTHON 지정 시 그것을 우선.)
export ROBOPATH_PYTHON="${ROBOPATH_PYTHON:-$HOME/miniconda3/envs/robopath/bin/python}"

LOG_DIR="$PROJECT_PATH/Logs"
mkdir -p "$LOG_DIR"

echo "[run_simulator] PROJECT_PATH=$PROJECT_PATH"
echo "[run_simulator] UNITY_BIN=$UNITY_BIN"
echo "[run_simulator] ROBOPATH_PYTHON=$ROBOPATH_PYTHON"
echo "[run_simulator] logFile=$LOG_DIR/simulator.log"

if [ ! -x "$UNITY_BIN" ]; then
  echo "[run_simulator] ERROR: Unity 바이너리를 찾을 수 없음: $UNITY_BIN" >&2
  echo "[run_simulator]        UNITY_BIN 환경변수로 정확한 경로를 지정하세요." >&2
  exit 1
fi

# 피드백 서브프로세스(push_feedback.py)가 사용할 Python.
# SubprocessTelemetrySink 의 python 경로 추정은 Windows 기준(USERPROFILE/python.exe)이라
# Mac 에선 폴백 'python' 으로 떨어지고, Unity 배치모드 환경에서 그걸 못 찾아 피드백 호출이
# 실패한다. robopath conda 환경의 python 절대경로를 ROBOPATH_PYTHON 으로 명시해 해결한다.
# (이미 설정돼 있으면 그 값을 존중. 경로 하드코딩 금지 원칙에 따라 $HOME 기반으로 구성.)
export ROBOPATH_PYTHON="${ROBOPATH_PYTHON:-$HOME/miniconda3/envs/robopath/bin/python}"
echo "[run_simulator] ROBOPATH_PYTHON=$ROBOPATH_PYTHON"
if [ ! -x "$ROBOPATH_PYTHON" ]; then
  echo "[run_simulator] WARN: ROBOPATH_PYTHON 경로에 실행 가능한 python 이 없음: $ROBOPATH_PYTHON" >&2
  echo "[run_simulator]       ROBOPATH_PYTHON 환경변수로 robopath python 절대경로를 지정하세요." >&2
fi

# 포그라운드 실행(exec): launchd 가 이 Unity 프로세스를 직접 supervise 한다.
# -quit 를 주지 않아야 executeMethod 이후에도 Editor 가 살아서 플레이 모드를 유지한다.
exec "$UNITY_BIN" \
  -batchmode \
  -nographics \
  -projectPath "$PROJECT_PATH" \
  -executeMethod SimulatorLauncher.RunHeadless \
  -logFile "$LOG_DIR/simulator.log"
