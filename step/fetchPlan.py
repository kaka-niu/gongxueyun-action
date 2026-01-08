import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from manager.PlanInfoManager import PlanInfoManager
from util.ApiService import ApiService

logger = logging.getLogger(__name__)

# 获取项目根目录
if getattr(sys, 'frozen', False):
    # 打包 exe 后
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # 源码运行
    BASE_DIR = Path(__file__).resolve().parent.parent

# 计划信息文件路径
PLAN_INFO_FILE = BASE_DIR / "user" / "planInfo.json"
# 计划信息缓存时间（小时）
PLAN_CACHE_HOURS = 24

def is_plan_info_expired() -> bool:
    """检查计划信息是否过期"""
    if not PLAN_INFO_FILE.exists():
        return True
    
    # 获取文件修改时间
    file_mtime = datetime.fromtimestamp(PLAN_INFO_FILE.stat().st_mtime)
    # 如果文件修改时间超过缓存时间，则认为过期
    return datetime.now() - file_mtime > timedelta(hours=PLAN_CACHE_HOURS)

def fetch_plan(*args, **kwargs) -> bool:
    """
    获取打卡计划信息

    Args:
        *args: 兼容旧版本调用方式
        force_refresh (bool): 是否强制刷新计划信息，默认为False

    Returns:
        bool: 获取成功返回True，获取失败返回False
    """
    # 兼容旧版本调用方式，如果args不为空，则忽略kwargs
    force_refresh = kwargs.get('force_refresh', False)
    if args:
        # 如果args不为空，说明是旧版本调用方式，强制刷新
        force_refresh = True
    
    logging.info("检查打卡信息")

    # 检查本地是否已存在打卡计划信息
    planId = PlanInfoManager.get_plan_id()
    plan_expired = is_plan_info_expired()
    
    if planId and not force_refresh and not plan_expired:
        logger.info("检测到本地已有打卡信息且未过期，跳过获取打卡信息")
        return True
    
    if plan_expired:
        logger.info("检测到本地打卡信息已过期，需要重新获取")
    elif force_refresh:
        logger.info("强制刷新打卡信息")
    else:
        logger.info("未检测到打卡信息，开始执行获取打卡信息")

    # 调用API服务获取打卡计划信息
    api_client = ApiService()
    success = api_client.fetch_plan()

    # 记录获取结果
    if success:
        logger.info("打卡信息获取成功")
    else:
        logger.warning("打卡信息获取失败")

    return success
