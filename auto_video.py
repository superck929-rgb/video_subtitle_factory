import os
import subprocess
import pandas as pd
import json

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

VIDEOS_DIR = os.path.join(PROJECT_DIR, "videos")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
ENDING_DIR = os.path.join(PROJECT_DIR, "ending")
FONTS_DIR = os.path.join(PROJECT_DIR, "fonts")

EXCEL_PATH = os.path.join(PROJECT_DIR, "brand.xlsx")

# ✅ drawtext fontfile은 상대경로가 안정적 (cwd=PROJECT_DIR로 고정할 것)
FONT_REL = "fonts/Pretendard-Bold.ttf"
FONT_ABS = os.path.join(PROJECT_DIR, FONT_REL)

ENDING_16x9 = os.path.join(ENDING_DIR, "ending_16x9_3s.mp4")
ENDING_9x16 = os.path.join(ENDING_DIR, "ending_9x16_3s.mp4")

OPENING_SEC = 4.0
ENDING_SEC = 3.0
BASE_SCROLL_SPEED = 220

Y_TOP = 0.06
Y_BOTTOM = 0.88

SCROLL_COLOR = "white@0.9"
SCROLL_BORDER_W = 3
SCROLL_BORDER_COLOR = "black@1"

SEASON_COLOR = "yellow"
SEASON_BORDER_W = 6
BRAND_COLOR = "white"
BRAND_BORDER_W = 10
BRAND_BORDER_COLOR = "black@1"


def run(cmd: list[str]) -> None:
    print("\n[RUN]", " ".join(cmd))
    p = subprocess.run(
        cmd,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if p.returncode != 0:
        print("\n[FFMPEG STDOUT]\n", p.stdout)
        print("\n[FFMPEG STDERR]\n", p.stderr)
        raise RuntimeError("FFmpeg 실행 실패 (위 로그 확인)")


def ffprobe_json(path: str) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-show_entries", "format=duration",
        "-of", "json",
        path
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def safe_drawtext_text(s: str) -> str:
    """
    ✅ 짧은 텍스트(시즌/브랜드)용 최소 escape
    - 콜론(:)은 반드시 escape
    - 따옴표/백슬래시 방어
    """
    s = str(s)
    s = s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    s = s.replace("\r", " ").replace("\n", " ")
    return s


def extract_brand_from_filename(filename: str) -> str:
    base = os.path.splitext(filename)[0]
    if "_" in base:
        brand = base.split("_", 1)[1]
    else:
        brand = base
    return brand.upper()


def ffconcat_escape(path: str) -> str:
    return path.replace("'", "''")


def relpath_for_ffmpeg(abs_path: str) -> str:
    """
    ✅ ffmpeg 인자/필터에 넣을 경로는 상대경로 + 슬래시가 안정적
    (cwd=PROJECT_DIR 기준)
    """
    rel = os.path.relpath(abs_path, PROJECT_DIR)
    return rel.replace("\\", "/")


def build_filter(width: int, height: int, duration: float,
                 season_text: str, brand_text: str,
                 scroll_textfile_rel: str) -> tuple[str, str]:
    """
    returns (vf_filter, ending_file)
    """
    is_landscape = width >= height
    ending_file = ENDING_16x9 if is_landscape else ENDING_9x16

    scroll_start = OPENING_SEC
    scroll_end = max(scroll_start + 1.0, duration - ENDING_SEC)

    y_ratio = Y_BOTTOM if is_landscape else Y_TOP
    y_expr = f"(h*{y_ratio})"

    speed = BASE_SCROLL_SPEED
    x_expr = f"w-(t-{scroll_start})*{speed}"


    fade_dur = 0.6
    alpha_scroll = (
        f"if(lt(t,{scroll_start}),0,"
        f" if(lt(t,{scroll_end - fade_dur}),1,"
        f"  if(lt(t,{scroll_end}),({scroll_end}-t)/{fade_dur},0)"
        f" ))"
    )

    op_fade_in = 0.6
    op_fade_out_start = 3.3
    alpha_open = (
        f"if(lt(t,{op_fade_in}), t/{op_fade_in},"
        f" if(lt(t,{op_fade_out_start}),1,"
        f"  if(lt(t,{OPENING_SEC}), ({OPENING_SEC}-t)/({OPENING_SEC}-{op_fade_out_start}), 0)"
        f" ))"
    )

    # ✅ 콤마는 -vf에서 필터 구분자로도 쓰이므로 반드시 escape
    alpha_open = alpha_open.replace(",", r"\,")
    alpha_scroll = alpha_scroll.replace(",", r"\,")

    season_text = safe_drawtext_text(season_text)
    brand_text = safe_drawtext_text(brand_text)

    # ✅ 중요: max() 안의 콤마도 반드시 escape + 공백 제거
    brand_fs = r"max(36\,w*0.065)"
    season_fs = r"max(20\,w*0.032)"
    scroll_fs = r"max(22\,w*0.03)"

    season_y = "(h*0.40)"
    brand_y = "(h*0.46)"

    fontfile = FONT_REL.replace("\\", "/")

    vf = (
        f"drawtext=fontfile='{fontfile}':"
        f"text='{season_text}':"
        f"fontsize={season_fs}:"
        f"fontcolor={SEASON_COLOR}@1"
        f":borderw={SEASON_BORDER_W}:"
        f"bordercolor={BRAND_BORDER_COLOR}:"
        f"x=(w-text_w)/2:"
        f"y={season_y}:"
        f"alpha={alpha_open}:"
        f"box=0"
        f","
        f"drawtext=fontfile='{fontfile}':"
        f"text='{brand_text}':"
        f"fontsize={brand_fs}:"
        f"fontcolor={BRAND_COLOR}@1"
        f":borderw={BRAND_BORDER_W}:"
        f"bordercolor={BRAND_BORDER_COLOR}:"
        f"x=(w-text_w)/2:"
        f"y={brand_y}:"
        f"alpha={alpha_open}:"
        f"box=0"
        f","
        f"drawtext=fontfile='{fontfile}':"
        f"textfile='{scroll_textfile_rel}':"
        f"reload=0:"
        f"fontsize={scroll_fs}:"
        f"fontcolor={SCROLL_COLOR}"
        f":borderw={SCROLL_BORDER_W}:"
        f"bordercolor={SCROLL_BORDER_COLOR}:"
        f"x={x_expr}:"
        f"y={y_expr}:"
        f"alpha={alpha_scroll}:"
        f"box=0"
    )

    return vf, ending_file


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 필수 파일 체크
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"엑셀 없음: {EXCEL_PATH}")
    if not os.path.exists(FONT_ABS):
        raise FileNotFoundError(f"폰트 없음: {FONT_ABS}")
    if not os.path.exists(ENDING_16x9):
        raise FileNotFoundError(f"엔딩 없음: {ENDING_16x9}")
    if not os.path.exists(ENDING_9x16):
        raise FileNotFoundError(f"엔딩 없음: {ENDING_9x16}")

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
        base_name = os.path.splitext(filename)[0]

        # ✅ 스크롤 텍스트를 txt로 저장 (UTF-8)
        scroll_txt_abs = os.path.join(OUTPUT_DIR, f"__scroll__{base_name}.txt")
        with open(scroll_txt_abs, "w", encoding="utf-8", newline="\n") as f:
            base = scroll_text.replace("\r", "").replace("\n", " ").strip()
            sep = "   •   "
            long_text = (base + sep) * 60   # 60번 정도 반복 (영상 길어도 충분)
            f.write(long_text)

        scroll_txt_rel = relpath_for_ffmpeg(scroll_txt_abs)

        vf, ending_file = build_filter(width, height, duration, season, brand, scroll_txt_rel)

        # 1) 자막 입힌 임시 파일
        temp_main = os.path.join(OUTPUT_DIR, f"__temp__{base_name}.mp4")
        cmd1 = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "192k",
            temp_main
        ]
        run(cmd1)

        # 2) 엔딩 붙이기
        final_out = os.path.join(OUTPUT_DIR, f"{base_name}_out.mp4")
        concat_list = os.path.join(OUTPUT_DIR, "__concat__.txt")

        with open(concat_list, "w", encoding="utf-8", newline="\n") as f:
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

        # 임시 파일 정리
        try:
            os.remove(temp_main)
            os.remove(concat_list)
            os.remove(scroll_txt_abs)
        except Exception:
            pass

        print(f"[DONE] {final_out}")


if __name__ == "__main__":
    main()
