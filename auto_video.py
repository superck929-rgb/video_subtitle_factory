import os
import sys
import shutil
import subprocess
import pandas as pd
import json

def get_base_dir() -> str:
    # exe로 실행하면 sys.executable이 RUN.exe 경로
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # py로 실행하면 현재 파일 폴더
    return os.path.dirname(os.path.abspath(__file__))

PROJECT_DIR = get_base_dir()

VIDEOS_DIR = os.path.join(PROJECT_DIR, "videos")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
ENDING_DIR = os.path.join(PROJECT_DIR, "ending")
FONTS_DIR = os.path.join(PROJECT_DIR, "fonts")
TOOLS_DIR = os.path.join(PROJECT_DIR, "tools")

EXCEL_PATH = os.path.join(PROJECT_DIR, "brand.xlsx")

def resolve_ffmpeg(tool_name: str) -> str:
    """
    1) tools 폴더에 있으면 그걸 사용
    2) 없으면 PATH에서 검색
    3) 둘 다 없으면 에러
    """
    local_path = os.path.join(TOOLS_DIR, f"{tool_name}.exe")
    if os.path.exists(local_path):
        print(f"[INFO] Using local {tool_name}: {local_path}")
        return local_path

    path_exec = shutil.which(tool_name)
    if path_exec:
        print(f"[INFO] Using PATH {tool_name}: {path_exec}")
        return path_exec

    raise FileNotFoundError(
        f"{tool_name}를 찾을 수 없습니다. tools 폴더에도 없고 시스템 PATH에도 없습니다."
    )

FFMPEG_EXE = resolve_ffmpeg("ffmpeg")
FFPROBE_EXE = resolve_ffmpeg("ffprobe")

FONT_CJK_CANDIDATES = [
    "fonts/SourceHanSansTC-Bold.otf",
    "fonts/SourceHanSansTC-Regular.otf",
    "fonts/NotoSansTC-Bold.ttf",
    "fonts/NotoSansTC-Regular.ttf",
    "fonts/NotoSansTC-Bold.otf",
    "fonts/NotoSansTC-Regular.otf",
]
FONT_FALLBACK = "fonts/Pretendard-Bold.ttf"

ENDING_16x9 = os.path.join(ENDING_DIR, "ending_16x9_3s.mp4")
ENDING_9x16 = os.path.join(ENDING_DIR, "ending_9x16_3s.mp4")

OPENING_SEC = 4.0
ENDING_SEC = 3.0

FADE_DUR = 0.8

BASE_SCROLL_SPEED = 220

Y_TOP = 0.06
Y_BOTTOM = 0.88

SCROLL_COLOR = "white@0.92"
SCROLL_BORDER_W = 3
SCROLL_BORDER_COLOR = "black@1"

SEASON_COLOR = "yellow"
SEASON_BORDER_W = 6
BRAND_COLOR = "white"
BRAND_BORDER_W = 10
BRAND_BORDER_COLOR = "black@1"

AUDIO_SR = "48000"
AUDIO_LAYOUT = "stereo"

# ✅ 브랜드 길이 기준 (10자 초과면 축소)
BRAND_LEN_THRESHOLD = 10
BRAND_SCALE_LONG = 2 / 3  # 0.666...

# ✅ 시즌 글자 85%
SEASON_SCALE = 0.85

# ✅ 시즌-브랜드 추가 간격(픽셀)
EXTRA_GAP_PX = 15

# ✅ 16:9 위치 더 위로(추가 40px)
LANDSCAPE_SHIFT_UP_MORE_PX = 40

# ✅ 9:16 스크롤만 5px 위로
PORTRAIT_SCROLL_UP_PX = 5

# ✅ 9:16에서 "영문 5글자 이하" 브랜드는 +40% 확대
PORTRAIT_SHORT_EN_LEN = 5
PORTRAIT_SHORT_EN_SCALE = 1.4


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
        FFPROBE_EXE, "-v", "error",
        "-show_entries", "format=duration",
        "-show_entries", "stream=index,codec_type,width,height",
        "-of", "json",
        path
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


def get_video_wh(path: str) -> tuple[int, int]:
    info = ffprobe_json(path)
    vstreams = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    if not vstreams:
        raise RuntimeError(f"비디오 스트림 없음: {path}")
    return int(vstreams[0]["width"]), int(vstreams[0]["height"])


def pick_cjk_font_rel() -> str:
    for rel in FONT_CJK_CANDIDATES:
        if os.path.exists(os.path.join(PROJECT_DIR, rel.replace("/", os.sep))):
            return rel.replace("\\", "/")
    return FONT_FALLBACK.replace("\\", "/")


def safe_drawtext_text(s: str) -> str:
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


def relpath_for_ffmpeg(abs_path: str) -> str:
    rel = os.path.relpath(abs_path, PROJECT_DIR)
    return rel.replace("\\", "/")


def esc_commas(expr: str) -> str:
    return expr.replace(",", r"\,")


def is_short_english_brand_for_portrait(brand: str) -> bool:
    """
    9:16에서만 적용할 "영문 5글자 이하" 조건
    - A~Z (공백/숫자/기호 없음)
    - 길이 <= 5
    """
    if not brand:
        return False
    if len(brand) > PORTRAIT_SHORT_EN_LEN:
        return False
    # 영문만 (A-Z)
    return brand.isascii() and brand.isalpha()


def build_vf(width: int, height: int, duration: float,
             season_text: str, brand_text: str,
             scroll_textfile_rel: str) -> str:
    is_landscape = width >= height

    scroll_start = OPENING_SEC
    fade_start = max(0.0, duration - FADE_DUR)

    # ✅ 스크롤 y (9:16만 5px 위로)
    if is_landscape:
        y_expr = f"(h*{Y_BOTTOM})"
    else:
        y_expr = f"(h*{Y_TOP}-{PORTRAIT_SCROLL_UP_PX})"

    speed = BASE_SCROLL_SPEED if is_landscape else int(BASE_SCROLL_SPEED * 0.85)
    x_expr = f"w-(t-{scroll_start})*{speed}"

    alpha_scroll = (
        f"if(lt(t,{scroll_start}),0,"
        f" if(lt(t,{fade_start}),1,"
        f"  if(lt(t,{duration}),({duration}-t)/{FADE_DUR},0)"
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

    alpha_open = esc_commas(alpha_open)
    alpha_scroll = esc_commas(alpha_scroll)

    season_text = safe_drawtext_text(season_text)
    brand_text_safe = safe_drawtext_text(brand_text)

    fontfile = pick_cjk_font_rel()

    if is_landscape:
        # 16:9 (요청대로 변경 없음)
        season_fs_base = r"max(100\,w*0.085)"
        brand_fs_base = r"max(110\,w*0.115)"
        scroll_fs = r"max(38\,w*0.048)"

        season_y = f"(h*0.40-55-30-{LANDSCAPE_SHIFT_UP_MORE_PX})"
        gap_y = r"max(22\,h*0.022)"
    else:
        # 9:16
        season_fs_base = r"max(90\,w*0.115)"
        brand_fs_base = r"max(100\,w*0.135)"
        scroll_fs = r"max(72\,w*0.105)"
        season_y = "(h*0.34)"
        gap_y = r"max(24\,h*0.024)"

    # ✅ 시즌 글자 85%
    season_fs = f"({season_fs_base}*{SEASON_SCALE})"

    # ✅ 브랜드 기본: 10자 초과면 2/3 축소
    if len(brand_text) > BRAND_LEN_THRESHOLD:
        brand_fs = f"({brand_fs_base}*{BRAND_SCALE_LONG})"
    else:
        brand_fs = brand_fs_base

    # ✅ 요청 반영:
    # - 9:16에서만
    # - 브랜드가 "영문 5글자 이하"면 브랜드 글자 +40% 확대
    # - 간격은 brand_y_expr가 season_fs 기준이라 좁아지지 않음
    if (not is_landscape) and is_short_english_brand_for_portrait(brand_text):
        brand_fs = f"({brand_fs}*{PORTRAIT_SHORT_EN_SCALE})"

    # ✅ 간격 유지 (brand text_h 사용 안 함)
    brand_y_expr = f"({season_y}+{season_fs}+{gap_y}+{EXTRA_GAP_PX})"

    vf_parts = [
        f"drawtext=fontfile='{fontfile}':text='{season_text}':fontsize={season_fs}:"
        f"fontcolor={SEASON_COLOR}@1:borderw={SEASON_BORDER_W}:bordercolor={BRAND_BORDER_COLOR}:"
        f"x=(w-text_w)/2:y={season_y}:alpha={alpha_open}:box=0",

        f"drawtext=fontfile='{fontfile}':text='{brand_text_safe}':fontsize={brand_fs}:"
        f"fontcolor={BRAND_COLOR}@1:borderw={BRAND_BORDER_W}:bordercolor={BRAND_BORDER_COLOR}:"
        f"x=(w-text_w)/2:y={brand_y_expr}:alpha={alpha_open}:box=0",

        f"drawtext=fontfile='{fontfile}':textfile='{scroll_textfile_rel}':reload=0:fontsize={scroll_fs}:"
        f"fontcolor={SCROLL_COLOR}:borderw={SCROLL_BORDER_W}:bordercolor={SCROLL_BORDER_COLOR}:"
        f"x={x_expr}:y={y_expr}:alpha={alpha_scroll}:box=0",
    ]

    return ",".join(vf_parts)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"엑셀 없음: {EXCEL_PATH}")
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
        vstreams = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
        if not vstreams:
            print(f"[SKIP] 비디오 스트림 없음: {filename}")
            continue

        width = int(vstreams[0]["width"])
        height = int(vstreams[0]["height"])
        duration = float(info["format"]["duration"])

        is_landscape = width >= height
        ending_file = ENDING_16x9 if is_landscape else ENDING_9x16

        brand = extract_brand_from_filename(filename)
        base_name = os.path.splitext(filename)[0]

        scroll_txt_abs = os.path.join(OUTPUT_DIR, f"__scroll__{base_name}.txt")
        with open(scroll_txt_abs, "w", encoding="utf-8", newline="\n") as f:
            base = scroll_text.replace("\r", "").replace("\n", " ").strip()
            sep = "   •   "
            f.write((base + sep) * 80)

        scroll_txt_rel = relpath_for_ffmpeg(scroll_txt_abs)
        vf = build_vf(width, height, duration, season, brand, scroll_txt_rel)

        fade_start = max(0.0, duration - FADE_DUR)

        temp_main_rel = relpath_for_ffmpeg(os.path.join(OUTPUT_DIR, f"__temp__{base_name}.mp4"))
        input_rel = relpath_for_ffmpeg(input_path)

        cmd1 = [
            FFMPEG_EXE, "-y",
            "-i", input_rel,
            "-vf", f"{vf},fade=t=out:st={fade_start}:d={FADE_DUR}",
            "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
            "-fps_mode", "vfr",
            "-af", f"aresample={AUDIO_SR},aformat=channel_layouts={AUDIO_LAYOUT},afade=t=out:st={fade_start}:d={FADE_DUR}",
            "-c:a", "aac", "-b:a", "192k",
            temp_main_rel
        ]
        run(cmd1)

        final_out_rel = relpath_for_ffmpeg(os.path.join(OUTPUT_DIR, f"{base_name}_out.mp4"))
        ending_rel = relpath_for_ffmpeg(ending_file)

        tw, th = get_video_wh(ending_file)
        vnorm = (
            f"scale={tw}:{th}:force_original_aspect_ratio=decrease,"
            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )

        cmd2 = [
            FFMPEG_EXE, "-y",
            "-i", temp_main_rel,
            "-i", ending_rel,
            "-filter_complex",
            (
                f"[0:v]{vnorm},setpts=PTS-STARTPTS[v0];"
                f"[0:a]aresample={AUDIO_SR},aformat=channel_layouts={AUDIO_LAYOUT},asetpts=PTS-STARTPTS[a0];"
                f"[1:v]{vnorm},trim=duration={ENDING_SEC},setpts=PTS-STARTPTS[v1];"
                f"[1:a]aresample={AUDIO_SR},aformat=channel_layouts={AUDIO_LAYOUT},atrim=duration={ENDING_SEC},asetpts=PTS-STARTPTS[a1];"
                "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
            ),
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
            "-fps_mode", "vfr",
            "-c:a", "aac", "-b:a", "192k",
            final_out_rel
        ]
        run(cmd2)

        try:
            os.remove(os.path.join(PROJECT_DIR, temp_main_rel.replace("/", os.sep)))
            os.remove(scroll_txt_abs)
        except Exception:
            pass

        print(f"[DONE] {os.path.join(OUTPUT_DIR, f'{base_name}_out.mp4')}")


if __name__ == "__main__":
    main()
