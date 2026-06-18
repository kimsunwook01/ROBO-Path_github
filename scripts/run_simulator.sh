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

LOG_DIR="$PROJECT_PATH/Logs"
mkdir -p "$LOG_DIR"

echo "[run_simulator] PROJECT_PATH=$PROJECT_PATH"
echo "[run_simulator] UNITY_BIN=$UNITY_BIN"
echo "[run_simulator] logFile=$LOG_DIR/simulator.log"

if [ ! -x "$UNITY_BIN" ]; then
  echo "[run_simulator] ERROR: Unity 바이너리를 찾을 수 없음: $UNITY_BIN" >&2
  echo "[run_simulator]        UNITY_BIN 환경변수로 정확한 경로를 지정하세요." >&2
  exit 1
fi

# 포그라운드 실행(exec): launchd 가 이 Unity 프로세스를 직접 supervise 한다.
# -quit 를 주지 않아야 executeMethod 이후에도 Editor 가 살아서 플레이 모드를 유지한다.
exec "$UNITY_BIN" \
  -batchmode \
  -nographics \
  -projectPath "$PROJECT_PATH" \
  -executeMethod SimulatorLauncher.RunHeadless \
  -logFile "$LOG_DIR/simulator.log"
