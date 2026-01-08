import logging
import smtplib
import sys
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

from manager.ConfigManager import ConfigManager

# 获取项目根目录
if getattr(sys, 'frozen', False):
    # 打包 exe 后
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # 源码运行
    BASE_DIR = Path(__file__).resolve().parent.parent

# 创建logger实例
logger = logging.getLogger(__name__)

def send_email(title, content):
    to_emails = ConfigManager.get("smtp", "to")
    smtp_host = ConfigManager.get("smtp", "host")
    smtp_port = ConfigManager.get("smtp", "port")
    smtp_username = ConfigManager.get("smtp", "username")
    smtp_password = ConfigManager.get("smtp", "password")
    from_name = ConfigManager.get("smtp", "from")
    
    # 检查必要的邮件配置
    if not all([to_emails, smtp_host, smtp_port, smtp_username, smtp_password]):
        logger.error("邮件配置不完整，无法发送邮件")
        logger.error(f"收件人: {to_emails}, SMTP服务器: {smtp_host}:{smtp_port}, 用户名: {smtp_username}")
        return False
    
    logger.info(f"准备发送邮件，SMTP服务器: {smtp_host}:{smtp_port}")
    
    success_count = 0
    total_count = len(to_emails)
    
    for to_email in to_emails:
        try:
            # 设置 MIMEText 对象
            message = MIMEText(content, 'plain', 'utf-8')
            message['Subject'] = Header(title, 'utf-8')
            from_header = Header(from_name, 'utf-8')
            message['From'] = formataddr((from_header.encode(), smtp_username))
            message['To'] = to_email
            
            logger.info(f"正在连接到SMTP服务器 {smtp_host}:{smtp_port}...")
            
            # 使用SMTP_SSL连接
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
                logger.info(f"SMTP_SSL服务器连接成功，正在登录用户 {smtp_username}...")
                server.login(smtp_username, smtp_password)
                logger.info("登录成功，正在发送邮件...")
                server.sendmail(smtp_username, to_email, message.as_string())
                logger.info(f"邮件发送成功: {to_email}")
                success_count += 1
                
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP认证失败，请检查用户名和密码: {str(e)}")
        except smtplib.SMTPConnectError as e:
            logger.error(f"无法连接到SMTP服务器 {smtp_host}:{smtp_port}: {str(e)}")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP错误: {str(e)}")
        except Exception as e:
            logger.error(f"发送邮件到 {to_email} 时发生未知错误: {str(e)}")
    
    logger.info(f"邮件发送完成，成功发送 {success_count}/{total_count} 封邮件")
    return success_count > 0