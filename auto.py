import json
import os
import logging
import sys
from datetime import datetime

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

def safe_get_env_var(var_name, default_value=""):
    """安全获取环境变量，带有错误处理和日志记录"""
    try:
        value = os.getenv(var_name, default_value)
        if value is None or value == "":
            if var_name in ["GX_USER_PHONE", "GX_USER_PASSWORD", "GX_USER_PHONES", "GX_USER_PASSWORDS"]:
                logging.error(f"关键环境变量 {var_name} 未设置或为空")
                logging.error(f"请在GitHub仓库的Settings > Secrets and variables > Actions中添加 {var_name}")
            else:
                logging.warning(f"环境变量 {var_name} 未设置，使用默认值: {default_value}")
            return default_value
        return value
    except Exception as e:
        logging.error(f"获取环境变量 {var_name} 时出错: {str(e)}")
        return default_value

def create_config_from_env():
    """从环境变量创建配置文件"""
    try:
        # 获取用户配置列表
        user_phones_str = safe_get_env_var("GX_USER_PHONES")
        user_passwords_str = safe_get_env_var("GX_USER_PASSWORDS")
        
        # 获取单用户配置
        user_phone = safe_get_env_var("GX_USER_PHONE")
        user_password = safe_get_env_var("GX_USER_PASSWORD")
        
        # 验证环境变量
        user_phones = user_phones_str.split(",") if user_phones_str else []
        user_passwords = user_passwords_str.split(",") if user_passwords_str else []
        
        # 检查是否有多用户配置
        has_multi_user = user_phones and user_passwords and len(user_phones) == len(user_passwords)
        
        # 检查是否有单用户配置
        has_single_user = user_phone and user_password
        
        # 如果既没有多用户配置也没有单用户配置，则报错
        if not has_multi_user and not has_single_user:
            logging.error("未找到有效的用户配置")
            logging.error("请设置以下环境变量之一：")
            logging.error("1. 多用户配置：GX_USER_PHONES 和 GX_USER_PASSWORDS")
            logging.error("2. 单用户配置：GX_USER_PHONE 和 GX_USER_PASSWORD")
            logging.error("请在GitHub仓库的Settings > Secrets and variables > Actions中添加这些环境变量")
            raise ValueError("未找到有效的用户配置")
        
        # 如果没有提供多用户配置，则使用单个用户配置
        if not has_multi_user:
            # 单用户配置
            config = {
                "config": {
                    "user": {
                        "phone": user_phone,
                        "password": user_password
                    },
                    "clockIn": {
                        "mode": safe_get_env_var("GX_CLOCKIN_MODE", "everyday"),
                        "location": {
                            "address": safe_get_env_var("GX_LOCATION_ADDRESS"),
                            "latitude": safe_get_env_var("GX_LOCATION_LATITUDE"),
                            "longitude": safe_get_env_var("GX_LOCATION_LONGITUDE"),
                            "province": safe_get_env_var("GX_LOCATION_PROVINCE"),
                            "city": safe_get_env_var("GX_LOCATION_CITY"),
                            "area": safe_get_env_var("GX_LOCATION_AREA")
                        },
                        "holidaysClockIn": safe_get_env_var("GX_HOLIDAYS_CLOCKIN", "false").lower() == "true",
                        "customDays": [int(day) for day in safe_get_env_var("GX_CUSTOM_DAYS", "1,2,3,4,5").split(",")] if safe_get_env_var("GX_CUSTOM_DAYS") else [],
                        "time": {
                            "start": safe_get_env_var("GX_TIME_START", "8:30"),
                            "end": safe_get_env_var("GX_TIME_END", "18:00"),
                            "float": int(safe_get_env_var("GX_TIME_FLOAT", "1"))
                        }
                    },
                    "smtp": {
                        "enable": safe_get_env_var("GX_SMTP_ENABLE", "false").lower() == "true",
                        "host": safe_get_env_var("GX_SMTP_HOST"),
                        "port": int(safe_get_env_var("GX_SMTP_PORT", "465")),
                        "username": safe_get_env_var("GX_SMTP_USERNAME"),
                        "password": safe_get_env_var("GX_SMTP_PASSWORD"),
                        "from": safe_get_env_var("GX_SMTP_FROM", "gongxueyun"),
                        "to": safe_get_env_var("GX_SMTP_TO", "").split(",") if safe_get_env_var("GX_SMTP_TO") else []
                    },
                    "device": safe_get_env_var("GX_DEVICE_INFO", "{brand: iOOZ9 Turbo, systemVersion: 15, Platform: Android, isPhysicalDevice: true, incremental: V2352A}")
                }
            }
        else:
            # 多用户配置
            configs = []
            for i, (phone, password) in enumerate(zip(user_phones, user_passwords)):
                config = {
                    "config": {
                        "user": {
                            "phone": phone.strip(),
                            "password": password.strip()
                        },
                        "clockIn": {
                            "mode": safe_get_env_var("GX_CLOCKIN_MODE", "everyday"),
                            "location": {
                                "address": safe_get_env_var("GX_LOCATION_ADDRESS"),
                                "latitude": safe_get_env_var("GX_LOCATION_LATITUDE"),
                                "longitude": safe_get_env_var("GX_LOCATION_LONGITUDE"),
                                "province": safe_get_env_var("GX_LOCATION_PROVINCE"),
                                "city": safe_get_env_var("GX_LOCATION_CITY"),
                                "area": safe_get_env_var("GX_LOCATION_AREA")
                            },
                            "holidaysClockIn": safe_get_env_var("GX_HOLIDAYS_CLOCKIN", "false").lower() == "true",
                            "customDays": [int(day) for day in safe_get_env_var("GX_CUSTOM_DAYS", "1,2,3,4,5").split(",")] if safe_get_env_var("GX_CUSTOM_DAYS") else [],
                            "time": {
                                "start": safe_get_env_var("GX_TIME_START", "8:30"),
                                "end": safe_get_env_var("GX_TIME_END", "18:00"),
                                "float": int(safe_get_env_var("GX_TIME_FLOAT", "1"))
                            }
                        },
                        "smtp": {
                            "enable": safe_get_env_var("GX_SMTP_ENABLE", "false").lower() == "true",
                            "host": safe_get_env_var("GX_SMTP_HOST"),
                            "port": int(safe_get_env_var("GX_SMTP_PORT", "465")),
                            "username": safe_get_env_var("GX_SMTP_USERNAME"),
                            "password": safe_get_env_var("GX_SMTP_PASSWORD"),
                            "from": safe_get_env_var("GX_SMTP_FROM", "gongxueyun"),
                            "to": safe_get_env_var("GX_SMTP_TO", "").split(",") if safe_get_env_var("GX_SMTP_TO") else []
                        },
                        "device": safe_get_env_var("GX_DEVICE_INFO", "{brand: iOOZ9 Turbo, systemVersion: 15, Platform: Android, isPhysicalDevice: true, incremental: V2352A}")
                    }
                }
                configs.append(config)
            
            # 将多个配置组合成一个列表
            config = configs
        
        # 保存配置到文件
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        logging.info("配置文件已从环境变量生成")
    except Exception as e:
        logging.error(f"创建配置文件时出错: {str(e)}")
        raise

def execute_checkin(checkin_type, user_index=None):
    """执行指定类型的打卡"""
    try:
        if user_index is not None:
            logging.info(f"开始执行用户{user_index+1}的{checkin_type}打卡")
        else:
            logging.info(f"开始执行{checkin_type}打卡")
        
        # 登录
        isLogin = login()
        if not isLogin:
            logging.warning("登录失败")
            return False
        
        # 脱敏处理用户数据
        user_data = UserInfoManager.load()
        if user_data and 'phone' in user_data:
            phone = user_data['phone']
            user_data['phone'] = phone[:3] + '*' * (len(phone) - 7) + phone[-4:] if len(phone) > 7 else '*' * len(phone)
        
        logging.info(f"用户数据：{user_data}")
        logging.info(f"用户类型：{UserInfoManager.get('roleKey')}")
        if UserInfoManager.get("userType") != "student":
            logging.warning("当前用户不是学生，跳过打卡任务")
            return False
        
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
    except Exception as e:
        logging.error(f"执行打卡过程中出现错误: {str(e)}")
        return False

def execute_multi_user_checkin(checkin_type):
    """执行多用户打卡"""
    try:
        # 加载配置文件
        with open("config.json", "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        # 检查是否为多用户配置
        if isinstance(config_data, list):
            # 多用户配置
            success_count = 0
            for i, user_config in enumerate(config_data):
                # 保存当前用户配置到临时文件
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump(user_config, f, ensure_ascii=False, indent=4)
                
                # 执行打卡
                if execute_checkin(checkin_type, i):
                    success_count += 1
                
                # 重置UserInfoManager缓存
                UserInfoManager._userInfo_cache = None
            
            logging.info(f"多用户打卡完成，成功打卡{success_count}/{len(config_data)}个用户")
            return success_count > 0
        else:
            # 单用户配置
            return execute_checkin(checkin_type)
    except Exception as e:
        logging.error(f"执行多用户打卡过程中出现错误: {str(e)}")
        return False

if __name__ == "__main__":
    try:
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
        
        execute_multi_user_checkin(checkin_type)
    except Exception as e:
        logging.error(f"程序执行过程中出现错误: {str(e)}")
        sys.exit(1)