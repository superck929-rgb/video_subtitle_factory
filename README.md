FFmpeg 에러:

Error opening output file ... Invalid argument


원인 거의 확정:

👉 drawtext 필터 안에 들어간 Windows 절대경로 (C:...) 때문

Windows의 \ 가 FFmpeg 필터에서는 이스케이프 문자처럼 작동해서
필터 문자열이 깨짐 → FFmpeg가 인자를 잘못 해석 → 출력 파일 생성 실패

그래서 output 폴더가 비어 있는 거야.

✅ 해결 방법 (가장 안정적인 방식)
1️⃣ 절대경로 사용하지 말 것

❌ 이렇게 쓰면 안 됨

C:\projects\video_subtitle_factory\fonts\Pretendard-Bold.ttf

2️⃣ 상대경로로 통일
🔹 폰트 경로 수정
FONT_PATH = "fonts/Pretendard-Bold.ttf"

🔹 엔딩 경로 수정
ENDING_16x9 = "ending/ending_16x9_3s.mp4"
ENDING_9x16 = "ending/ending_9x16_3s.mp4"

🎯 핵심 원칙

drawtext 안에서는 절대경로 쓰지 않는다

슬래시는 / 사용

프로젝트 폴더 기준 상대경로만 사용

🔁 수정 후 실행
python auto_video.py

📌 만약 또 에러 나면

FFmpeg 로그에서

👉 drawtext=fontfile=... 포함된 줄
👉 그 위아래 5줄만 캡처

그거 보면 바로 정확히 어디가 깨졌는지 알 수 있음.

🎬 video_subtitle_factory 현재 상태 요약
1️⃣ 프로그램 구조

Python 기반 자동 영상 제작 시스템

입력

brand.xlsx

파일명

시즌

소개문구

처리

ffprobe로 영상 해상도/길이 자동 분석

opening 4초:

시즌 텍스트

브랜드 텍스트

페이드 인/아웃 적용

4초 이후:

소개문구 스크롤

마지막 3초:

엔딩 영상 자동 연결

출력
output/
   01_blackbean_out.mp4
   02_our_out.mp4
   ...

2️⃣ 해결된 핵심 문제들

이번 작업에서 해결한 구조적 문제:

drawtext 파싱 오류

콤마(,) escape 문제

max() / mod() 함수 파싱 문제

Windows 백슬래시 문제

CRLF 줄바꿈 문제

UTF-8 인코딩 문제

text 대신 textfile 방식으로 스크롤 안정화

👉 현재 구조는 안정화된 상태

3️⃣ 현재 필터 구조 (안정 버전)

시즌 / 브랜드 → text=

스크롤 → textfile=

alpha 수식 → 콤마 escape 처리

box=0 유지

x 스크롤 방식 → w-(t-4.0)*220 (mod 제거)

이 구조는 건드리지 않는 것이 안전

4️⃣ 반복 사용 가능 여부

✔ Excel만 수정하면 무한 반복 가능
✔ 여러 영상 자동 처리 가능
✔ 동일 구조 유지 시 parsing 문제 재발 가능성 낮음

5️⃣ 앞으로 수정 가능 영역

영상 보고 조정 가능한 부분:

시즌 글자 크기

브랜드 글자 크기

시즌/브랜드 Y 위치

스크롤 속도

스크롤 위치 (상단/하단)

페이드 시간 조정

색상 변경

📌 현재 상태 정의

이건 단순 스크립트가 아니라

Excel 기반 자동 영상 자막 + 엔딩 합성 시스템

1차 자동화 엔진 완성 상태

PowerShell에서 push
cd C:\projects\video_subtitle_factory
git add README.md
git commit -m "Update README (usage, structure, ffmpeg fallback, build notes)"
git push

2) README.md에 넣을 최종 내용 (복사해서 그대로 사용)
# Video Subtitle Factory (영상 자막 공장)

브랜드별 영상에 **오프닝 타이틀(시즌/브랜드)** + **스크롤 소개문구**를 자동으로 입히고, 마지막에 **엔딩 영상**을 붙여 최종 결과물을 생성합니다.  
(9:16 / 16:9 모두 지원)

---

## 주요 기능

- Excel(`brand.xlsx`) 기반 배치 처리
- 오프닝 타이틀 자동 삽입
  - 상단: 시즌(예: `26 春季款`)
  - 하단: 브랜드명(예: `BLACKBEAN`)
- 브랜드명이 긴 경우(10자 초과) 자동 축소 표시 (9:16에서 화면 밖으로 나가는 문제 방지)
- 스크롤 소개문구(상단/하단 위치는 비율별 설정)
  - 16:9: 기존 스크롤 크기 유지
  - 9:16: 스크롤 글자 크기 조정(요구사항 반영)
- 영상 종료 직전에 오디오/영상 페이드아웃 후 엔딩으로 자연스럽게 전환
- 엔딩 영상 자동 합치기
  - `ending/ending_16x9_3s.mp4`
  - `ending/ending_9x16_3s.mp4`
- CJK(대만 번체) 폰트 지원
  - 폰트 파일을 `fonts/`에 넣어 drawtext로 사용

---

## 폴더 구조

아래 구조를 유지해야 합니다.



video_subtitle_factory/
auto_video.py
brand.xlsx
videos/
fonts/
ending/
tools/ (선택: ffmpeg 포함 배포용)
output/ (자동 생성)


- `videos/` : 원본 영상(.mp4) 넣는 곳
- `brand.xlsx` : 파일명/시즌/소개문구 입력
- `fonts/` : 폰트 파일 저장
- `ending/` : 엔딩 영상 저장
- `tools/` : (선택) `ffmpeg.exe`, `ffprobe.exe`를 넣어 배포용으로 사용 가능
- `output/` : 결과 영상 생성 폴더(자동 생성)

---

## Excel (brand.xlsx) 컬럼

필수 컬럼:

- `파일명`
- `시즌`
- `소개문구`

예시:

| 파일명 | 시즌 | 소개문구 |
|---|---|---|
| 01_blackbean.mp4 | 26 春季款 | 韓系春季新款上架… |

---

## 실행 방법 (개발/로컬)

PowerShell에서 프로젝트 폴더로 이동 후 실행:

```bash
python auto_video.py


결과물은 output/ 폴더에 생성됩니다.

FFmpeg 사용 방식 (중요)

본 프로젝트는 다음 우선순위로 ffmpeg/ffprobe를 찾습니다.

tools/ffmpeg.exe, tools/ffprobe.exe가 있으면 그 파일 사용

없으면 시스템 PATH에 등록된 ffmpeg/ffprobe 사용

둘 다 없으면 에러

배포 환경(동료 PC)에서는 tools/ 폴더에 ffmpeg를 함께 포함하는 것을 권장합니다.

폰트 (대만 번체 깨짐 해결)

CJK(중국어 번체) 문자가 깨지는 경우, CJK 지원 폰트를 fonts/에 넣고 사용합니다.

예:

fonts/SourceHanSansTC-Bold.otf

fonts/NotoSansTC-Bold.ttf

GitHub에 업로드 시 주의 (.gitignore)

프로젝트는 기본적으로 mp4를 무시하도록 설정되어 있을 수 있습니다.

엔딩(mp4)을 GitHub에 포함하려면 .gitignore에 아래 예외를 추가합니다:

!ending/
!ending/*.mp4

동료에게 배포(압축 전달) 방식

동료에게 전달 시 아래 폴더/파일이 포함되어야 합니다.

auto_video.py

brand.xlsx

videos/ (동료가 영상 넣는 폴더)

fonts/

ending/

tools/ (권장: ffmpeg/ffprobe 포함)

output/ (없어도 됨, 실행 시 자동 생성)

동료는:

압축 해제

videos/에 새 영상 넣기

brand.xlsx 수정

실행

문제 해결 (Troubleshooting)

중국어(번체) 글자 깨짐: CJK 폰트(예: SourceHanSansTC, NotoSansTC)를 fonts/에 넣고 사용

엔딩 합치기 오류(해상도 불일치): 엔딩 영상은 입력 영상 비율/해상도에 맞게 준비되어야 함(필요 시 스케일/패드 처리)

FFmpeg 실행 실패: tools/ 폴더에 ffmpeg가 있는지 확인하거나 시스템 PATH에 ffmpeg 설치/등록

다음 단계(선택)

PyInstaller로 RUN.exe 실행파일 빌드(배포 편의성 향상)

실행 중 진행상태 표시(UI), 에러 팝업/로그 저장


---

원하면 내가 README에 **“exe 빌드 방법(PyInstaller 명령어/배포 zip 구성)” 섹션까지 포함한 버전**으로도 바로 만들어줄게.  
(오빠는 다음 창에서 exe 얘기하자고 했으니, 원하면 그때 합쳐서 업데이트해도 돼.)


📦 YB Video Automation System v1.1
(영상 생성 + SNS 업로드 자동화 설계 문서)
1️⃣ 프로젝트 개요

이 시스템은 다음을 목표로 한다:

🎬 브랜드 영상 자동 생성

🧠 엑셀 기반 메타데이터 관리

📤 YouTube 자동 업로드

🔜 Facebook / Instagram 확장 가능 구조

2️⃣ 현재 완료된 기능
✅ 영상 자동 생성

엑셀 upload_1 시트 기반 영상 제작

브랜드명 자동 추출

시즌 텍스트 오버레이

스크롤 소개문구 자동 삽입

16:9 / 9:16 자동 비율 대응

엔딩 자동 연결

ffmpeg 기반 렌더링

✅ 엑셀 구조 (brand.xlsx)

실행용 시트명: upload_1

값(value) 기반 읽기 (data_only=True)

수식 대신 값 저장 권장

필수 컬럼
파일명	시즌	소개문구
3️⃣ YouTube 자동화 설계
🎯 업로드 전략

하나의 채널에 여러 브랜드 업로드

기본 공개 상태: 미등록 (unlisted)

테스트 후 공개 전환

🎬 자동 생성 메타데이터 구조
제목 (자동 조합 + GPT 옵션)

기본 구조:

【{시즌}】{브랜드} 韓系童裝新款上架｜東大門人氣品牌

설명

엑셀 소개문구 기반

GPT를 통해 유튜브용 마케팅 문장 변환 가능

150~250자 권장

해시태그

예시:

#韓國童裝
#東大門童裝
#童裝批發
#春季新品
#{브랜드명}

키워드(tags 필드)

유튜브 내부 검색 최적화용 배열 형태 입력

📂 업로드 파이프라인 구조
영상 생성
   ↓
엑셀 데이터 읽기
   ↓
GPT 변환 (선택)
   ↓
YouTube 미등록 업로드
   ↓
로그 저장

4️⃣ GPT 자동화 설계 (선택 기능)
활용 목적

유튜브용 제목 최적화

설명 마케팅 문장 생성

해시태그 자동 생성

권장 전략

초기 단계: 콘솔 출력 후 확인

안정화 이후: 완전 자동 업로드

5️⃣ Instagram / Facebook 확장 계획
Instagram

요구사항:

Professional 계정 (Business 또는 Creator)

Facebook 페이지 연결

Meta Graph API 사용

향후 가능 기능:

릴스 자동 업로드

썸네일 자동 지정

해시태그 자동 생성

Facebook 페이지

가능 기능:

페이지 동영상 자동 게시

브랜드별 게시글 자동 작성

다국어 설명 자동 삽입

6️⃣ 향후 고도화 로드맵
단계 1 (현재)

영상 자동 생성

유튜브 미등록 자동 업로드

수동 재생목록 관리

단계 2

썸네일 자동 생성

GPT 제목/설명 자동화 완성

업로드 로그 관리 시스템

단계 3

Instagram 자동 업로드

Facebook 자동 업로드

재생목록 자동 분류

7️⃣ 운영 전략

v1.x → 기능 안정화 중심

브랜드 단위 자동화 확장

B2B + 브랜드 홍보 병행

대만/홍콩 번체 시장 중심 콘텐츠 최적화

8️⃣ 버전 관리 정책

엑셀 구조 변경 시 버전 증가

upload_1 시트는 항상 실행용

이전 EXE는 백업 유지

ZIP 배포 파일에 버전 명시

예시:

YB_影片自動字幕系統_v1.1.zip

9️⃣ 시스템 철학

이 시스템은 단순 영상 제작 도구가 아니라

🎬 브랜드 콘텐츠 생산 자동화 플랫폼

을 목표로 한다.