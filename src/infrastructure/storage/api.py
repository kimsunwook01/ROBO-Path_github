"""
ROBO-Path 로컬 SSD 스토리지 관리 FastAPI 서버
============================================
역할: 워크스테이션(Isaac Sim)에서 생성된 PCD 및 CSV 파일을
      라즈베리파이 1TB SSD에 수신·저장하고 서빙합니다.

엔드포인트:
  POST /upload/pcd          - PCD 파일 업로드 및 SSD 저장
  POST /upload/log          - CSV 로그 파일 업로드 및 SSD 저장
  GET  /files/{file_path}   - 저장된 파일 다운로드/서빙
  GET  /list/pcd            - 저장된 PCD 파일 목록 조회
  GET  /list/logs           - 저장된 로그 파일 목록 조회
  GET  /health              - 서버 상태 및 스토리지 가용 공간 확인

아키텍처 참고:
  - 이 파일은 Infrastructure 계층에 속합니다.
  - 비즈니스 로직(도메인)은 포함하지 않습니다.
  - 파일 저장 경로는 .env의 STORAGE_BASE_PATH로 제어됩니다.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

# .env 파일 로드 (STORAGE_BASE_PATH 등 환경 변수)
load_dotenv()

# ─────────────────────────────────────────────
# 앱 초기화
# ─────────────────────────────────────────────
app = FastAPI(
    title="ROBO-Path Storage API",
    version="1.0.0",
    description="라즈베리파이 SSD 스토리지 관리 API",
)

# ─────────────────────────────────────────────
# 스토리지 경로 설정
# ─────────────────────────────────────────────
STORAGE_BASE_PATH = Path(os.getenv("STORAGE_BASE_PATH", "/mnt/ssd/robo-path-data"))
PCD_DIR = STORAGE_BASE_PATH / "pcd"
LOG_DIR = STORAGE_BASE_PATH / "logs"

# 서버 시작 시 디렉토리가 없으면 자동 생성
PCD_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────
def _get_disk_usage(path: Path) -> dict:
    """스토리지 가용 공간 정보를 반환합니다."""
    usage = shutil.disk_usage(path)
    return {
        "total_gb": round(usage.total / (1024**3), 2),
        "used_gb": round(usage.used / (1024**3), 2),
        "free_gb": round(usage.free / (1024**3), 2),
        "used_percent": round(usage.used / usage.total * 100, 1),
    }


# ─────────────────────────────────────────────
# 헬스 체크
# ─────────────────────────────────────────────
@app.get("/health", summary="서버 상태 및 스토리지 가용 공간 확인")
def health_check():
    """서버가 정상 작동 중인지 확인하고 스토리지 사용량을 반환합니다."""
    return {
        "status": "ok",
        "storage_base": str(STORAGE_BASE_PATH),
        "disk": _get_disk_usage(STORAGE_BASE_PATH),
        "pcd_count": len(list(PCD_DIR.glob("*.pcd"))),
        "log_count": len(list(LOG_DIR.glob("*.csv"))),
    }


# ─────────────────────────────────────────────
# 파일 업로드
# ─────────────────────────────────────────────
@app.post("/upload/pcd", summary="PCD 파일 업로드")
async def upload_pcd(file: UploadFile = File(...)):
    """
    Isaac Sim에서 생성된 3D 포인트 클라우드(.pcd) 파일을 수신하여
    SSD의 pcd/ 디렉토리에 저장합니다.
    """
    if not file.filename.endswith(".pcd"):
        raise HTTPException(
            status_code=400,
            detail="PCD 파일(.pcd)만 업로드 가능합니다.",
        )

    # 동일 파일명 충돌 방지: 타임스탬프 접두사 부여
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    dest = PCD_DIR / safe_filename

    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size_mb = round(dest.stat().st_size / (1024**2), 2)

    return {
        "status": "success",
        "filename": safe_filename,
        "size_mb": file_size_mb,
        "saved_path": str(dest),
        "download_url": f"/files/pcd/{safe_filename}",
    }


@app.post("/upload/log", summary="CSV 로그 파일 업로드")
async def upload_log(file: UploadFile = File(...)):
    """
    로봇 주행 로그(.csv) 파일을 수신하여
    SSD의 logs/ 디렉토리에 저장합니다.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="CSV 파일(.csv)만 업로드 가능합니다.",
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    dest = LOG_DIR / safe_filename

    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size_kb = round(dest.stat().st_size / 1024, 2)

    return {
        "status": "success",
        "filename": safe_filename,
        "size_kb": file_size_kb,
        "saved_path": str(dest),
        "download_url": f"/files/logs/{safe_filename}",
    }


# ─────────────────────────────────────────────
# 파일 서빙 및 목록 조회
# ─────────────────────────────────────────────
@app.get("/files/{file_path:path}", summary="저장된 파일 다운로드")
async def serve_file(file_path: str):
    """
    SSD에 저장된 파일을 다운로드합니다.
    예: GET /files/pcd/20260518_123456_map.pcd
    """
    full_path = STORAGE_BASE_PATH / file_path

    # 경로 탈출 공격(Path Traversal) 방지
    try:
        full_path.resolve().relative_to(STORAGE_BASE_PATH.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="접근이 허용되지 않는 경로입니다.")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    return FileResponse(full_path)


@app.get("/list/pcd", summary="저장된 PCD 파일 목록 조회")
def list_pcd_files() -> List[dict]:
    """SSD에 저장된 PCD 파일 목록과 메타데이터를 반환합니다."""
    files = []
    for f in sorted(PCD_DIR.glob("*.pcd"), reverse=True):
        stat = f.stat()
        files.append({
            "filename": f.name,
            "size_mb": round(stat.st_size / (1024**2), 2),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "download_url": f"/files/pcd/{f.name}",
        })
    return files


@app.get("/list/logs", summary="저장된 로그 파일 목록 조회")
def list_log_files() -> List[dict]:
    """SSD에 저장된 CSV 로그 파일 목록과 메타데이터를 반환합니다."""
    files = []
    for f in sorted(LOG_DIR.glob("*.csv"), reverse=True):
        stat = f.stat()
        files.append({
            "filename": f.name,
            "size_kb": round(stat.st_size / 1024, 2),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "download_url": f"/files/logs/{f.name}",
        })
    return files
