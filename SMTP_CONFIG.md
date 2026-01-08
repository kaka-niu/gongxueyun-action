# 自动打卡系统配置指南

## 环境变量配置

本系统支持两种方式配置SMTP邮件通知：

### 方式一：使用SEND环境变量（推荐）

在GitHub仓库的Settings > Secrets and variables > Actions中添加SEND环境变量，值为以下格式的JSON：

```json
{
  "smtp": {
    "enable": true,
    "host": "smtp.qq.com",
    "port": 465,
    "username": "your_email@qq.com",
    "password": "your_password",
    "from": "gongxueyun",
    "to": ["your_email@qq.com"]
  }
}
```

### 方式二：使用单独的SMTP环境变量

在GitHub仓库的Settings > Secrets and variables > Actions中添加以下环境变量：

- `GX_SMTP_ENABLE`: 是否启用SMTP（true/false）
- `GX_SMTP_HOST`: SMTP服务器地址（如：smtp.qq.com）
- `GX_SMTP_PORT`: SMTP服务器端口（如：465）
- `GX_SMTP_USERNAME`: SMTP用户名（邮箱地址）
- `GX_SMTP_PASSWORD`: SMTP密码（QQ邮箱使用授权码）
- `GX_SMTP_FROM`: 发件人名称（如：gongxueyun）
- `GX_SMTP_TO`: 收件人邮箱地址（多个地址用逗号分隔）

## QQ邮箱配置示例

1. 登录QQ邮箱，进入设置 > 账户
2. 开启SMTP服务
3. 获取授权码
4. 配置SEND环境变量：

```json
{
  "smtp": {
    "enable": true,
    "host": "smtp.qq.com",
    "port": 465,
    "username": "your_email@qq.com",
    "password": "your_qq_mail_authorization_code",
    "from": "gongxueyun",
    "to": ["your_email@qq.com"]
  }
}
```

## 故障排除

如果系统日志显示"环境变量 SEND 未设置"，请检查：

1. 确保已在GitHub仓库的Settings > Secrets and variables > Actions中添加了SEND环境变量
2. 确保SEND环境变量的值是有效的JSON格式
3. 确保JSON中包含了所有必需的字段：enable, host, port, username, password, from, to

可以使用提供的测试脚本验证配置：

```bash
python test_send_env.py
```

## 优先级

系统会按以下优先级使用SMTP配置：

1. 用户配置中的smtp字段（在GX_USER环境变量中）
2. SEND环境变量
3. 单独的SMTP环境变量（GX_SMTP_*）