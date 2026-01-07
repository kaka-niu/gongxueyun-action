import logging
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

from manager.ConfigManager import ConfigManager


def send_email(title, content):
    to_emails = ConfigManager.get("smtp", "to")
    smtp_host = ConfigManager.get("smtp", "host")
    smtp_port = ConfigManager.get("smtp", "port")
    smtp_username = ConfigManager.get("smtp", "username")
    smtp_password = ConfigManager.get("smtp", "password")
    from_name = ConfigManager.get("smtp", "from")
    
    logging.info(f"准备发送邮件，SMTP服务器: {smtp_host}:{smtp_port}")
    
    for to_email in to_emails:
        try:
            # 设置 MIMEText 对象
            message = MIMEText(content, 'plain', 'utf-8')
            message['Subject'] = Header(title, 'utf-8')
            from_header = Header(from_name, 'utf-8')
            message['From'] = formataddr((from_header.encode(), smtp_username))
            message['To'] = to_email
            
            logging.info(f"正在连接到SMTP服务器 {smtp_host}:{smtp_port}...")
            
            # 使用SMTP_SSL连接
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
                logging.info(f"SMTP_SSL服务器连接成功，正在登录用户 {smtp_username}...")
                server.login(smtp_username, smtp_password)
                logging.info("登录成功，正在发送邮件...")
                server.sendmail(smtp_username, to_email, message.as_string())
                logging.info(f"邮件发送成功: {to_email}")
                
        except Exception as e:
            logging.warning("邮件发送失败，但打卡任务已完成")