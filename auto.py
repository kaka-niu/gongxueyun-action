import json
import os
import logging
import sys
from datetime import datetime

from main import execute_tasks
from manager.ConfigManager import ConfigManager
from step.clockIn import clock_in
from step.fetchPlan import fetch_plan
from step.login import login
from manager.UserInfoManager import UserInfoManager
from step.sendEmail import send_email

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def create_config_from_env():
    """从环境变量创建配置文件"""
    config = {
        "config": {
            "user": {
                "phone": os.getenv("GX_USER_PHONE", ""),
                "password": os.getenv("GX_USER_PASSWORD", "")
            },
            "clockIn": {
                "mode": os.getenv("GX_CLOCKIN_MODE", "everyday"),
                "location": {
                    "address": os.getenv("GX_LOCATION_ADDRESS", ""),
                    "latitude": os.getenv("GX_LOCATION_LATITUDE", ""),
                    "longitude": os.getenv("GX_LOCATION_LONGITUDE", ""),
                    "province": os.getenv("GX_LOCATION_PROVINCE", ""),
                    "city": os.getenv("GX_LOCATION_CITY", ""),
                    "area": os.getenv("GX_LOCATION_AREA", "")
                },
                "holidaysClockIn": os.getenv("GX_HOLIDAYS_CLOCKIN", "false").lower() == "true",
                "customDays": [int(day) for day in os.getenv("GX_CUSTOM_DAYS", "1,2,3,4,5").split(",")] if os.getenv("GX_CUSTOM_DAYS") else [],
                "time": {
                    "start": os.getenv("GX_TIME_START", "8:30"),
                    "end": os.getenv("GX_TIME_END", "18:00"),
                    "float": int(os.getenv("GX_TIME_FLOAT", "1"))
                }
            },
            "smtp": {
                "enable": os.getenv("GX_SMTP_ENABLE", "false").lower() == "true",
                "host": os.getenv("GX_SMTP_HOST", ""),
                "port": int(os.getenv("GX_SMTP_PORT", "465")),
                "username": os.getenv("GX_SMTP_USERNAME", ""),
                "password": os.getenv("GX_SMTP_PASSWORD", ""),
                "from": os.getenv("GX_SMTP_FROM", "gongxueyun"),
                "to": os.getenv("GX_SMTP_TO", "").split(",") if os.getenv("GX_SMTP_TO") else []
            },
            "device": os.getenv("GX_DEVICE_INFO", "{brand: iOOZ9 Turbo, systemVersion: 15, Platform: Android, isPhysicalDevice: true, incremental: V2352A}")
        }
    }
    
    # 保存配置到文件
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    logging.info("配置文件已从环境变量生成")

def execute_checkin(checkin_type):
    """执行指定类型的打卡"""
    logging.info(f"开始执行{checkin_type}打卡")
    
    # 登录
    isLogin = login()
    if not isLogin:
        logging.warning("登录失败")
        return False
    logging.info(f"用户数据：{UserInfoManager.load()}")
    logging.info(f"用户类型：{UserInfoManager.get('roleKey')}")
    if UserInfoManager.get("userType") != "student":
        sys.exit("当前用户不是学生，结束执行打卡任务")
    
    # 获取打卡信息
    hasPlan = fetch_plan()
    if not hasPlan:
        logging.warning("未获取到打卡信息")
        return False
    
    # 强制设置打卡类型
    import step.clockIn
    step.clockIn.FORCED_CHECKIN_TYPE = checkin_type
    
    # 执行打卡
    result = clock_in()
    logging.info(result)
    
    # 发送邮件通知
    if ConfigManager.get("smtp", "enable"):
        try:
            send_email(result["title"], result["content"])
        except Exception as e:
            logging.error(f"邮件发送过程中出现错误: {str(e)}")
            logging.warning("邮件发送失败，但打卡任务已完成")
    
    return True

if __name__ == "__main__":
    # 从环境变量获取配置
    create_config_from_env()
    
    # 从命令行参数获取打卡类型
    if len(sys.argv) < 2:
        logging.error("请指定打卡类型: START 或 END")
        sys.exit(1)
    
    checkin_type = sys.argv[1].upper()
    if checkin_type not in ["START", "END"]:
        logging.error("打卡类型必须是 START 或 END")
        sys.exit(1)
    
    execute_checkin(checkin_type)