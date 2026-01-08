import logging
from datetime import datetime

from manager.ConfigManager import ConfigManager
from manager.UserInfoManager import UserInfoManager
from util.ApiService import ApiService
from util.HelperFunctions import get_checkin_type, desensitize_name, FORCED_CHECKIN_TYPE, check_attendance_status

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
    checkin_list = api_client.get_checkin_info()
    
    # 检查打卡状态
    attendance_status = check_attendance_status(checkin_list, current_time)
    has_start = attendance_status["has_start"]
    has_end = attendance_status["has_end"]
    
    # 检查是否已经打过相同类型的卡
    if (checkin_type == "START" and has_start) or (checkin_type == "END" and has_end):
        log = f"今日[{display_type}]卡已打，无需重复打卡"
        logger.info(log)
        return {"title": "工学云签到任务通知", "content": log}
    
    # 设置打卡信息
    last_checkin_info = checkin_list[0] if checkin_list else {}
    
    # 如果是下班打卡，检查是否已经打过上班卡
    if checkin_type == "END":
        if not has_start:
            # 如果是手动执行END打卡，且未打上班卡，则提示错误
            if FORCED_CHECKIN_TYPE is not None and FORCED_CHECKIN_TYPE == "END":
                log = "今日未打上班卡，无法执行下班打卡"
                logger.info(log)
                return {"title": "工学云签到任务通知", "content": log}
            else:
                # 非手动模式下，如果未打上班卡，则先打上班卡
                logger.info("今日未打上班卡，先执行上班打卡")
                
                # 临时设置强制打卡类型为START
                original_forced_type = FORCED_CHECKIN_TYPE
                FORCED_CHECKIN_TYPE = "START"
                
                # 重新获取打卡类型
                temp_checkin = get_checkin_type()
                temp_checkin_type = temp_checkin.get("type")
                temp_display_type = temp_checkin.get("display")
                
                # 执行上班打卡
                temp_checkin_data = {
                    "type": temp_checkin_type,
                    "lastDetailAddress": last_checkin_info.get("address") if last_checkin_info else None,
                    "attachments": None,
                    "description": "",
                }

                temp_success = api_client.submit_clock_in(temp_checkin_data)
                
                # 恢复原始强制打卡类型
                FORCED_CHECKIN_TYPE = original_forced_type
                
                if temp_success.get("result"):
                    logger.info("上班卡补打成功")
                    # 更新has_start状态
                    has_start = True
                else:
                    logger.warning(f"上班卡补打失败：{temp_success.get('data')}")
                    # 即使上班卡补打失败，也继续尝试下班打卡

    user_name = desensitize_name(UserInfoManager.get("nikeName"))
    logger.info(f"用户 {user_name} 开始 {display_type} 打卡")

    # 设置打卡信息
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