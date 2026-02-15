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
