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
