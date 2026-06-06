# Supabase 데이터베이스 휴면 방지 (Keep-Alive) 메커니즘

이 문서는 ROBO-Path 프로젝트에서 사용 중인 Supabase(PostgreSQL 기반) 데이터베이스의 무료 요금제(Free Tier) 휴면 정책을 방지하기 위한 자동화 메커니즘을 설명합니다.

## 1. 목적
Supabase의 무료 요금제는 일정 기간(보통 7일) 동안 데이터베이스에 활동(트래픽)이 없을 경우, 리소스 절약을 위해 프로젝트를 자동으로 휴면(Pause) 상태로 전환합니다. 로봇 주행 테스트가 간헐적으로 진행될 때 데이터베이스가 휴면 상태로 진입하는 것을 방지하기 위해 3일에 한 번씩 주기적인 접근(Ping)을 수행합니다.

## 2. 구성 요소

### 2.1 휴면 방지 전용 테이블 (`sleep_prevention_table`)
기존의 비즈니스 로직(메타데이터, 로그 등) 테이블에 영향을 주지 않기 위해 휴면 방지 전용의 더미 테이블을 생성하여 사용합니다.

* **테이블 명:** `sleep_prevention_table`
* **역할:** GitHub Actions에서 읽어갈 수 있는 더미 데이터(`wake_up`) 제공
* **마이그레이션 파일:** `supabase/migrations/20260607000000_create_sleep_prevention_table.sql`
* **보안 정책:** 인증되지 않은 익명 사용자(anon)도 GitHub Actions를 통해 REST API로 `SELECT` 할 수 있도록 RLS(Row Level Security) 읽기 권한 개방

### 2.2 GitHub Actions 워크플로우
파이썬 환경 구축 없이 빠르고 가볍게 실행될 수 있도록 셸 환경의 `curl` 명령어를 사용하여 Supabase REST API를 직접 호출합니다.

* **워크플로우 경로:** `.github/workflows/supabase-keep-alive.yml`
* **실행 주기:** `cron: '0 0 */3 * *'` (UTC 기준 매 3일 자정마다 실행)
* **환경 변수 (Secrets):**
  * `SUPABASE_URL`: Supabase 프로젝트 URL
  * `SUPABASE_KEY`: Supabase 프로젝트의 anon(public) API 키
* **검증:** HTTP 응답 코드가 `200 OK`인지 자체 검증하여 로그를 남깁니다.

## 3. 관리 방법
* **수동 테스트:** GitHub 저장소의 **Actions** 탭에서 **Supabase Keep Alive Ping** 워크플로우를 선택한 뒤 **Run workflow** 버튼을 통해 수동으로 정상 작동 여부를 확인할 수 있습니다.
* **보안:** 해당 테이블은 오직 읽기 권한만 개방되어 있으므로, 악의적인 데이터 쓰기나 기존 시스템(지도, 로그)에 대한 접근은 RLS 정책에 의해 원천 차단됩니다.
