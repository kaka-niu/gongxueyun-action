import logging
from datetime import datetime

from manager.ConfigManager import ConfigManager
from manager.UserInfoManager import UserInfoManager
from util.ApiService import ApiService
from util.HelperFunctions import get_checkin_type, desensitize_name, FORCED_CHECKIN_TYPE

logger = logging.getLogger(__name__)

FORCED_CHECKIN_TYPE = FORCED_CHECKIN_TYPE

def desensitize_phone(phone: str) -> str:
    """
    对手机号进行脱敏处理，保留前3位和后4位，中间用*代替。
    
    Args:
        phone (str): 待脱敏的手机号。
        
    Returns:
        str: 脱敏后的手机号。
    """
    if len(phone) >= 11:
        return f"{phone[:3]}****{phone[-4:]}"
    elif len(phone) >= 7:
        return f"{phone[:3]}***{phone[-3:]}"
    else:
        return "***"  # 对于过短的手机号，返回全隐藏

def clock_in() -> dict[str, str]:
    logging.info("执行签到打卡")

    current_time = datetime.now()

    # 获取打卡类型
    checkin = get_checkin_type()
    checkin_type = checkin.get("type")
    display_type = checkin.get("display")

    # 调用API服务
    api_client = ApiService()
    # 获取打卡信息
    checkin_info = api_client.get_checkin_info()
    
    # 将打卡信息转换为列表格式，以便后续处理
    checkin_list = [checkin_info] if checkin_info else []
    
    # 检查是否已经打过相同类型的卡
    if checkin_list:
        for info in checkin_list:
            if info.get("type") == checkin_type:
                checkin_time = datetime.strptime(
                    info["createTime"], "%Y-%m-%d %H:%M:%S")
                if checkin_time.date() == current_time.date():
                    log = f"今日[{display_type}]卡已打，无需重复打卡"
                    logger.info(log)
                    return {"title": "工学云签到任务通知", "content": log}
    
    # 如果是下班打卡，检查是否已经打过上班卡
    if checkin_type == "END":
        has_start_checkin = False
        if checkin_list:
            for info in checkin_list:
                if info.get("type") == "START":
                    checkin_time = datetime.strptime(
                        info["createTime"], "%Y-%m-%d %H:%M:%S")
                    if checkin_time.date() == current_time.date():
                        has_start_checkin = True
                        break
        
        if not has_start_checkin:
            # 未打上班卡，忽略检查，继续执行下班卡打卡
            logger.info("今日未打上班卡，继续执行下班卡打卡")

    user_name = desensitize_name(UserInfoManager.get("nikeName"))
    logger.info(f"用户 {user_name} 开始 {display_type} 打卡")

    # 设置打卡信息
    last_checkin_info = checkin_list[0] if checkin_list else {}
    checkin_data = {
        "type": checkin_type,
        "lastDetailAddress": last_checkin_info.get("address"),
        "attachments": None,
        "description": "",
    }

    success = api_client.submit_clock_in(checkin_data)
    # success = {"result": True, "data": "打卡成功"}

    # 记录获取结果
    if success.get("result"):
        logger.info("打卡成功")
        # 使用脱敏后的手机号
        desensitized_phone = desensitize_phone(ConfigManager.get('user', 'phone'))
        content = f"签到账号：{desensitized_phone}\n签到类型：{display_type}\n签到地点：{ConfigManager.get('clockIn', 'location', 'address')}"
        return {"title": "工学云签到成功通知", "content": content}
    else:
        logger.warning(f"打卡失败：{success.get('data')}")
        return {"title": "fail", "content": success.get("data")}