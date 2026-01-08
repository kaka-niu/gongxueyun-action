import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ======================
# 根目录 & config 路径
# ======================
if getattr(sys, 'frozen', False):
    # 打包 exe 后
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # 源码运行
    BASE_DIR = Path(__file__).resolve().parent.parent

USER_DIR = BASE_DIR
USER_DIR.mkdir(parents=True, exist_ok=True)  # 不存在则自动创建

CONFIG_PATH = USER_DIR / "config.json"


class ConfigManager:
    """
    管理配置：
    - 从文件加载到缓存
    - 从环境变量读取配置（优先级更高）
    - 提供 get/set 方法访问任意字段
    - 更新缓存并写回文件
    """
    _config_cache: dict | None = None

    @classmethod
    def _load_from_file(cls) -> Optional[dict]:
        if not CONFIG_PATH.exists():
            logger.warning(f"config.json 不存在: {CONFIG_PATH.resolve()}")
            return None
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("config")  # 外层 key
        except Exception as e:
            logger.error(f"读取 config.json 失败: {e}")
            return None

    @classmethod
    def load(cls) -> Optional[dict]:
        """获取缓存中的 config，如果没有缓存则从文件加载"""
        if cls._config_cache is not None:
            return cls._config_cache
        cls._config_cache = cls._load_from_file()
        return cls._config_cache

    @classmethod
    def get(cls, *keys: str, default: Any = None) -> Any:
        """
        通用访问方法，支持嵌套 key
        优先从环境变量读取，其次从配置文件读取
        """
        # 1. 尝试从环境变量读取（优先级最高）
        env_key = "_".join([key.upper() for key in keys])
        env_value = os.getenv(f"GX_{env_key}")
        
        if env_value is not None and env_value != "":
            logger.debug(f"从环境变量 GX_{env_key} 读取配置: {env_value}")
            # 根据配置类型进行适当转换
            if keys[-1] in ["latitude", "longitude"]:
                try:
                    return float(env_value)
                except ValueError:
                    pass
            elif keys[-1] in ["port", "float"]:
                try:
                    return int(env_value)
                except ValueError:
                    pass
            elif keys[-1] == "enable":
                return env_value.lower() == "true"
            elif keys[-1] == "customDays":
                if env_value:
                    return [int(day) for day in env_value.split(",")]
            return env_value
        
        # 2. 从配置文件读取
        config_data = cls.load()
        if not config_data:
            if keys[0] == "smtp":
                logger.debug(f"未找到SMTP配置，使用默认值: {default}")
            return default
        
        data = config_data
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                if keys[0] == "smtp":
                    logger.debug(f"未找到SMTP配置项 {'.'.join(keys)}，使用默认值: {default}")
                return default
        
        if keys[0] == "smtp":
            logger.debug(f"从配置文件读取SMTP配置项 {'.'.join(keys)}: {data}")
        return data

    @classmethod
    def set(cls, keys: list[str], value: Any):
        """更新指定字段的值并写回文件"""
        config_data = cls.load() or {}
        data = config_data
        for key in keys[:-1]:
            if key not in data or not isinstance(data[key], dict):
                data[key] = {}
            data = data[key]
        data[keys[-1]] = value
        cls._config_cache = config_data
        cls._write_back()

    @classmethod
    def _write_back(cls):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({"config": cls._config_cache}, f, ensure_ascii=False, indent=4)
            logger.info(f"config.json 已更新: {CONFIG_PATH.resolve()}")
        except Exception as e:
            logger.error(f"写入 config.json 失败: {e}")