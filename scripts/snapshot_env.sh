#!/bin/bash
# ROBO-Path 라즈베리파이 환경 스냅샷 저장 스크립트
# 사용법: bash scripts/snapshot_env.sh
# 목적: pip/apt 패키지 목록과 OS 정보를 SSD에 날짜별로 백업하여 환경 복원을 가능하게 함

SNAPSHOT_DIR="/mnt/ssd/robo-path-data/backups/env_snapshot_$(date +%Y%m%d_%H%M%S)"
PROJECT_DIR="/home/pi/ROBO-Path_project"

echo "=== ROBO-Path 환경 스냅샷 시작 ==="
mkdir -p "$SNAPSHOT_DIR"

# 1. apt 설치 패키지 목록 저장
echo "[1/4] apt 패키지 목록 저장 중..."
dpkg --get-selections > "$SNAPSHOT_DIR/apt_packages.txt"
echo "  -> $SNAPSHOT_DIR/apt_packages.txt"

# 2. Python pip 패키지 목록 저장
echo "[2/4] pip 패키지 목록 저장 중..."
source "$PROJECT_DIR/venv/bin/activate"
pip freeze > "$SNAPSHOT_DIR/pip_packages.txt"
deactivate
echo "  -> $SNAPSHOT_DIR/pip_packages.txt"

# 3. OS 및 커널 버전 기록
echo "[3/4] OS 정보 저장 중..."
uname -a > "$SNAPSHOT_DIR/os_info.txt"
cat /etc/os-release >> "$SNAPSHOT_DIR/os_info.txt"
echo "  -> $SNAPSHOT_DIR/os_info.txt"

# 4. 스냅샷 목록 파일 업데이트
echo "[4/4] 스냅샷 메타데이터 기록 중..."
echo "$(date '+%Y-%m-%d %H:%M:%S') | $SNAPSHOT_DIR" >> "/mnt/ssd/robo-path-data/backups/snapshot_history.log"

echo ""
echo "=== 스냅샷 완료: $SNAPSHOT_DIR ==="
echo ""
echo "복원 방법:"
echo "  apt:  sudo dpkg --set-selections < $SNAPSHOT_DIR/apt_packages.txt && sudo apt-get dselect-upgrade -y"
echo "  pip:  pip install -r $SNAPSHOT_DIR/pip_packages.txt"
