import logging
import threading
from datetime import datetime, timedelta
import holidays
import requests
from typing import Dict, Any, List

from manager.ConfigManager import ConfigManager
from manager.UserInfoManager import UserInfoManager

# 尝试导入主模块的日志上下文，失败则创建本地版本
try:
    from main import _log_ctx
except ImportError:
    _log_ctx = threading.local()

logger = logging.getLogger(__name__)


# 全局变量，用于强制设置打卡类型
FORCED_CHECKIN_TYPE = None

def get_current_month_info() -> dict:
    """
    获取当前月份的开始和结束时间。

    该方法计算当前月份的开始日期和结束日期，并将它们返回为字典，
    字典中包含这两项的字符串表示。

    Returns:
        包含当前月份开始和结束时间的字典。
    """
    now = datetime.now()
    # 当前月份的第一天
    start_of_month = datetime(now.year, now.month, 1)

    # 下个月的第一天
    if now.month == 12:
        next_month_start = datetime(now.year + 1, 1, 1)
    else:
        next_month_start = datetime(now.year, now.month + 1, 1)

    # 当前月份的最后一天（下个月第一天减一天）
    end_of_month = next_month_start - timedelta(days=1)

    # 格式化为字符串
    start_time_str = start_of_month.strftime("%Y-%m-%d %H:%M:%S")
    end_time_str = end_of_month.strftime("%Y-%m-%d 00:00:00Z")

    return {"startTime": start_time_str, "endTime": end_time_str}


def desensitize_name(name: str) -> str:
    """
    对姓名进行脱敏处理，将中间部分字符替换为星号。

    Args:
        name (str): 待脱敏的姓名。

    Returns:
        str: 脱敏后的姓名。
    """
    name = name.strip()  # 去除前后空格，防止输入有空格影响判断

    n = len(name)
    if n < 3:
        return f"{name[0]}*"
    else:
        return f"{name[0]}{'*' * (n - 2)}{name[-1]}"


def is_workday_realtime() -> bool:
    """
    实时判断今天是否为法定工作日。

    通过调用第三方节假日 API（https://timor.tech/api/holiday）获取当前日期的节假日信息，
    并根据返回结果判断是否为法定工作日。若调用失败或解析异常，则降级使用 weekday 判断。

    返回值:
        bool: True 表示是法定工作日，False 表示是非工作日（周末或节假日）
    """

    check_date = datetime.today()
    date_str = check_date.strftime("%Y-%m-%d")
    url = f"https://timor.tech/api/holiday/info/{date_str}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    # 默认降级结果：weekday < 5 为工作日
    fallback_is_workday = check_date.weekday() < 5

    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code != 200:
            logging.warning(f"API 非 200 状态码: {resp.status_code}, 内容: {resp.text[:200]}")
            return fallback_is_workday

        data = resp.json()
        logging.debug(f"API 返回数据: {data}")

        # Timor API：code == 0 表示请求成功
        if data.get("code") != 0:
            logging.warning(f"API 业务码异常: {data}")
            return fallback_is_workday

        # 解析 type.type 字段以判断日期类型：
        # 0 - 工作日；1 - 周末；2 - 节假日；3 - 调休日（视为工作日）
        day_type = data.get("type", {}).get("type")
        if day_type is None:
            logging.warning(f"返回数据缺少 type.type 字段: {data}")
            return fallback_is_workday

        is_workday = day_type in (0, 3)
        logging.info(f"{date_str} 是否为法定工作日: {is_workday}")

        return is_workday

    except Exception as e:
        logging.error(f"API 调用异常: {e}")
        return fallback_is_workday


def get_checkin_type() -> dict[str, str]:
    """
    获取打卡类型。

    该方法根据配置文件获取打卡类型，并返回一个字典，包含打卡类型和显示名称。
    如果设置了强制打卡类型，则忽略其他逻辑直接返回。

    Returns:
        dict[str, str]: 包含打卡类型和显示名称的字典。
    """
    result = None
    try:
        # 检查是否有强制设置的打卡类型
        global FORCED_CHECKIN_TYPE
        if FORCED_CHECKIN_TYPE is not None:
            # 确保FORCED_CHECKIN_TYPE是有效的打卡类型
            if FORCED_CHECKIN_TYPE in ["START", "END"]:
                checkin_type = FORCED_CHECKIN_TYPE
                display_type = "上班" if checkin_type == "START" else "下班"
                result = {"type": checkin_type, "display": display_type}
                logger.debug(f"使用强制打卡类型: {result}")
                logger.info(f"强制打卡类型返回结果类型: {type(result)}, 值: {result}")
                return result
            else:
                logger.warning(f"无效的强制打卡类型: {FORCED_CHECKIN_TYPE}，忽略强制设置")
        
        current_hour = datetime.now().hour
        
        # 判断是上午还是下午
        is_morning = current_hour < 12
        
        mode = ConfigManager.get("clockIn", "mode")
        logger.info(f"从ConfigManager获取的mode值: {mode}, 类型: {type(mode)}")
        if not isinstance(mode, str):
            logger.warning(f"获取打卡模式失败，返回值类型为: {type(mode)}，值为: {mode}")
            # 默认使用everyday模式
            mode = "everyday"
        
        # 1. 法定工作日模式
        if mode == "weekday":
            # 判断今天是否为工作日
            if is_workday_realtime():
                if is_morning:
                    result = {"type": "START", "display": "上班"}
                else:
                    result = {"type": "END", "display": "下班"}
            else:
                result = {"type": "HOLIDAY", "display": "休息/节假日"}

        # 2. 每天执行
        elif mode == "everyday":
            if is_morning:
                result = {"type": "START", "display": "上班"}
            else:
                result = {"type": "END", "display": "下班"}

        # 3. 自定义模式
        elif mode == "customize":
            custom_days = ConfigManager.get("clockIn", "customDays", default=[])
            today = datetime.today().weekday() + 1  # 1=星期一, 7=星期天
            if today in custom_days:
                if is_morning:
                    result = {"type": "START", "display": "上班"}
                else:
                    result = {"type": "END", "display": "下班"}
            else:
                result = {"type": "HOLIDAY", "display": "休息/节假日"}
        else:
            # 默认返回，防止mode值无效时函数没有返回值
            logger.warning(f"无效的打卡模式: {mode}，默认使用everyday模式")
            if is_morning:
                result = {"type": "START", "display": "上班"}
            else:
                result = {"type": "END", "display": "下班"}
        
        logger.debug(f"打卡类型结果: {result}")
        logger.info(f"正常逻辑返回结果类型: {type(result)}, 值: {result}")
        
        # 确保返回的是字典类型
        if not isinstance(result, dict):
            logger.error(f"get_checkin_type返回值类型不正确，原值: {result}, 类型: {type(result)}")
            current_hour = datetime.now().hour
            is_morning = current_hour < 12
            result = {
                "type": "START" if is_morning else "END", 
                "display": "上班(类型保护)" if is_morning else "下班(类型保护)"
            }
            logger.info(f"类型保护后返回结果: {result}")
        
        return result
    except Exception as e:
        logger.error(f"获取打卡类型时发生异常: {e}")
        import traceback
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        # 发生异常时返回默认值
        current_hour = datetime.now().hour
        is_morning = current_hour < 12
        result = {
            "type": "START" if is_morning else "END", 
            "display": "上班(异常后默认)" if is_morning else "下班(异常后默认)"
        }
        logger.info(f"异常处理返回结果类型: {type(result)}, 值: {result}")
        
        return result


def check_attendance_status(checkin_list: List[Dict[str, Any]], current_date: datetime = None) -> Dict[str, bool]:
    """
    检查打卡状态，确定今天是否已经打了上班卡和下班卡。

    Args:
        checkin_list: 打卡记录列表
        current_date: 当前日期，默认为今天

    Returns:
        dict: 包含 'has_start' 和 'has_end' 的字典，表示是否已打上班卡和下班卡
    """
    if current_date is None:
        current_date = datetime.now()
    
    has_start = False
    has_end = False
    
    if checkin_list:
        for checkin_info in checkin_list:
            if checkin_info.get("type") == "START":
                checkin_time = datetime.strptime(
                    checkin_info["createTime"], "%Y-%m-%d %H:%M:%S")
                if checkin_time.date() == current_date.date():
                    has_start = True
            elif checkin_info.get("type") == "END":
                checkin_time = datetime.strptime(
                    checkin_info["createTime"], "%Y-%m-%d %H:%M:%S")
                if checkin_time.date() == current_date.date():
                    has_end = True
    
    return {"has_start": has_start, "has_end": has_end}