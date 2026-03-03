"""
AgendaX动态日志记录器模块
"""
import inspect
import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import Union

from core.bases.resource_release import ResourceReleasable


class Logger(ResourceReleasable):
    """
    动态日志记录器
    
    输出格式：[LEVEL|@module.path|YYYY-MM-DD HH:MM:SS] (logger_name) message
    
    示例：[INFO|@core.utils.app_thread|2026-02-20 20:58:59] (Task.server) 任务启动
    """
    
    # 终端颜色定义（Windows CMD/PowerShell 支持）
    _COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'       # 重置
    }
    
    file_handler: logging.FileHandler | None = None

    def __init__(self, name: str|None = None, level: int = logging.INFO):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称，如果为 None 则自动获取调用者模块名
            level: 日志级别
        """
        # 如果没有指定名称，自动获取调用者模块名
        if name is None:
            name = self._get_caller_module()
        
        self._name = name
        self._internal_logger = logging.getLogger(name)
        self._internal_logger.setLevel(level)
        for hdlr in self._internal_logger.handlers[:]:
            self._internal_logger.removeHandler(hdlr)

        _create_log_folder()
        file_handler = TimedRotatingFileHandler('./log/app.log', encoding='utf-8', delay=True, backupCount=10, when="midnight")
        file_handler.setLevel(logging.DEBUG)
        file_handler.createLock()
        file_handler.setFormatter(self._DynamicFormatter(False))
        self.addHandler(file_handler)
        self.file_handler = file_handler

        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(self._DynamicFormatter())
        self._internal_logger.addHandler(handler)
        self._internal_logger.propagate = False
        
        self.register_release()
    
    @staticmethod
    def _get_caller_module() -> str:
        """
        获取调用者模块名
        
        返回: 调用者的完整模块路径（如 'core.utils.app_thread'）
        """
        try:
            # 获取当前调用栈
            frame = inspect.currentframe()
            # 跳过 Logger.__init__ 和 _get_caller_module
            for _ in range(3):
                if frame:
                    frame = frame.f_back
            
            # 查找第一个非 logging 相关的模块
            while frame:
                module = inspect.getmodule(frame)
                if module and not module.__name__.endswith('logging'):
                    module_name = module.__name__
                    return module_name
                frame = frame.f_back if frame else None
        except (AttributeError, ValueError, TypeError):
            pass
        
        return 'unknown'
    
    class _DynamicFormatter(logging.Formatter):
        """动态格式化器，使用 Python 内置的 module 信息"""
        
        def __init__(self, useColor: bool|None = None):
            super().__init__()
            self._use_color = sys.stdout.isatty() if useColor is None and not sys.stdout is None else useColor
        
        def format(self, record: logging.LogRecord) -> str:
            """
            格式化日志记录
            
            使用 record.name（记录器名称）作为模块路径
            如果 record.name 是 'root'，则使用 record.module
            """

            module_path = Logger._get_caller_module()
            
            # 时间戳
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 构建日志前缀
            level_name = record.levelname
            prefix = f"[{level_name}|@{module_path}|{timestamp}]"
            
            # 添加颜色
            if self._use_color and level_name in Logger._COLORS:
                prefix = f"{Logger._COLORS[level_name]}{prefix}{Logger._COLORS['RESET']}"
            
            # 记录器名称（如果不同于模块路径）
            logger_name = ''
            if record.name != 'root' and record.name != module_path:
                logger_name = f"({record.name})"
            
            # 构建完整日志行
            log_line = f"{prefix} {logger_name} {record.getMessage()}"
            
            # 添加异常堆栈信息
            if record.exc_info:
                import traceback
                log_line += f"\n{traceback.format_exc().rstrip()}"
            
            return log_line
    
    # ============ 标准 logging API ============
    
    def debug(self, msg: str, *args, **kwargs):
        """记录 DEBUG 级别日志"""
        self._internal_logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """记录 INFO 级别日志"""
        self._internal_logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """记录 WARNING 级别日志"""
        self._internal_logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """记录 ERROR 级别日志"""
        self._internal_logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """记录 CRITICAL 级别日志"""
        self._internal_logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        """记录异常日志（包含堆栈跟踪）"""
        kwargs.setdefault('exc_info', True)
        self._internal_logger.error(msg, *args, **kwargs)
    
    def log(self, level: int, msg: str, *args, **kwargs):
        """通用日志记录方法"""
        self._internal_logger.log(level, msg, *args, **kwargs)
    
    # ============ 兼容属性和方法 ============
    
    @property
    def name(self) -> str:
        """记录器名称"""
        return self._name
    
    @property
    def level(self) -> int:
        """当前日志级别"""
        return self._internal_logger.level
    
    @level.setter
    def level(self, level: int):
        """设置日志级别"""
        self._internal_logger.setLevel(level)
        for handler in self._internal_logger.handlers:
            handler.setLevel(level)
    
    def setLevel(self, level: int):
        """设置日志级别（兼容方法）"""
        self.level = level
    
    def addHandler(self, handler: logging.Handler):
        """添加处理器"""
        self._internal_logger.addHandler(handler)
    
    def removeHandler(self, handler: logging.Handler):
        """移除处理器"""
        self._internal_logger.removeHandler(handler)
    
    def hasHandlers(self) -> bool:
        """检查是否有处理器"""
        return self._internal_logger.hasHandlers()
    
    def isEnabledFor(self, level: int) -> bool:
        """检查是否启用指定级别的日志"""
        return self._internal_logger.isEnabledFor(level)
    
    def getEffectiveLevel(self) -> int:
        """获取有效日志级别"""
        return self._internal_logger.getEffectiveLevel()
    
    def release_resource(self):
        if self.file_handler:
            self.file_handler.close()


# ============ 全局管理器 ============

_logger_cache: dict[str, Logger] = {}

def getLogger(name: str|None = None, level: int = logging.INFO) -> Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称，如果为 None 则自动获取调用者模块名
        level: 日志级别
        
    Returns:
        Logger 实例
    """
    # 如果没有指定名称，自动获取调用者模块名
    if name is None:
        name = Logger._get_caller_module()
    
    if name not in _logger_cache:
        _logger_cache[name] = Logger(name, level)
    return _logger_cache[name]


# ============ 快捷函数（可选） ============

def debug(msg: str, *args, **kwargs):
    """全局 DEBUG 日志"""
    getLogger().debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs):
    """全局 INFO 日志"""
    getLogger().info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs):
    """全局 WARNING 日志"""
    getLogger().warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs):
    """全局 ERROR 日志"""
    getLogger().error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs):
    """全局 CRITICAL 日志"""
    getLogger().critical(msg, *args, **kwargs)

def exception(msg: str, *args, **kwargs):
    """全局异常日志"""
    getLogger().exception(msg, *args, **kwargs)

def log(level: int, msg: str, *args, **kwargs):
    """全局通用日志"""
    getLogger().log(level, msg, *args, **kwargs)

def _create_log_folder() -> None:
    os.makedirs('log', exist_ok=True)

# ============ 配置函数 ============

def set_default_level(level: Union[int, str]):
    """
    设置默认日志级别
    
    Args:
        level: 日志级别或级别名称（'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'）
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    # 更新所有缓存的记录器
    for logger in _logger_cache.values():
        logger.setLevel(level) # type: ignore
    
    # 同时更新 logging 的根记录器
    logging.getLogger().setLevel(level)


def configure(level: Union[int, str] = logging.INFO):
    """
    配置全局日志
    
    Args:
        level: 日志级别
        format_string: 格式化字符串（如果为 None 则使用默认格式）
        datefmt: 日期格式
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    # 配置根记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

# ============ 初始化默认配置 ============

# 导出常用常量
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL