import json
import logging
import random
import re
import time
import uuid
from typing import Dict, Any, List, Optional

import requests

from manager.ConfigManager import ConfigManager
from manager.PlanInfoManager import PlanInfoManager
from manager.UserInfoManager import UserInfoManager
from util.CaptchaUtils import recognize_blockPuzzle_captcha, recognize_clickWord_captcha
from util.CryptoUtils import create_sign, aes_encrypt, aes_decrypt
from util.HelperFunctions import get_current_month_info

logger = logging.getLogger(__name__)

# 常量
BASE_URL = "https://api.moguding.net:9000/"
HEADERS = {
    "user-agent": "Dart/2.17 (dart:io)",
    "content-type": "application/json; charset=utf-8",
    "accept-encoding": "gzip",
    "host": "api.moguding.net:9000",
}

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

def desensitize_log_data(log_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    对日志数据中的敏感信息进行脱敏处理。
    
    Args:
        log_data (Dict[str, Any]): 包含敏感信息的日志数据。
        
    Returns:
        Dict[str, Any]: 脱敏后的日志数据。
    """
    desensitized_data = log_data.copy()
    
    # 脱敏手机号
    if 'phone' in desensitized_data:
        desensitized_data['phone'] = desensitize_phone(desensitized_data['phone'])
    
    # 脱敏密码字段
    if 'password' in desensitized_data:
        desensitized_data['password'] = '***'
    
    # 脱敏token等认证信息
    sensitive_keys = ['token', 'authorization', 'password', 'captcha', 'uuid']
    for key in sensitive_keys:
        if key in desensitized_data:
            desensitized_data[key] = '***'
    
    return desensitized_data

class ApiService:
    """API服务类，用于处理与工学云服务器的交互。"""

    def __init__(self):
        """初始化API服务实例。"""
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _post_request(self, url: str, headers: Dict[str, str], data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送POST请求到指定的URL。

        Args:
            url (str): 请求的URL。
            headers (Dict[str, str]): 请求头。
            data (Dict[str, Any]): 请求数据。

        Returns:
            Dict[str, Any]: 响应数据。

        Raises:
            ValueError: 如果请求失败或返回错误状态码，抛出包含详细错误信息的异常。
        """
        try:
            response = self.session.post(BASE_URL + url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            raise ValueError(f"请求失败: {str(e)}")

    def _get_authenticated_headers(
            self,
            sign_data: Optional[List[Optional[str]]] = None  # 允许 List[str | None]
    ) -> Dict[str, str]:
        """
        生成带有认证信息的请求头。

        该方法会从配置管理器中获取用户的Token、用户ID及角色Key，并生成包含这些信息的请求头。
        如果提供了sign_data，还会生成并添加签名信息。

        Args:
            sign_data (Optional[List[str]]): 用于生成签名的数据列表，默认为None。

        Returns:
            包含认证信息和签名的请求头字典。
        """
        headers = {
            **HEADERS,
            "authorization": UserInfoManager.get_token(),
            "userid": UserInfoManager.get_userid(),
            "rolekey": UserInfoManager.get("roleKey"),
        }
        if sign_data:
            headers["sign"] = create_sign(*sign_data)
        return headers

    def pass_blockPuzzle_captcha(self) -> str:
        """
        处理滑块验证码，获取验证结果。

        Returns:
            str: 验证码识别结果的JSON字符串。
        """
        try:
            # 获取验证码图片
            captcha_url = "attach/captcha/slider"
            response = self.session.get(BASE_URL + captcha_url, timeout=30)
            response.raise_for_status()
            
            captcha_data = response.json()
            if not captcha_data.get("data"):
                logger.error("获取滑块验证码失败：返回数据为空")
                raise ValueError("获取滑块验证码失败：返回数据为空")
            
            # 提取验证码图片数据
            target = captcha_data["data"].get("targetImage", "")
            background = captcha_data["data"].get("backImage", "")
            
            if not target or not background:
                logger.error("滑块验证码图片数据不完整")
                raise ValueError("滑块验证码图片数据不完整")
            
            # 调用验证码识别函数
            result = recognize_blockPuzzle_captcha(target, background)
            logger.info("滑块验证码识别成功")
            return result
            
        except Exception as e:
            logger.error(f"滑块验证码处理失败: {e}")
            raise

    def solve_click_word_captcha(self) -> str:
        """
        处理点击文字验证码，获取验证结果。

        Returns:
            str: 验证码识别结果的JSON字符串。
        """
        try:
            # 获取验证码图片
            captcha_url = "attach/captcha/clickWord"
            response = self.session.get(BASE_URL + captcha_url, timeout=30)
            response.raise_for_status()
            
            captcha_data = response.json()
            if not captcha_data.get("data"):
                logger.error("获取点击文字验证码失败：返回数据为空")
                raise ValueError("获取点击文字验证码失败：返回数据为空")
            
            # 提取验证码图片数据和文字列表
            target = captcha_data["data"].get("targetImage", "")
            wordlist = captcha_data["data"].get("wordList", [])
            
            if not target or not wordlist:
                logger.error("点击文字验证码数据不完整")
                raise ValueError("点击文字验证码数据不完整")
            
            # 调用验证码识别函数
            result = recognize_clickWord_captcha(target, wordlist)
            logger.info("点击文字验证码识别成功")
            return result
            
        except Exception as e:
            logger.error(f"点击文字验证码处理失败: {e}")
            raise

    def login(self) -> bool:
        """
        执行用户登录操作，成功后将 user_info 写入 UserInfoManager 管理的缓存和文件。

        Returns:
            bool: 登录并写入成功返回 True，否则返回 False
        """
        logger.info("执行登录")

        try:
            url = "session/user/v6/login"
            data = {
                "phone": aes_encrypt(ConfigManager.get("user", "phone")),
                "password": aes_encrypt(ConfigManager.get("user", "password")),
                "captcha": self.pass_blockPuzzle_captcha(),
                "loginType": "android",
                "uuid": str(uuid.uuid4()).replace("-", ""),
                "device": "android",
                "version": "5.16.0",
                "t": aes_encrypt(str(int(time.time() * 1000))),
            }

            # 使用脱敏后的数据进行日志记录
            desensitized_data = desensitize_log_data({
                "phone": ConfigManager.get("user", "phone"),
                "password": "***",  # 密码已加密，但仍显示为***
                "captcha": "***",
                "loginType": "android",
                "uuid": "***",
                "device": "android",
                "version": "5.16.0",
                "t": "***"
            })
            logger.info(f"登录数据：{desensitized_data}")
            
            response = self._post_request(url, HEADERS, data)

            encrypted_data = response.get("data")
            if not encrypted_data:
                logger.error("登录失败：返回数据为空")
                return False

            user_info = json.loads(aes_decrypt(encrypted_data))
            
            # 脱敏用户信息中的敏感数据
            desensitized_user_info = user_info.copy()
            if 'phone' in desensitized_user_info:
                desensitized_user_info['phone'] = desensitize_phone(desensitized_user_info['phone'])
            logger.info(f"登录结果：{desensitized_user_info}")

            # 使用 UserInfoManager 写入缓存和文件
            UserInfoManager.set_userinfo(user_info)

            logger.info("用户信息已保存到 UserInfoManager 管理的文件和缓存中")
            return True

        except Exception as e:
            logger.exception(f"登录过程发生异常：{e}")
            return False

    def fetch_plan(self) -> bool:
        """
        获取当前用户的实习计划并更新 PlanInfoManager 中的 planInfo。

        返回:
            bool: 成功获取并更新 planInfo 返回 True，否则返回 False
        """
        try:
            # 生成请求
            url = "practice/plan/v3/getPlanByStu"
            data = {
                "pageSize": 999999,
                "t": aes_encrypt(str(int(time.time() * 1000)))
            }
            headers = self._get_authenticated_headers(sign_data=[
                UserInfoManager.get_userid(),
                UserInfoManager.get("roleKey"),
            ])

            # 发送请求
            rsp = self._post_request(url, headers, data)

            # 获取实习计划列表
            data_list = rsp.get("data")
            if not data_list or not isinstance(data_list, list):
                logger.warning("未获取到实习计划数据，rsp 内容: %s", rsp)
                return False

            plan_info = data_list[0]
            if not plan_info:
                logger.warning("实习计划数据为空")
                return False
            
            # 脱敏计划信息中的敏感数据
            desensitized_plan_info = plan_info.copy()
            sensitive_fields = ['mobile', 'teacherName', 'createName']
            for field in sensitive_fields:
                if field in desensitized_plan_info and desensitized_plan_info[field]:
                    desensitized_plan_info[field] = '***'
            
            logger.info("获取到的实习计划数据: %s", desensitized_plan_info)
            # 更新缓存和文件
            PlanInfoManager.set_planinfo(plan_info)
            logger.info("实习计划信息已更新到 PlanInfoManager")
            return True

        except Exception as e:
            logger.exception("获取实习计划过程中发生异常: %s", e)
            return False

    def get_checkin_info(self) -> Dict[str, Any] | List[Dict[str, Any]]:
        """
        获取用户的打卡信息。

        该方法会发送请求获取当前用户当月的打卡记录。

        Returns:
            包含用户打卡信息的字典或字典列表。

        Raises:
            ValueError: 如果获取打卡信息失败，抛出包含详细错误信息的异常。
        """
        url = "attendence/clock/v2/listSynchro"
        if UserInfoManager.get("userType") == "teacher":
            url = "attendence/clock/teacher/v1/listSynchro"
        headers = self._get_authenticated_headers()
        data = {
            **get_current_month_info(),
            "t":
                aes_encrypt(str(int(time.time() * 1000))),
        }
        rsp = self._post_request(url, headers, data)
        # 返回打卡记录列表，如果为空则返回空列表
        return rsp.get("data", []) if rsp.get("data") else []

    def submit_clock_in(self, checkin_info: Dict[str, Any]) -> dict[str, dict[str, Any] | bool] | None:
        """
        提交打卡信息。

        该方法会根据传入的打卡信息生成打卡请求，并发送至服务器完成打卡操作。

        Args:
            checkin_info (Dict[str, Any]): 包含打卡类型及相关信息的字典。

        Raises:
            ValueError: 如果打卡提交失败，抛出包含详细错误信息的异常。
        """
        url = "attendence/clock/teacher/v2/save"
        sign_data = None
        planId = PlanInfoManager.get_plan_id()

        if UserInfoManager.get("userType") != "teacher":
            url = "attendence/clock/v5/save"
            sign_data = [
                ConfigManager.get("device"),
                checkin_info.get("type"),
                planId,
                UserInfoManager.get_userid(),
                ConfigManager.get("clockIn", "location", "address")
            ]

        logger.info(f'打卡类型：{checkin_info.get("type")}')

        data = {
            "distance": None,
            "content": None,
            "lastAddress": None,
            "lastDetailAddress": checkin_info.get("lastDetailAddress"),
            "attendanceId": None,
            "country": "中国",
            "createBy": None,
            "createTime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "description": checkin_info.get("description", None),
            "device": ConfigManager.get("device"),
            "images": None,
            "isDeleted": None,
            "isReplace": None,
            "modifiedBy": None,
            "modifiedTime": None,
            "schoolId": None,
            "state": "NORMAL",
            "teacherId": None,
            "teacherNumber": None,
            "type": checkin_info.get("type"),
            "stuId": None,
            "planId": planId,
            "attendanceType": None,
            "username": None,
            "attachments": checkin_info.get("attachments", None),
            "userId": UserInfoManager.get_userid(),
            "isSYN": None,
            "studentId": None,
            "applyState": None,
            "studentNumber": None,
            "memberNumber": None,
            "headImg": None,
            "attendenceTime": None,
            "depName": None,
            "majorName": None,
            "className": None,
            "logDtoList": None,
            "isBeyondFence": None,
            "practiceAddress": None,
            "tpJobId": None,
            "t": aes_encrypt(str(int(time.time() * 1000))),
        }

        data.update(ConfigManager.get("clockIn", "location"))

        headers = self._get_authenticated_headers(sign_data)

        responses = self._post_request(url, headers, data)
        if responses.get("msg") == "302":
            logger.info("检测到行为验证码，正在通过···")
            data["captcha"] = self.solve_click_word_captcha()
            rsp = self._post_request(url, headers, data)
            logger.info(f"打卡结果: {rsp}")
            return {"result": True, "data": rsp}
        else:
            return {"result": True, "data": responses}