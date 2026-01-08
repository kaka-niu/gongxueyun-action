#!/usr/bin/env python3
"""
测试SEND环境变量配置
"""
import os
import json
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def safe_get_env_var(var_name, default_value=""):
    """安全获取环境变量，带有错误处理和日志记录"""
    try:
        value = os.getenv(var_name, default_value)
        if value is None or value == "":
            if var_name == "SEND":
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

def test_send_env_var():
    """测试SEND环境变量"""
    logging.info("正在检查SEND环境变量...")
    send_json_str = safe_get_env_var("SEND")
    
    if send_json_str and send_json_str.strip():
        logging.info(f"SEND环境变量已设置，内容长度: {len(send_json_str)} 字符")
        logging.info(f"SEND环境变量前100个字符: {send_json_str[:100]}")
        
        try:
            smtp_config = json.loads(send_json_str)
            logging.info("已从SEND环境变量获取SMTP配置")
            logging.info(f"SMTP配置: {json.dumps(smtp_config, ensure_ascii=False)}")
            
            # 验证必需字段
            if "smtp" not in smtp_config:
                logging.error("SEND环境变量中缺少smtp字段")
                return False
            
            smtp = smtp_config["smtp"]
            required_fields = ["enable", "host", "port", "username", "password", "from", "to"]
            for field in required_fields:
                if field not in smtp:
                    logging.error(f"SMTP配置中缺少必需字段: {field}")
                    return False
            
            logging.info("SMTP配置验证通过")
            return True
        except json.JSONDecodeError as e:
            logging.error(f"SEND环境变量JSON格式错误: {str(e)}")
            logging.error(f"SEND环境变量内容: {send_json_str}")
            return False
    else:
        logging.warning("SEND环境变量未设置或为空")
        return False

if __name__ == "__main__":
    success = test_send_env_var()
    if success:
        print("\n✅ SEND环境变量配置正确")
    else:
        print("\n❌ SEND环境变量配置有误")
        print("\n请在GitHub仓库的Settings > Secrets and variables > Actions中添加SEND环境变量")
        print("SEND环境变量应包含以下格式的JSON:")
        print('{ "smtp": { "enable": true, "host": "smtp.qq.com", "port": 465, "username": "your_email@qq.com", "password": "your_password", "from": "gongxueyun", "to": ["your_email@qq.com"] } }')