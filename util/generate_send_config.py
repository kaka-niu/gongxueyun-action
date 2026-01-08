#!/usr/bin/env python3
"""
生成SEND环境变量配置
"""
import json

def generate_send_config():
    """生成SEND环境变量配置"""
    print("欢迎使用SEND环境变量配置生成器")
    print("=" * 50)
    
    # 获取用户输入
    smtp_host = input("SMTP服务器地址 (默认: smtp.qq.com): ") or "smtp.qq.com"
    smtp_port = input("SMTP服务器端口 (默认: 465): ") or "465"
    smtp_username = input("SMTP用户名 (邮箱地址): ")
    smtp_password = input("SMTP密码 (QQ邮箱使用授权码): ")
    smtp_from = input("发件人名称 (默认: gongxueyun): ") or "gongxueyun"
    smtp_to = input("收件人邮箱地址 (多个地址用逗号分隔): ")
    
    # 处理收件人列表
    to_list = [email.strip() for email in smtp_to.split(",")]
    
    # 生成配置
    config = {
        "smtp": {
            "enable": True,
            "host": smtp_host,
            "port": int(smtp_port),
            "username": smtp_username,
            "password": smtp_password,
            "from": smtp_from,
            "to": to_list
        }
    }
    
    # 转换为JSON字符串
    json_str = json.dumps(config, ensure_ascii=False, indent=2)
    
    print("\n生成的SEND环境变量配置:")
    print("-" * 50)
    print(json_str)
    print("-" * 50)
    
    print("\n使用说明:")
    print("1. 复制上面的JSON内容")
    print("2. 在GitHub仓库的Settings > Secrets and variables > Actions中添加SEND环境变量")
    print("3. 将JSON内容粘贴到SEND环境变量的值中")
    print("4. 保存设置")
    
    return config

if __name__ == "__main__":
    generate_send_config()