"""工序视频处理：ffprobe 取时长 + ffmpeg 按时间区间切片。

视频分析路：用户上传视频 → 在播放器上手动打点切分 → 每段=一道工序（段时长→SAM）。
本模块只做两件无状态的事：探测时长、切出片段。所有外部命令参数都来自受控数值/
经校验的路径，不拼接用户原始字符串。
"""
import json
import shutil
import subprocess
from pathlib import Path

ALLOWED_EXT = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}


class VideoError(RuntimeError):
    """ffmpeg/ffprobe 调用失败或视频不可读。"""


def _bin(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise VideoError(f"未找到 {name}，请确认已安装 ffmpeg 并在 PATH 中")
    return path


def probe_duration(video_path: Path) -> float:
    """返回视频时长(秒)。失败抛 VideoError。"""
    cmd = [
        _bin("ffprobe"), "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(video_path),
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as e:
        raise VideoError("ffprobe 探测超时") from e
    if out.returncode != 0:
        raise VideoError(f"ffprobe 失败: {out.stderr.strip()[:200]}")
    try:
        dur = float(json.loads(out.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        raise VideoError("无法解析视频时长") from e
    return round(dur, 3)


def clip_segment(src: Path, dst: Path, start: float, end: float) -> None:
    """从 src 截取 [start, end) 区间到 dst。优先流复制，失败回退重编码。"""
    if end <= start:
        raise VideoError("结束时间必须大于开始时间")
    duration = end - start
    dst.parent.mkdir(parents=True, exist_ok=True)

    base = [_bin("ffmpeg"), "-y", "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{duration:.3f}"]
    copy_cmd = base + ["-c", "copy", "-avoid_negative_ts", "make_zero", str(dst)]
    try:
        out = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=120)
        if out.returncode == 0 and dst.exists() and dst.stat().st_size > 0:
            return
        # 流复制在非关键帧切点可能产出空/坏片段，回退重编码
        reencode = base + ["-c:v", "libx264", "-c:a", "aac", "-preset", "veryfast", str(dst)]
        out2 = subprocess.run(reencode, capture_output=True, text=True, timeout=300)
        if out2.returncode != 0:
            raise VideoError(f"ffmpeg 切片失败: {out2.stderr.strip()[:200]}")
    except subprocess.TimeoutExpired as e:
        raise VideoError("ffmpeg 切片超时") from e
