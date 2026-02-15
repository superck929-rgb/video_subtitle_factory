import os
import re
import subprocess
import pandas as pd

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

VIDEOS_DIR = os.path.join(PROJECT_DIR, "videos")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
ENDING_DIR = os.path.join(PROJECT_DIR, "ending")
FONTS_DIR = os.path.join(PROJECT_DIR, "fonts")

EXCEL_PATH = os.path.join(PROJECT_DIR, "brand.xlsx")
FONT_PATH = os.path.join(FONTS_DIR, "Pretendard-Bold.ttf")

# 엔딩 파일명(오빠 폴더에 맞춰 두 파일을 준비해둔 상태 가정)
ENDING_16x9 = os.path.join(ENDING_DIR, "ending_16x9_3s.mp4")
ENDING_9x16 = os.path.join(ENDING_DIR, "ending_9x16_3s.mp4")

# 타임라인(초)
OPENING_SEC = 4.0
ENDING_SEC = 3.0

# 스크롤 기본 속도(px/sec)
BASE_SCROLL_SPEED = 220

# 스크롤 자막 높이(비율별 y 위치)
Y_TOP = 0.06   # 9:16 상단
Y_BOTTOM = 0.88  # 16:9 하단

# 스타일
SCROLL_COLOR = "white@0.9"   # 흰색 90% 불투명 (=10% 투과 느낌)
SCROLL_BORDER_W = 3
SCROLL_BORDER_COLOR = "black@1"

# 오프닝 스타일 (박스 없음)
SEASON_COLOR = "yellow"
SEASON_BORDER_W = 6
BRAND_COLOR = "white"
BRAND_BORDER_W = 10
BRAND_BORDER_COLOR = "black@1"

def run(cmd: list[str]) -> None:
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

def ffprobe_json(path: str) -> dict:
    # width/height/duration 가져오기
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-show_entries", "format=duration",
        "-of", "json",
        path
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    import json
    return json.loads(p.stdout)

def safe_drawtext_text(s: str) -> str:
    # ffmpeg drawtext에서 ':' '\' "'" 같은 문자가 문제될 수 있어 최소한 escape
    # (중문/한글은 그대로 가능)
    s = s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return s

def extract_brand_from_filename(filename: str) -> str:
    # 01_blackbean.mp4 -> BLACKBEAN
    base = os.path.splitext(filename)[0]
    if "_" in base:
        brand = base.split("_", 1)[1]
    else:
        brand = base
    return brand.upper()

def build_filter(width: int, height: int, duration: float, season_text: str, brand_text: str, scroll_text: str) -> tuple[str, str]:
    """
    returns (vf_filter, ending_file)
    """
    is_landscape = width >= height
    ending_file = ENDING_16x9 if is_landscape else ENDING_9x16

    # 스크롤 구간 종료(엔딩 3초 직전)
    # 전체 편집은 "원본 영상 위에 자막" + "뒤에 엔딩 붙이기" 방식이므로
    # 여기 duration은 원본의 길이. 스크롤은 원본 마지막 ENDING_SEC 전에 페이드아웃되도록.
    scroll_start = OPENING_SEC
    scroll_end = max(scroll_start + 1.0, duration - ENDING_SEC)  # 최소 1초는 보장

    # 9:16 상단, 16:9 하단
    y_ratio = Y_BOTTOM if is_landscape else Y_TOP
    y_expr = f"(h*{y_ratio})"

    # 스크롤 x 수식: 오른쪽 -> 왼쪽, 반복
    # x = w - mod( (t-scroll_start)*speed , w+text_w )
    # speed는 기본 속도 사용. (짧은 영상 완주 보정은 2차 단계에서 추가할게)
    speed = BASE_SCROLL_SPEED
    x_expr = f"w-mod((t-{scroll_start})*{speed}, w+text_w)"

    # 스크롤 페이드아웃: 엔딩 직전에 자연스럽게 사라지게(마지막 0.6초)
    fade_dur = 0.6
    alpha_scroll = (
        f"if(lt(t,{scroll_start}),0,"
        f" if(lt(t,{scroll_end - fade_dur}),1,"
        f"  if(lt(t,{scroll_end}),({scroll_end}-t)/{fade_dur},0)"
        f" ))"
    )

    # 오프닝 페이드 인/아웃(0~4초)
    # 0~0.6초 페이드인, 3.3~4초 페이드아웃
    op_fade_in = 0.6
    op_fade_out_start = 3.3
    alpha_open = (
        f"if(lt(t,{op_fade_in}), t/{op_fade_in},"
        f" if(lt(t,{op_fade_out_start}),1,"
        f"  if(lt(t,{OPENING_SEC}), ({OPENING_SEC}-t)/({OPENING_SEC}-{op_fade_out_start}), 0)"
        f" ))"
    )

    season_text = safe_drawtext_text(season_text)
    brand_text = safe_drawtext_text(brand_text)
    scroll_text = safe_drawtext_text(scroll_text)

    # 글자 크기(해상도 비례)
    # 브랜드는 화면 가로 기준 6~7%, 시즌은 절반
    brand_fs = "max(36, w*0.065)"
    season_fs = "max(20, w*0.032)"

    # 시즌은 브랜드 위쪽 (중앙 정렬)
    # y = center - brand_half - gap - season_height
    season_y = "(h*0.40)"  # 중앙보다 조금 위(감각적으로 안정적)
    brand_y  = "(h*0.46)"  # 시즌 아래

    # 오프닝 drawtext 2개 + 스크롤 drawtext 1개
    vf = (
        f"drawtext=fontfile='{FONT_PATH}':"
        f"text='{season_text}':"
        f"fontsize={season_fs}:"
        f"fontcolor={SEASON_COLOR}@1:"
        f"borderw={SEASON_BORDER_W}:"
        f"bordercolor={BRAND_BORDER_COLOR}:"
        f"x=(w-text_w)/2:"
        f"y={season_y}:"
        f"alpha='{alpha_open}':"
        f"enable='between(t,0,{OPENING_SEC})'"
        f","
        f"drawtext=fontfile='{FONT_PATH}':"
        f"text='{brand_text}':"
        f"fontsize={brand_fs}:"
        f"fontcolor={BRAND_COLOR}@1:"
        f"borderw={BRAND_BORDER_W}:"
        f"bordercolor={BRAND_BORDER_COLOR}:"
        f"x=(w-text_w)/2:"
        f"y={brand_y}:"
        f"alpha='{alpha_open}':"
        f"enable='between(t,0,{OPENING_SEC})'"
        f","
        f"drawtext=fontfile='{FONT_PATH}':"
        f"text='{scroll_text}':"
        f"fontsize=max(22,w*0.03):"
        f"fontcolor={SCROLL_COLOR}:"
        f"borderw={SCROLL_BORDER_W}:"
        f"bordercolor={SCROLL_BORDER_COLOR}:"
        f"x={x_expr}:"
        f"y={y_expr}:"
        f"alpha='{alpha_scroll}':"
        f"enable='between(t,{scroll_start},{scroll_end})'"
    )

    return vf, ending_file

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 엑셀 읽기
    df = pd.read_excel(EXCEL_PATH)
    expected_cols = ["파일명", "시즌", "소개문구"]
    for c in expected_cols:
        if c not in df.columns:
            raise ValueError(f"엑셀 컬럼명이 필요해: {expected_cols} / 현재: {list(df.columns)}")

    for _, row in df.iterrows():
        filename = str(row["파일명"]).strip()
        if not filename or filename.lower() == "nan":
            continue

        season = str(row["시즌"]).strip()
        scroll_text = str(row["소개문구"]).strip()

        input_path = os.path.join(VIDEOS_DIR, filename)
        if not os.path.exists(input_path):
            print(f"[SKIP] videos 폴더에 없음: {filename}")
            continue

        info = ffprobe_json(input_path)
        width = int(info["streams"][0]["width"])
        height = int(info["streams"][0]["height"])
        duration = float(info["format"]["duration"])

        brand = extract_brand_from_filename(filename)

        vf, ending_file = build_filter(width, height, duration, season, brand, scroll_text)

        # 1) 원본 영상에 자막 입힌 임시 파일 생성
        temp_main = os.path.join(OUTPUT_DIR, f"__temp__{os.path.splitext(filename)[0]}.mp4")
        cmd1 = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "192k",
            temp_main
        ]
        run(cmd1)

        # 2) 엔딩 붙이기 (re-encode로 안정적으로 concat)
        final_out = os.path.join(OUTPUT_DIR, f"{os.path.splitext(filename)[0]}_out.mp4")

        # concat을 위한 list 파일
        concat_list = os.path.join(OUTPUT_DIR, "__concat__.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            f.write("file '" + ffconcat_escape(temp_main) + "'\n")
            f.write("file '" + ffconcat_escape(ending_file) + "'\n")

        cmd2 = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "192k",
            final_out
        ]
        run(cmd2)

        # 임시 파일 삭제(원하면 주석 처리)
        try:
            os.remove(temp_main)
            os.remove(concat_list)
        except Exception:
            pass

        print(f"[DONE] {final_out}")

if __name__ == "__main__":
    main()
