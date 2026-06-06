"""
工具：日志、历史记录、缓存清理
"""
import os
import sys
import json
import glob
import time
import shutil
import logging


LOG_DIR = "logs"
HISTORY_DIR = "history"
_logger = None


def _exe_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_logger():
    global _logger
    if _logger is not None:
        return _logger
    log_dir = os.path.join(_exe_dir(), LOG_DIR)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"app_{time.strftime('%Y-%m-%d')}.log")

    _logger = logging.getLogger("char_analyzer")
    _logger.setLevel(logging.INFO)
    _logger.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    _logger.addHandler(fh)
    return _logger


def log_info(msg: str):
    get_logger().info(msg)


def log_error(msg: str):
    get_logger().error(msg)


def log_warning(msg: str):
    get_logger().warning(msg)


def save_history(character_name: str, changes: dict, report: str, overseer: str,
                 front_path: str = "", back_path: str = ""):
    exe_d = _exe_dir()
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"{ts}_{character_name}" if character_name else f"{ts}_unknown"
    folder = os.path.join(exe_d, HISTORY_DIR, folder_name)
    os.makedirs(folder, exist_ok=True)

    # 复制输入文件到历史存档，删除 dropbox 源文件
    input_dir = os.path.join(folder, "input")
    os.makedirs(input_dir, exist_ok=True)
    for src_path, label in [(front_path, "front"), (back_path, "back")]:
        if src_path and os.path.exists(src_path):
            try:
                ext = os.path.splitext(src_path)[1] or ".txt"
                dst = os.path.join(input_dir, f"{label}{ext}")
                shutil.copy2(src_path, dst)
                # 如果在 dropbox 内则删除源文件
                if "\\dropbox\\" in src_path:
                    os.remove(src_path)
            except:
                pass

    with open(os.path.join(folder, "report.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    if overseer:
        with open(os.path.join(folder, "overseer.json"), "w", encoding="utf-8") as f:
            f.write(overseer)

    meta = {
        "character": character_name,
        "time": ts,
        "change_index": changes.get("change_index"),
        "predictability": changes.get("predictability_score"),
        "rationality": changes.get("rationality_score"),
        "change_nature": changes.get("change_nature"),
        "change_direction": changes.get("change_direction"),
        "success": changes.get("success", True),
    }
    with open(os.path.join(folder, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    log_info(f"历史已保存: {folder}")


def list_history() -> list[dict]:
    exe_d = _exe_dir()
    hist_dir = os.path.join(exe_d, HISTORY_DIR)
    if not os.path.isdir(hist_dir):
        return []
    results = []
    for name in sorted(os.listdir(hist_dir), reverse=True):
        meta_path = os.path.join(hist_dir, name, "meta.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["folder"] = name
                results.append(meta)
            except:
                pass
    return results


# ---- 分析日志（实时持久化） ----
_analysis_log_path = None

def start_analysis_log() -> str:
    """创建本次分析的实时日志文件，返回路径"""
    global _analysis_log_path
    exe_d = _exe_dir()
    log_dir = os.path.join(exe_d, LOG_DIR)
    os.makedirs(log_dir, exist_ok=True)
    ts = time.strftime('%Y-%m-%d_%H-%M-%S')
    path = os.path.join(log_dir, f"analysis_{ts}.log")
    _analysis_log_path = path
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"=== 分析日志 {ts} ===\n\n")
    return path

def write_analysis_log(msg: str):
    """追加写入分析日志（强制刷盘，防崩溃丢数据）"""
    global _analysis_log_path
    if not _analysis_log_path:
        return
    try:
        with open(_analysis_log_path, 'a', encoding='utf-8') as f:
            f.write(msg + "\n")
            f.flush()
            os.fsync(f.fileno())
    except:
        pass

def get_analysis_log_path() -> str:
    return _analysis_log_path or ""

def clean_temp_cache(silent: bool = True) -> int:
    if not getattr(sys, 'frozen', False):
        return 0
    temp_dir = os.environ.get('TEMP', '')
    if not temp_dir or not os.path.isdir(temp_dir):
        return 0
    current = getattr(sys, '_MEIPASS', '').lower()
    count = 0
    for folder in glob.glob(os.path.join(temp_dir, '_MEI*')):
        if os.path.isdir(folder) and folder.lower() != current:
            try:
                shutil.rmtree(folder, ignore_errors=True)
                count += 1
            except:
                pass
    if count > 0 and not silent:
        log_info(f"清理旧缓存: {count}个")
    return count
