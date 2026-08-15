# 정기 실행 작업 (Scheduled Jobs)

주문 동기화와 환율 동기화를 Windows 작업 스케줄러에 등록하는 절차.

실행 환경: **로컬 PC (Windows)**. 저장소에 Dockerfile·IaC·CI 워크플로가 없고,
`.moai/project/tech.md`의 ECS/Fargate 섹션은 실제 운영 환경이 아니라 목표
아키텍처 기술이다. 서버로 이전하면 이 문서는 폐기하고 해당 플랫폼의
스케줄러 절차로 대체한다.

---

## 1. 대상 작업

| 작업 | 커맨드 | 권장 주기 | 1회 소요 |
|---|---|---|---|
| 주문 동기화 | `python manage.py sync_orders` | 5분 | 약 16초 (신규 0~2건 기준) |
| 환율 동기화 | `python manage.py sync_exchange_rates` | 하루 1회 | 약 4초 |

두 커맨드 모두:

- **멱등**하다. 중복 실행해도 데이터가 어긋나지 않는다.
- 할 일이 없으면 아무것도 쓰지 않고 종료 코드 0으로 끝난다.
- 실패하면 `CommandError`로 **종료 코드가 0이 아니다** → 작업 스케줄러의
  "마지막 실행 결과"에 그대로 드러난다.

### 커맨드별 특성

**`sync_orders`**

- 인자 없이 실행하면 gimssine·etoile 양쪽을 순차 동기화한다.
- 스토어별 독립 트랜잭션이라 한쪽 실패가 다른 쪽을 롤백하지 않는다.
- 증분 기준점은 `orders_store_sync_watermark` 테이블에서 읽고, 이번 배치에서
  실제로 받아온 주문들의 최대 `updated_at`으로만 전진한다(단조 증가).
- `--store gimssine` 으로 한쪽만 돌릴 수 있다.

**`sync_exchange_rates`**

- 인자 없이 실행하면 "마지막 저장일 다음날 ~ 오늘(UTC)" 범위를 채운다.
- 주말·공휴일은 환율이 없다. Frankfurter가 직전 영업일 값을 그 영업일 날짜로
  돌려주므로, 이미 저장된 날짜로 판정되어 스킵된다 — **주말 실행은 무해한
  무동작**이다. 현재 DB의 2일짜리 공백 32개는 전부 주말이며 결함이 아니다.
- 하루에 여러 번 돌아도 이미 있는 날짜는 건너뛴다.
- ⚠️ **ExchangeRate 레코드가 하나도 없으면 `--start` 없이는 실패한다.**
  최초 구축 시에만 해당하며, 현재는 2026-01-02부터 데이터가 있어 무관하다.

---

## 2. 래퍼 스크립트

작업 스케줄러는 `scripts\` 아래의 배치 파일을 실행한다. 직접 `python.exe`를
등록하지 않는 이유가 세 가지 있다.

1. **작업 디렉터리가 반드시 `backend\` 여야 한다.** Django 설정은
   python-decouple로 `.env`를 읽는데, 이 라이브러리는 작업 디렉터리에서
   위쪽으로 올라가며 `.env`를 찾는다. 다른 곳에서 실행하면 DB 접속 정보를
   찾지 못한다.
2. **`PYTHONIOENCODING=utf-8` 이 필요하다.** Windows 콘솔 기본 인코딩이
   cp949라, 출력이나 오류 메시지에 한글·특수문자가 섞이면 실제 오류가
   기록되기도 전에 `UnicodeEncodeError`로 죽는다. (실제로 겪은 문제다.)
3. **종료 코드를 전파해야 한다.** 그래야 실패가 "마지막 실행 결과"에 남는다.

| 스크립트 | 로그 |
|---|---|
| `scripts\sync_orders.bat` | `logs\sync_orders.log` |
| `scripts\sync_exchange_rates.bat` | `logs\sync_exchange_rates.log` |

### 창 숨김

작업 스케줄러는 `.bat`을 직접 실행하지 않고 `scripts\run_hidden.vbs`를 거친다.
그렇지 않으면 실행할 때마다 cmd 창이 화면에 뜬다 — `sync_orders`는 5분마다다.

```
wscript.exe "C:\app\scm_v2\scripts\run_hidden.vbs" "C:\app\scm_v2\scripts\sync_orders.bat"
```

`wscript.exe`는 창 없는 스크립트 호스트이고, VBS의 `Run(..., 0, True)`가 자식
프로세스를 숨긴 채 실행한 뒤 **종료 코드를 그대로 전달한다**. 종료 코드를
삼키면 "마지막 실행 결과"가 항상 0이 되어 실패를 놓치므로, 이 전달은 필수다.
(검증: 종료 코드 3을 반환하는 배치를 태우면 3이 그대로 나온다.)

`logs\` 는 `.gitignore` 대상이며 스크립트가 없으면 자동 생성한다.

`DJANGO_SETTINGS_MODULE` 은 `manage.py`가 `config.settings.local` 로 기본값을
설정하므로 별도 환경변수 지정이 필요 없다.

---

## 3. 등록 절차

### PowerShell (관리자 권한)

```powershell
$vbs     = "C:\app\scm_v2\scripts\run_hidden.vbs"
$action  = New-ScheduledTaskAction -Execute "wscript.exe" `
           -Argument ('"{0}" "C:\app\scm_v2\scripts\sync_orders.bat"' -f $vbs)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
           -RepetitionInterval (New-TimeSpan -Minutes 5) `
           -RepetitionDuration (New-TimeSpan -Days 3650)
$set     = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
           -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -StartWhenAvailable
$prin    = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
           -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName "scm_v2 sync_orders" `
    -Action $action -Trigger $trigger -Settings $set -Principal $prin `
    -Description "Shopify 주문 증분 동기화 (5분 주기)"
```

```powershell
$action  = New-ScheduledTaskAction -Execute "C:\app\scm_v2\scripts\sync_exchange_rates.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At 10:00
$set     = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
           -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -StartWhenAvailable
Register-ScheduledTask -TaskName "scm_v2 sync_exchange_rates" `
    -Action $action -Trigger $trigger -Settings $set `
    -Description "USD/KRW 환율 동기화 (일 1회)"
```

환율은 KST 10:00에 돌린다. UTC 기준 01:00이라 전일 환율이 확정된 뒤다.

> ⚠️ `-RepetitionDuration` 에 `[TimeSpan]::MaxValue` 를 주면 안 된다.
> `P99999999DT23H59M59S` 로 변환되어 작업 스케줄러가 XML을 거부한다
> (PowerShell 5.1에서 실제로 실패 확인). 위처럼 유한한 값(3650일)을 쓸 것.
> 등록 후에는 반드시 4절의 확인 절차로 반복 간격이 저장됐는지 볼 것.

### GUI 대안

작업 스케줄러 → 작업 만들기:

- **일반** 탭 → "사용자의 로그온 여부에 관계없이 실행" 선택
- **트리거** 탭 → 매일, 반복 간격 5분, 기간 "무기한"
- **동작** 탭 → 프로그램 시작 → `C:\app\scm_v2\scripts\sync_orders.bat`
- **설정** 탭 → **"작업이 이미 실행 중이면 다음 규칙 적용: 새 인스턴스 시작 안 함"**

마지막 항목이 중요하다. 4절 참고.

---

## 4. 중복 실행 처리

`sync_orders`는 **수동 동기화 버튼과 락을 공유하지 않는다.** 예약 실행과
사용자의 버튼 클릭이 같은 주문에 겹치면 둘 중 하나가 실패한다:

- 락 대기 시간 초과(MySQL 기본 50초), 또는
- 중복 키 충돌(신규 주문을 양쪽이 동시에 INSERT)

**데이터는 안전하다.** 주요 모델에 unique 제약이 있어 중복 행이 생길 수 없고,
실패한 쪽은 트랜잭션째 롤백된다. 워터마크 전진도 같은 트랜잭션 안이라 함께
되돌아가므로, 겹침이 주문 누락으로 이어지지는 않는다. 실패한 회차의 주문은
다음 회차에 그대로 수집된다.

사용자 눈에는 수동 동기화가 "실패"로 보이는 성가심만 남는다. 잦으면 워터마크
행에 `select_for_update` 를 걸어 중복 실행을 차단하는 방안을 검토할 것.

**예약 실행끼리의 겹침**은 작업 스케줄러의 "새 인스턴스 시작 안 함" 설정으로
막는다. 반드시 켤 것.

---

## 5. 등록 후 확인

```powershell
Get-ScheduledTask -TaskName "scm_v2 *" | Get-ScheduledTaskInfo |
    Select-Object TaskName, LastRunTime, LastTaskResult, NextRunTime
```

- `LastTaskResult` 가 `0` 이면 정상. `0` 이 아니면 로그 파일을 확인한다.
- 등록 직후 5분 이상 기다렸다가 `NextRunTime` 이 갱신되는지, 로그에 항목이
  계속 쌓이는지 확인한다 (3절의 반복 간격 경고 참고).

로그 확인:

```powershell
Get-Content C:\app\scm_v2\logs\sync_orders.log -Tail 20
```

---

## 6. 알아둘 한계

- **PC가 꺼져 있거나 절전 상태면 동기화가 멈춘다.** 이번 #38163~#38266 누락
  사고처럼, 멈춘 사실을 아무도 모르는 상태가 길어질 수 있다. 로그의 마지막
  기록 시각을 가끔 확인할 것.
- **로그오프 상태에서도 실행되지 않는다.** 현재 등록은 `LogonType Interactive`
  이며, 계정 비밀번호를 저장하지 않기 위한 선택이다. 로그오프 중에도 돌리려면
  `LogonType S4U` 로 바꾸면 되는데(이 역시 비밀번호 불필요), **관리자 권한
  PowerShell이 필요하다.** 비승격 상태에서 `Set-ScheduledTask` 는
  액세스 거부(0x80070005)로 실패한다. S4U로 바꾸면 비대화형 세션에서 돌기
  때문에 `run_hidden.vbs` 없이도 창이 뜨지 않는다.
- **체크아웃된 브랜치의 코드가 실행된다.** 작업 스케줄러는 작업 트리를 그대로
  쓰므로, 브랜치를 바꾸면 동기화 동작도 바뀐다. 워터마크 수정은
  `feat/spec-purchase-order-011-damaged-exchange` 브랜치에 있으므로, master를
  체크아웃한 상태로 예약 실행이 돌면 수정 이전 코드가 동작한다.
- **로그는 자동 회전하지 않는다.** 5분 주기 기준 연 20MB 남짓이라 당장 문제는
  없지만, 주기적으로 비워줄 것.

---

Version: 1.0.0
Last Updated: 2026-08-15
