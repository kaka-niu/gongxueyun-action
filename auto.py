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
            if var_name in ["GX_USER_PHONE", "GX_USER_PASSWORD", "GX_USER_PHONES", "GX_USER_PASSWORDS", "GX_USER"]:
                logging.error(f"关键环境变量 {var_name} 未设置或为空")
                logging.error(f"请在GitHub仓库的Settings > Secrets and variables > Actions中添加 {var_name}")
            elif var_name == "SEND":
                logging.error(f"SMTP配置环境变量 {var_name} 未设置或为空")
                logging.error(f"请在GitHub仓库的Settings > Secrets and variables > Actions中添加 {var_name}")
                logging.error(f"SEND环境变量应包含以下格式的JSON:")
                logging.error('{ "smtp": { "enable": true, "host": "smtp.qq.com", "port": 465, "username": "your_email@qq.com", "password": "your_password", "from": "gongxueyun", "to": ["your_email@qq.com"] } }')
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
        # 尝试从GX_USER环境变量获取JSON格式的配置
        user_json_str = safe_get_env_var("GX_USER")
        
        # 尝试从SEND环境变量获取SMTP配置
        logging.info("正在检查SEND环境变量...")
        send_json_str = safe_get_env_var("SEND")
        if send_json_str and send_json_str.strip():
            logging.info(f"SEND环境变量已设置，内容长度: {len(send_json_str)} 字符")
            logging.info(f"SEND环境变量前100个字符: {send_json_str[:100]}")
        else:
            logging.warning("SEND环境变量未设置或为空")
        
        # 解析SMTP配置
        smtp_config = None
        if send_json_str and send_json_str.strip():
            try:
                smtp_config = json.loads(send_json_str)
                logging.info("已从SEND环境变量获取SMTP配置")
                logging.info(f"SMTP配置: {json.dumps(smtp_config, ensure_ascii=False)}")
                
                # 验证必需字段
                if "smtp" not in smtp_config:
                    logging.error("SEND环境变量中缺少smtp字段")
                    raise ValueError("SEND环境变量中缺少smtp字段")
                
                smtp = smtp_config["smtp"]
                required_fields = ["enable", "host", "port", "username", "password", "from", "to"]
                for field in required_fields:
                    if field not in smtp:
                        logging.error(f"SMTP配置中缺少必需字段: {field}")
                        raise ValueError(f"SMTP配置中缺少必需字段: {field}")
                
                logging.info("SMTP配置验证通过")
            except json.JSONDecodeError as e:
                logging.error(f"SEND环境变量JSON格式错误: {str(e)}")
                logging.error(f"SEND环境变量内容: {send_json_str}")
                logging.error("请检查SEND环境变量是否为有效的JSON格式")
                raise ValueError(f"SEND环境变量不是有效的JSON格式: {str(e)}")
            except ValueError as e:
                # 重新抛出我们自己的验证错误
                raise e
            except Exception as e:
                logging.error(f"解析SEND环境变量时出错: {str(e)}")
                raise ValueError(f"解析SEND环境变量时出错: {str(e)}")
        
        # 如果GX_USER环境变量存在，则解析JSON格式的配置
        if user_json_str and user_json_str.strip():
            try:
                # 解析JSON字符串
                user_configs = json.loads(user_json_str)
                
                # 处理两种格式：
                # 1. 完整配置格式：{"config": {...}}
                # 2. 用户配置格式：{"phone": "...", "password": "..."} 或 [{"phone": "...", "password": "..."}, ...]
                
                # 处理三种JSON格式：
                # 1. 完整配置格式：{"config": {...}}
                # 2. 用户配置格式：{"phone": "...", "password": "..."}
                # 3. 多用户配置格式：[{"config": {...}}, {"config": {...}}]
                
                configs = []
                
                # 如果是单个完整配置格式（包含config字段），直接使用
                if isinstance(user_configs, dict) and "config" in user_configs:
                    configs = [user_configs]
                # 如果是单个用户配置（字典格式，不包含config字段），转换为完整配置
                elif isinstance(user_configs, dict):
                    if not isinstance(user_configs, dict):
                        raise ValueError("GX_USER环境变量中的每个用户配置必须是JSON对象")
                    
                    # 验证必需字段
                    if "phone" not in user_configs or "password" not in user_configs:
                        raise ValueError("每个用户配置必须包含phone和password字段")
                    
                    # 创建完整配置
                    config = {
                        "config": {
                            "user": {
                                "phone": user_configs["phone"],
                                "password": user_configs["password"]
                            },
                            "clockIn": {
                                "mode": user_configs.get("mode", safe_get_env_var("GX_CLOCKIN_MODE", "everyday")),
                                "location": {
                                    "address": user_configs.get("address", safe_get_env_var("GX_LOCATION_ADDRESS")),
                                    "latitude": user_configs.get("latitude", safe_get_env_var("GX_LOCATION_LATITUDE")),
                                    "longitude": user_configs.get("longitude", safe_get_env_var("GX_LOCATION_LONGITUDE")),
                                    "province": user_configs.get("province", safe_get_env_var("GX_LOCATION_PROVINCE")),
                                    "city": user_configs.get("city", safe_get_env_var("GX_LOCATION_CITY")),
                                    "area": user_configs.get("area", safe_get_env_var("GX_LOCATION_AREA"))
                                },
                                "holidaysClockIn": user_configs.get("holidaysClockIn", safe_get_env_var("GX_HOLIDAYS_CLOCKIN", "false").lower() == "true"),
                                "customDays": user_configs.get("customDays", [int(day) for day in safe_get_env_var("GX_CUSTOM_DAYS", "1,2,3,4,5").split(",")] if safe_get_env_var("GX_CUSTOM_DAYS") else []),
                                "time": {
                                    "start": user_configs.get("startTime", safe_get_env_var("GX_TIME_START", "8:30")),
                                    "end": user_configs.get("endTime", safe_get_env_var("GX_TIME_END", "18:00")),
                                    "float": user_configs.get("timeFloat", int(safe_get_env_var("GX_TIME_FLOAT", "1")))
                                }
                            },
                            # 如果用户配置中包含smtp字段，直接使用；否则使用SEND环境变量或GX_前缀环境变量
                            "smtp": user_configs.get("smtp", {
                                "enable": smtp_config.get("smtp", {}).get("enable", user_configs.get("smtpEnable", safe_get_env_var("GX_SMTP_ENABLE", "false").lower() == "true")) if smtp_config else user_configs.get("smtpEnable", safe_get_env_var("GX_SMTP_ENABLE", "false").lower() == "true"),
                                "host": smtp_config.get("smtp", {}).get("host", user_configs.get("smtpHost", safe_get_env_var("GX_SMTP_HOST"))) if smtp_config else user_configs.get("smtpHost", safe_get_env_var("GX_SMTP_HOST")),
                                "port": smtp_config.get("smtp", {}).get("port", user_configs.get("smtpPort", int(safe_get_env_var("GX_SMTP_PORT", "465")))) if smtp_config else user_configs.get("smtpPort", int(safe_get_env_var("GX_SMTP_PORT", "465"))),
                                "username": smtp_config.get("smtp", {}).get("username", user_configs.get("smtpUsername", safe_get_env_var("GX_SMTP_USERNAME"))) if smtp_config else user_configs.get("smtpUsername", safe_get_env_var("GX_SMTP_USERNAME")),
                                "password": smtp_config.get("smtp", {}).get("password", user_configs.get("smtpPassword", safe_get_env_var("GX_SMTP_PASSWORD"))) if smtp_config else user_configs.get("smtpPassword", safe_get_env_var("GX_SMTP_PASSWORD")),
                                "from": smtp_config.get("smtp", {}).get("from", user_configs.get("smtpFrom", safe_get_env_var("GX_SMTP_FROM", "gongxueyun"))) if smtp_config else user_configs.get("smtpFrom", safe_get_env_var("GX_SMTP_FROM", "gongxueyun")),
                                "to": smtp_config.get("smtp", {}).get("to", user_configs.get("smtpTo", safe_get_env_var("GX_SMTP_TO", "").split(",") if safe_get_env_var("GX_SMTP_TO") else [])) if smtp_config else user_configs.get("smtpTo", safe_get_env_var("GX_SMTP_TO", "").split(",") if safe_get_env_var("GX_SMTP_TO") else [])
                            }),
                            "device": user_configs.get("device", safe_get_env_var("GX_DEVICE_INFO", "{brand: iOOZ9 Turbo, systemVersion: 15, Platform: Android, isPhysicalDevice: true, incremental: V2352A}"))
                        }
                    }
                    configs = [config]
                # 如果是列表格式，检查每个元素
                elif isinstance(user_configs, list):
                    for item in user_configs:
                        # 如果是完整配置格式（包含config字段），直接使用
                        if isinstance(item, dict) and "config" in item:
                            configs.append(item)
                        # 如果是用户配置格式（不包含config字段），转换为完整配置
                        elif isinstance(item, dict):
                            # 验证必需字段
                            if "phone" not in item or "password" not in item:
                                raise ValueError("每个用户配置必须包含phone和password字段")
                            
                            # 创建完整配置
                            config = {
                                "config": {
                                    "user": {
                                        "phone": item["phone"],
                                        "password": item["password"]
                                    },
                                    "clockIn": {
                                        "mode": item.get("mode", safe_get_env_var("GX_CLOCKIN_MODE", "everyday")),
                                        "location": {
                                            "address": item.get("address", safe_get_env_var("GX_LOCATION_ADDRESS")),
                                            "latitude": item.get("latitude", safe_get_env_var("GX_LOCATION_LATITUDE")),
                                            "longitude": item.get("longitude", safe_get_env_var("GX_LOCATION_LONGITUDE")),
                                            "province": item.get("province", safe_get_env_var("GX_LOCATION_PROVINCE")),
                                            "city": item.get("city", safe_get_env_var("GX_LOCATION_CITY")),
                                            "area": item.get("area", safe_get_env_var("GX_LOCATION_AREA"))
                                        },
                                        "holidaysClockIn": item.get("holidaysClockIn", safe_get_env_var("GX_HOLIDAYS_CLOCKIN", "false").lower() == "true"),
                                        "customDays": item.get("customDays", [int(day) for day in safe_get_env_var("GX_CUSTOM_DAYS", "1,2,3,4,5").split(",")] if safe_get_env_var("GX_CUSTOM_DAYS") else []),
                                        "time": {
                                            "start": item.get("startTime", safe_get_env_var("GX_TIME_START", "8:30")),
                                            "end": item.get("endTime", safe_get_env_var("GX_TIME_END", "18:00")),
                                            "float": item.get("timeFloat", int(safe_get_env_var("GX_TIME_FLOAT", "1")))
                                        }
                                    },
                                    # 如果用户配置中包含smtp字段，直接使用；否则使用SEND环境变量或GX_前缀环境变量
                            "smtp": item.get("smtp", {
                                "enable": smtp_config.get("smtp", {}).get("enable", item.get("smtpEnable", safe_get_env_var("GX_SMTP_ENABLE", "false").lower() == "true")) if smtp_config else item.get("smtpEnable", safe_get_env_var("GX_SMTP_ENABLE", "false").lower() == "true"),
                                "host": smtp_config.get("smtp", {}).get("host", item.get("smtpHost", safe_get_env_var("GX_SMTP_HOST"))) if smtp_config else item.get("smtpHost", safe_get_env_var("GX_SMTP_HOST")),
                                "port": smtp_config.get("smtp", {}).get("port", item.get("smtpPort", int(safe_get_env_var("GX_SMTP_PORT", "465")))) if smtp_config else item.get("smtpPort", int(safe_get_env_var("GX_SMTP_PORT", "465"))),
                                "username": smtp_config.get("smtp", {}).get("username", item.get("smtpUsername", safe_get_env_var("GX_SMTP_USERNAME"))) if smtp_config else item.get("smtpUsername", safe_get_env_var("GX_SMTP_USERNAME")),
                                "password": smtp_config.get("smtp", {}).get("password", item.get("smtpPassword", safe_get_env_var("GX_SMTP_PASSWORD"))) if smtp_config else item.get("smtpPassword", safe_get_env_var("GX_SMTP_PASSWORD")),
                                "from": smtp_config.get("smtp", {}).get("from", item.get("smtpFrom", safe_get_env_var("GX_SMTP_FROM", "gongxueyun"))) if smtp_config else item.get("smtpFrom", safe_get_env_var("GX_SMTP_FROM", "gongxueyun")),
                                "to": smtp_config.get("smtp", {}).get("to", item.get("smtpTo", safe_get_env_var("GX_SMTP_TO", "").split(",") if safe_get_env_var("GX_SMTP_TO") else [])) if smtp_config else item.get("smtpTo", safe_get_env_var("GX_SMTP_TO", "").split(",") if safe_get_env_var("GX_SMTP_TO") else [])
                            }),
                                    "device": item.get("device", safe_get_env_var("GX_DEVICE_INFO", "{brand: iOOZ9 Turbo, systemVersion: 15, Platform: Android, isPhysicalDevice: true, incremental: V2352A}"))
                                }
                            }
                            configs.append(config)
                        else:
                            raise ValueError("GX_USER环境变量中的每个用户配置必须是JSON对象")
                else:
                    raise ValueError("GX_USER环境变量格式不正确，应为JSON对象或JSON对象数组")
                
                # 保存配置到文件
                with open("config.json", "w", encoding="utf-8") as f:
                    # 如果是单个配置，直接保存
                    if len(configs) == 1:
                        json.dump(configs[0], f, ensure_ascii=False, indent=4)
                    # 如果是多个配置，保存为列表
                    else:
                        json.dump(configs, f, ensure_ascii=False, indent=4)
                
                logging.info("配置文件已从GX_USER环境变量生成")
                return
            except json.JSONDecodeError as e:
                logging.error(f"GX_USER环境变量JSON格式错误: {str(e)}")
                raise ValueError(f"GX_USER环境变量不是有效的JSON格式: {str(e)}")
            except Exception as e:
                logging.error(f"处理GX_USER环境变量时出错: {str(e)}")
                raise
        
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
            logging.error("3. JSON格式配置：GX_USER (包含JSON格式的用户信息)")
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
                    # 如果SEND环境变量存在，则使用SEND环境变量中的SMTP配置；否则使用单独的环境变量
                    "smtp": {
                        "enable": smtp_config.get("smtp", {}).get("enable", safe_get_env_var("GX_SMTP_ENABLE", "false").lower() == "true") if smtp_config else safe_get_env_var("GX_SMTP_ENABLE", "false").lower() == "true",
                        "host": smtp_config.get("smtp", {}).get("host", safe_get_env_var("GX_SMTP_HOST")) if smtp_config else safe_get_env_var("GX_SMTP_HOST"),
                        "port": smtp_config.get("smtp", {}).get("port", int(safe_get_env_var("GX_SMTP_PORT", "465"))) if smtp_config else int(safe_get_env_var("GX_SMTP_PORT", "465")),
                        "username": smtp_config.get("smtp", {}).get("username", safe_get_env_var("GX_SMTP_USERNAME")) if smtp_config else safe_get_env_var("GX_SMTP_USERNAME"),
                        "password": smtp_config.get("smtp", {}).get("password", safe_get_env_var("GX_SMTP_PASSWORD")) if smtp_config else safe_get_env_var("GX_SMTP_PASSWORD"),
                        "from": smtp_config.get("smtp", {}).get("from", safe_get_env_var("GX_SMTP_FROM", "gongxueyun")) if smtp_config else safe_get_env_var("GX_SMTP_FROM", "gongxueyun"),
                        "to": smtp_config.get("smtp", {}).get("to", safe_get_env_var("GX_SMTP_TO", "").split(",") if safe_get_env_var("GX_SMTP_TO") else []) if smtp_config else safe_get_env_var("GX_SMTP_TO", "").split(",") if safe_get_env_var("GX_SMTP_TO") else []
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
                        # 如果SEND环境变量存在，则使用SEND环境变量中的SMTP配置；否则使用单独的环境变量
                        "smtp": {
                            "enable": smtp_config.get("smtp", {}).get("enable", safe_get_env_var("GX_SMTP_ENABLE", "false").lower() == "true") if smtp_config else safe_get_env_var("GX_SMTP_ENABLE", "false").lower() == "true",
                            "host": smtp_config.get("smtp", {}).get("host", safe_get_env_var("GX_SMTP_HOST")) if smtp_config else safe_get_env_var("GX_SMTP_HOST"),
                            "port": smtp_config.get("smtp", {}).get("port", int(safe_get_env_var("GX_SMTP_PORT", "465"))) if smtp_config else int(safe_get_env_var("GX_SMTP_PORT", "465")),
                            "username": smtp_config.get("smtp", {}).get("username", safe_get_env_var("GX_SMTP_USERNAME")) if smtp_config else safe_get_env_var("GX_SMTP_USERNAME"),
                            "password": smtp_config.get("smtp", {}).get("password", safe_get_env_var("GX_SMTP_PASSWORD")) if smtp_config else safe_get_env_var("GX_SMTP_PASSWORD"),
                            "from": smtp_config.get("smtp", {}).get("from", safe_get_env_var("GX_SMTP_FROM", "gongxueyun")) if smtp_config else safe_get_env_var("GX_SMTP_FROM", "gongxueyun"),
                            "to": smtp_config.get("smtp", {}).get("to", safe_get_env_var("GX_SMTP_TO", "").split(",") if safe_get_env_var("GX_SMTP_TO") else []) if smtp_config else safe_get_env_var("GX_SMTP_TO", "").split(",") if safe_get_env_var("GX_SMTP_TO") else []
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
        smtp_enabled = ConfigManager.get("smtp", "enable")
        logging.info(f"SMTP邮件通知配置检查 - 启用状态: {smtp_enabled}")
        
        if smtp_enabled:
            try:
                # 检查SMTP配置
                smtp_host = ConfigManager.get("smtp", "host")
                smtp_port = ConfigManager.get("smtp", "port")
                smtp_username = ConfigManager.get("smtp", "username")
                smtp_password = ConfigManager.get("smtp", "password")
                smtp_from = ConfigManager.get("smtp", "from")
                smtp_to = ConfigManager.get("smtp", "to")
                
                logging.info(f"SMTP配置详情:")
                logging.info(f"  服务器: {smtp_host}:{smtp_port}")
                logging.info(f"  用户名: {smtp_username}")
                logging.info(f"  发件人: {smtp_from}")
                logging.info(f"  收件人数量: {len(smtp_to) if smtp_to else 0}")
                logging.info(f"  密码已设置: {'是' if smtp_password else '否'}")
                
                if not all([smtp_host, smtp_port, smtp_username, smtp_password, smtp_to]):
                    logging.error("SMTP配置不完整，跳过邮件发送")
                    logging.error(f"缺失配置项: host={bool(smtp_host)}, port={bool(smtp_port)}, username={bool(smtp_username)}, password={bool(smtp_password)}, to={bool(smtp_to)}")
                else:
                    logging.info(f"准备发送邮件通知，标题: {result['title']}")
                    logging.info(f"邮件内容: {result['content']}")
                    send_email(result["title"], result["content"])
                    logging.info("邮件发送完成")
            except Exception as e:
                logging.error(f"邮件发送过程中出现错误: {str(e)}")
                import traceback
                logging.error(f"错误堆栈: {traceback.format_exc()}")
                logging.warning("邮件发送失败，但打卡任务已完成")
        else:
            logging.info("SMTP邮件通知已禁用，跳过邮件发送")
        
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
                
                # 重置ConfigManager缓存，确保加载最新配置
                ConfigManager._config_cache = None
                
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
        import traceback
        logging.error(f"错误堆栈: {traceback.format_exc()}")
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