import logging
import os
import sys
from datetime import datetime
from manager.ConfigManager import ConfigManager
from step.clockIn import clock_in
from step.fetchPlan import fetch_plan
from step.login import login
from manager.UserInfoManager import UserInfoManager
from step.sendEmail import send_email

# ======================
# 日志配置
# ======================
log_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "main.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),  # 写入日志文件
        logging.StreamHandler(sys.stdout)  # 控制台输出
    ]
)


def execute_tasks():
    # 登录
    isLogin = login()
    if not isLogin:
        logging.warning("登录失败")
        return
    logging.info(f"用户数据：{UserInfoManager.load()}")
    logging.info(f"用户类型：{UserInfoManager.get('roleKey')}")
    if UserInfoManager.get("userType") != "student":
        sys.exit("当前用户不是学生，结束执行打卡任务")
    # 获取打卡信息
    hasPlan = fetch_plan()
    if not hasPlan:
        logging.warning("未获取到打卡信息")
        return
    # 执行打卡
    str = clock_in()
    logging.info(str)
    # 发送邮件通知
    if ConfigManager.get("smtp", "enable"):
        send_email(str["title"], str["content"])


def test_clock_in():
    """
    测试模式：只打卡一次，根据当前时间判断上班卡还是下班卡
    """
    current_time = datetime.now()
    hour = current_time.hour
    
    # 判断打卡类型
    if hour < 12:
        clock_type = "上班"
        logging.info(f"当前时间 {current_time.strftime('%H:%M')}，执行上班卡测试")
    else:
        clock_type = "下班"
        logging.info(f"当前时间 {current_time.strftime('%H:%M')}，执行下班卡测试")
    
    # 登录
    isLogin = login()
    if not isLogin:
        logging.warning("登录失败")
        return
    logging.info(f"用户数据：{UserInfoManager.load()}")
    logging.info(f"用户类型：{UserInfoManager.get('roleKey')}")
    if UserInfoManager.get("userType") != "student":
        sys.exit("当前用户不是学生，结束执行打卡任务")
    
    # 获取打卡信息
    hasPlan = fetch_plan()
    if not hasPlan:
        logging.warning("未获取到打卡信息")
        return
    
    # 执行打卡
    result = clock_in()
    logging.info(f"{clock_type}卡测试结果：{result}")
    
    # 发送邮件通知
    if ConfigManager.get("smtp", "enable"):
        send_email(result["title"], result["content"])
    
    return result

if __name__ == '__main__':
    # 测试模式：只打卡一次
    test_clock_in()
