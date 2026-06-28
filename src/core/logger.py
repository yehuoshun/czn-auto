"""
日志模块 - 文件 + 控制台双输出
- 文件始终 DEBUG 全量，控制台按配置级别
- 终端和文件格式、内容完全一致
- 支持日志轮转、启动横幅
"""

import logging
import logging.handlers
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

APP_VERSION = "0.1.0"

# ── 简单格式：时间 + 级别 + 位置 + 消息 ──
LOG_FMT_VERBOSE = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-5s] %(name)s:%(lineno)d %(funcName)s(): %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── 紧凑格式：时间 + 级别 + 消息 ──
LOG_FMT_COMPACT = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-5s] %(message)s",
    datefmt="%H:%M:%S",
)


def setup_logging(
    level: str = "DEBUG",
    log_file: str = "logs/czn-auto.log",
    max_size_mb: int = 50,
    backup_count: int = 5,
    compact: bool = False,
) -> logging.Logger:
    """
    初始化日志系统。

    Args:
        level: 控制台日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_file: 日志文件路径
        max_size_mb: 单文件最大 MB，超出轮转
        backup_count: 保留的历史日志数
        compact: True 用紧凑格式（无模块/行号），False 用详细格式
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    console_level = getattr(logging, level.upper(), logging.DEBUG)
    log_fmt = LOG_FMT_COMPACT if compact else LOG_FMT_VERBOSE

    # 根 logger
    logger = logging.getLogger("czn-auto")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # ── 控制台 ──
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(log_fmt)
    logger.addHandler(console)

    # ── 文件（始终 DEBUG）──
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        mode="a",
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_fmt)
    logger.addHandler(file_handler)

    logger.info(f"日志系统就绪: {log_file} (文件=DEBUG, 控制台={level})")
    return logger


def get_logger(name: str) -> logging.Logger:
    """获取模块 logger (czn-auto.{name})"""
    return logging.getLogger(f"czn-auto.{name}")


def print_startup_banner(logger: logging.Logger, config: dict | None = None) -> None:
    """
    打印启动横幅：版本、环境、配置摘要。
    方便从日志快速定位运行环境和参数。
    """
    logger.info("=" * 60)
    logger.info(f"CZN Auto v{APP_VERSION}  启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python: {sys.version.split()[0]}  |  平台: {sys.platform}")
    logger.info(f"工作目录: {Path.cwd()}")
    logger.info(f"可执行: {sys.executable}")

    # 管理员权限
    try:
        import ctypes
        is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        is_admin = False
    logger.info(f"管理员权限: {'是' if is_admin else '否 (部分操作可能失败)'}")

    # 配置摘要
    if config:
        logger.info(f"配置文件: {json.dumps(config, ensure_ascii=False, indent=None)}")
    logger.info("=" * 60)
