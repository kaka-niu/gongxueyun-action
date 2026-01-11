#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工学云自动签到脚本
支持多用户配置，可在GitHub Actions上运行
"""

import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
# 在文件顶部的导入部分添加
import yaml
# 导入现有模块
from manager.ConfigManager import ConfigManager, CONFIG_PATH as ORIGINAL_CONFIG_PATH
from manager.UserInfoManager import UserInfoManager, USER_INFO_PATH as ORIGINAL_USER_INFO_PATH
from manager.PlanInfoManager import PlanInfoManager, PLAN_INFO_PATH as ORIGINAL_PLAN_INFO_PATH
from step.clockIn import clock_in
from step.fetchPlan import fetch_plan
from step.login import login
from step.sendEmail import send_email
from util.HelperFunctions import get_checkin_type

def is_custom_checkin_day(user_config):
    """检查当前日期是否为自定义打卡日期"""
    try:
        # 获取自定义打卡日期配置
        custom_days = user_config.get("config", {}).get("clockIn", {}).get("customDays", [])
        
        # 如果没有配置自定义日期，则默认每天都打卡
        if not custom_days:
            return True
        
        # 获取当前日期（星期几，0-6，0代表周一）
        from datetime import datetime
        current_weekday = datetime.now().weekday()
        
        # 转换为配置格式（1-7代表周一至周日）
        # Python weekday(): 0=周一, 1=周二, ..., 6=周日
        # 配置格式: 1=周一, 2=周二, ..., 7=周日
        config_weekday = current_weekday + 1
        
        # 检查当前日期是否在自定义打卡日期内
        if config_weekday in custom_days:
            weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            logging.info(f"今天是{weekday_names[current_weekday]}，在自定义打卡日期内")
            return True
        else:
            weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            logging.info(f"今天是{weekday_names[current_weekday]}，不在自定义打卡日期内，跳过打卡")
            return False
            
    except Exception as e:
        logging.error(f"检查自定义打卡日期时发生错误: {e}")
        # 发生错误时默认打卡，避免漏打
        return True

# ======================
# 日志配置
# ======================
def setup_logging():
    """设置日志配置"""
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),  # 写入日志文件
            logging.StreamHandler(sys.stdout)  # 控制台输出
        ]
    )

def load_users_config():
    """从环境变量或配置文件加载用户配置"""
    # 尝试从环境变量获取用户配置
    users_json = os.environ.get('USERS', None)
    
    if users_json:
        try:
            # 添加调试信息
            logging.info(f"从环境变量获取的USERS内容: {users_json[:100]}...")  # 只显示前100个字符
            users = json.loads(users_json)
            logging.info(f"从环境变量加载了 {len(users)} 个用户配置")
            return users
        except json.JSONDecodeError as e:
            logging.error(f"解析环境变量中的用户配置失败: {e}")
            logging.error(f"USERS内容: {users_json}")
            return None
        except Exception as e:
            logging.error(f"加载用户配置时发生未知错误: {e}")
            return None
    
    # ... 其余代码保持不变

def setup_user_config(user_config):
    """为单个用户设置配置"""
    # 创建临时目录存储用户配置
    temp_dir = tempfile.mkdtemp()
    
    # 设置配置文件路径
    config_path = os.path.join(temp_dir, "config.json")
    user_dir = os.path.join(temp_dir, "user")
    os.makedirs(user_dir, exist_ok=True)
    
    # 写入配置文件
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(user_config, f, ensure_ascii=False, indent=4)
    
    # 保存原始路径
    original_config_path = ORIGINAL_CONFIG_PATH
    original_user_info_path = ORIGINAL_USER_INFO_PATH
    original_plan_info_path = ORIGINAL_PLAN_INFO_PATH
    
    # 导入模块并修改路径常量
    import manager.ConfigManager as cm
    import manager.UserInfoManager as uim
    import manager.PlanInfoManager as pim
    
    # 更新路径常量
    cm.CONFIG_PATH = Path(config_path)
    uim.USER_INFO_PATH = Path(user_dir) / "userInfo.json"
    pim.PLAN_INFO_PATH = Path(user_dir) / "planInfo.json"
    
    # 清除缓存
    ConfigManager._config_cache = None
    UserInfoManager._userInfo_cache = None
    PlanInfoManager._planinfo_cache = None
    
    # 返回临时目录和原始路径，以便后续恢复
    return temp_dir, original_config_path, original_user_info_path, original_plan_info_path

def execute_clock_in(user_config, clock_type=None):
    """为单个用户执行打卡操作"""
    phone = user_config.get("config", {}).get("user", {}).get("phone", "未知用户")
    logging.info(f"开始为用户 {phone} 执行打卡任务")
    
    # 检查自定义打卡日期
    if not is_custom_checkin_day(user_config):
        logging.info(f"用户 {phone} 今日不在自定义打卡日期内，跳过打卡")
        return True  # 返回True表示成功跳过，不视为失败
    
    # 设置用户配置
    temp_dir, original_config_path, original_user_info_path, original_plan_info_path = setup_user_config(user_config)
    
    try:
        # 判断打卡类型
        if clock_type is None:
            # 获取北京时间（UTC+8）
            from datetime import timezone, timedelta
            current_time = datetime.now(timezone(timedelta(hours=8)))
            hour = current_time.hour
            clock_type = "上班" if hour < 12 else "下班"
            logging.info(f"当前北京时间: {current_time.strftime('%H:%M')}, 执行{clock_type}卡")
        else:
            logging.info(f"执行{clock_type}卡打卡")
        
        # 登录
        is_login = login()
        if not is_login:
            logging.warning(f"用户 {phone} 登录失败")
            return False
        
        logging.info(f"用户 {phone} 登录成功")
        
        # 获取打卡信息
        has_plan = fetch_plan()
        if not has_plan:
            logging.warning(f"用户 {phone} 未获取到打卡信息")
            return False
        
        # 执行打卡 - 根据clock_type参数决定打卡类型
        result = clock_in_with_type(clock_type)
        logging.info(f"用户 {phone} 打卡结果: {result}")
        
        # 发送邮件通知
        if user_config.get("config", {}).get("smtp", {}).get("enable", False):
            send_email(result["title"], result["content"])
        
        return True
    
    except Exception as e:
        logging.error(f"用户 {phone} 打卡过程中发生异常: {e}")
        return False
    
    finally:
        # 恢复原始路径
        import manager.ConfigManager as cm
        import manager.UserInfoManager as uim
        import manager.PlanInfoManager as pim
        
        cm.CONFIG_PATH = original_config_path
        uim.USER_INFO_PATH = original_user_info_path
        pim.PLAN_INFO_PATH = original_plan_info_path
        
        # 清除缓存
        ConfigManager._config_cache = None
        UserInfoManager._userInfo_cache = None
        PlanInfoManager._planinfo_cache = None
        
        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
def clock_in_with_type(clock_type):
    """
    根据指定的打卡类型执行打卡
    """
    from manager.ConfigManager import ConfigManager
    from util.ApiService import ApiService
    from util.HelperFunctions import desensitize_name, desensitize_phone, desensitize_address
    from manager.UserInfoManager import UserInfoManager
    from datetime import datetime
    
    logging.info(f"执行{clock_type}卡打卡")
    
    current_time = datetime.now()
    
    # 根据clock_type设置打卡类型
    if clock_type == "上班":
        checkin_type = "START"
        display_type = "上班"
    elif clock_type == "下班":
        checkin_type = "END"
        display_type = "下班"
    else:
        # 默认上班卡
        checkin_type = "START"
        display_type = "上班"
    
    # 调用API服务 - 每次创建新的实例确保使用当前用户配置
    api_client = ApiService()
    
    # 重新获取当前用户的打卡信息，确保不是前一个用户的信息
    try:
        # 清除缓存，强制重新获取当前用户信息
        UserInfoManager._userInfo_cache = None
        PlanInfoManager._planinfo_cache = None
        
        # 获取打卡信息
        last_checkin_info = api_client.get_checkin_info()
        
        # 检查是否已经打过卡
        if last_checkin_info and last_checkin_info.get("type") == checkin_type:
            last_checkin_time = datetime.strptime(
                last_checkin_info["createTime"], "%Y-%m-%d %H:%M:%S")
            if last_checkin_time.date() == current_time.date():
                log = f"今日[{display_type}]卡已打，无需重复打卡"
                logging.info(log)
                return {"title": "工学云签到任务通知", "content": log}
    except Exception as e:
        logging.warning(f"获取打卡信息失败，继续执行打卡: {e}")
        last_checkin_info = None

    user_name = desensitize_name(UserInfoManager.get("nikeName"))
    logging.info(f"用户 {user_name} 开始 {display_type} 打卡")

    # 设置打卡信息
    checkin_info = {
        "type": checkin_type,
        "lastDetailAddress": last_checkin_info.get("address") if last_checkin_info else None,
        "attachments": None,
        "description": "",
    }

    success = api_client.submit_clock_in(checkin_info)

    # 记录获取结果
    if success.get("result"):
        logging.info("打卡成功")
        # 使用脱敏函数处理敏感信息
        phone = desensitize_phone(ConfigManager.get('user', 'phone'))
        address = desensitize_address(ConfigManager.get('clockIn', 'location', 'address'))
        content = f"签到账号：{phone}\n签到地点：{address}"
        return {"title": "工学云签到成功通知", "content": content}
    else:
        logging.warning(f"打卡失败：{success.get('data')}")
        # 打卡失败时也返回账号和地点信息
        phone = desensitize_phone(ConfigManager.get('user', 'phone'))
        address = desensitize_address(ConfigManager.get('clockIn', 'location', 'address'))
        content = f"签到账号：{phone}\n签到地点：{address}\n失败原因：{success.get('data')}"
        return {"title": "工学云签到失败通知", "content": content}

def main():
    """主函数"""
    setup_logging()
    
    # 获取执行模式
    mode = os.environ.get('MODE', 'manual')  # 默认为手动模式
    
    # 加载用户配置
    users = load_users_config()
    if not users:
        logging.error("未找到用户配置，程序退出")
        sys.exit(1)
    
    # 判断打卡类型
    clock_type = None
    if mode == 'morning':
        clock_type = "上班"
    elif mode == 'evening':
        clock_type = "下班"
    
    # 执行打卡
    success_count = 0
    total_count = len(users)
    
    for user_config in users:
        if execute_clock_in(user_config, clock_type):
            success_count += 1
    
    logging.info(f"打卡任务完成，成功: {success_count}/{total_count}")
    
    # 如果有用户打卡失败，返回非零退出码
    if success_count < total_count:
        sys.exit(1)

if __name__ == '__main__':
    main()