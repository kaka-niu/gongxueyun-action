# 工学云自动打卡系统实现

## 项目概述

工学云自动打卡系统是一个基于Python的自动化工具，用于自动完成工学云平台的每日打卡任务。该项目通过模拟真实用户操作，实现自动登录、获取计划信息、执行打卡以及发送邮件通知等功能。

`原作者项目地址`: https://gitee.com/gumeite-hardware-products_0/GongXueYunAutoCheckIn_CodeVersion
在基础上增加了下班卡，工作流部署代码
## 项目架构
mainn.py是单次打卡的测试文件 gong_xue_yun.py是主程序入口（带定时功能）
auto.py是GitHub Actions部署的主要文件
### 主要目录结构

```
.
├── .github/workflows/  # GitHub Actions工作流配置
│   └── auto-checkin.yml
├── manager/           # 配置和数据管理模块
│   ├── ConfigManager.py      # 系统配置管理
│   ├── PlanInfoManager.py    # 计划信息管理
│   └── UserInfoManager.py    # 用户信息管理
├── step/              # 执行步骤模块
│   ├── clockIn.py     # 打卡执行
│   ├── fetchPlan.py   # 获取计划
│   ├── login.py       # 登录
│   └── sendEmail.py   # 发送邮件
├── user/              # 用户数据存储
│   ├── planInfo.json  # 计划信息文件
│   └── userInfo.json  # 用户信息文件
├── util/              # 工具模块
│   ├── ApiService.py      # API服务接口
│   ├── CaptchaUtils.py    # 验证码处理
│   ├── CryptoUtils.py     # 加密解密工具
│   ├── HelperFunctions.py # 辅助函数
│   └── generate_send_config.py  # 生成SEND环境变量配置的脚本
├── config.json        # 系统配置文件
├── gong_xue_yun.py    # 主程序入口（带定时功能）
├── main.py           # 主执行流程
├── auto.py           # GitHub Actions部署的主要文件
├── test_send_env.py  # 测试SEND环境变量的脚本
├── SMTP_CONFIG.md    # SMTP配置详细说明
└── README.md
```

## 核心模块详解

### 1. 配置管理模块 (manager/)

#### ConfigManager.py
- 负责管理 [config.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/config.json) 配置文件
- 提供 [get](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/manager/ConfigManager.py#L57-L72) 和 [set](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/manager/ConfigManager.py#L74-L84) 方法访问任意层级的配置项
- 支持嵌套键访问，如 `ConfigManager.get("clockIn", "location", "address")`
- 缓存配置数据，避免重复读取文件

#### UserInfoManager.py
- 管理用户信息，包括登录凭证、token等
- 将用户数据存储在 [userInfo.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/user/userInfo.json) 文件中
- 提供对用户信息的缓存访问，支持嵌套键访问

#### PlanInfoManager.py
- 管理实习计划信息，存储在 [planInfo.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/user/planInfo.json) 文件中
- 实现大小写不敏感的键访问，提高容错性

### 2. 执行步骤模块 (step/)

#### login.py
- 实现登录流程，首先检查本地是否已有有效token
- 如果本地token存在且用户信息一致，则跳过登录
- 否则调用 [ApiService](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/ApiService.py#L32-L435) 执行登录操作
- 登录成功后将用户信息保存到 [userInfo.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/user/userInfo.json)

#### fetchPlan.py
- 获取用户的实习计划信息
- 检查本地是否已有计划信息，如有则跳过获取
- 调用 [ApiService.fetch_plan()](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/ApiService.py#L322-L353) 获取计划并保存到 [planInfo.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/user/planInfo.json)

#### clockIn.py
- 执行打卡操作的核心模块
- 根据配置和时间判断打卡类型（上班/下班/节假日）
- 避免重复打卡，检查当日是否已完成相应打卡
- 调用 [ApiService.submit_clock_in()](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/ApiService.py#L377-L434) 提交打卡信息

#### sendEmail.py
- 可选的邮件通知功能
- 根据配置决定是否启用邮件通知
- 发送打卡成功或失败的通知邮件

### 3. 工具模块 (util/)

#### ApiService.py
- 项目的核心网络请求模块
- 封装了与工学云服务器的所有API交互
- 处理登录、获取计划、打卡等操作
- 实现了自动处理滑块验证码和点选验证码的功能
- 包含重试机制和Token失效处理

#### CaptchaUtils.py
- 验证码识别工具
- 实现滑块拼图验证码和点选文字验证码的自动识别

#### CryptoUtils.py
- 加解密工具
- 实现AES加密解密和签名算法
- 用于处理工学云API的加密需求

#### HelperFunctions.py
- 提供辅助功能函数
- 包括工作日判断、姓名脱敏、获取当前月份信息等

## 核心功能实现

### 1. 定时打卡机制

[gong_xue_yun.py](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/gong_xue_yun.py) 文件实现了定时打卡功能：

- 支持三种打卡模式：[weekday](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/HelperFunctions.py#L147-L147)（法定工作日）、[everyday](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/HelperFunctions.py#L150-L150)（每天）、[customize](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/util/HelperFunctions.py#L153-L153)（自定义）
- 使用 [schedule](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/main.py#L9-L9) 库进行任务调度
- 每天生成随机打卡时间（在配置时间基础上增加随机分钟数）

### 2. 验证码处理

项目实现了对工学云平台验证码的自动处理：

- 滑块拼图验证码：通过图像识别技术定位滑块位置
- 点选文字验证码：识别图片中的文字并返回坐标

### 3. 加密机制

项目使用了复杂的加密机制来模拟真实用户请求：

- AES加密用于处理密码、请求参数等
- 签名算法确保请求的合法性

### 4. 防检测机制

- 随机打卡时间，避免在固定时间点打卡
- 模拟真实用户设备信息
- 智能处理验证码，确保请求的合法性

## 配置说明

[config.json](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/config.json) 文件包含以下配置项：

1. **用户信息**：手机号和密码
2. **打卡设置**：
   - 打卡模式（工作日/每天/自定义）
   - 打卡位置信息（经纬度、地址等）
   - 打卡时间设置
3. **邮件通知**：SMTP服务器配置
4. **设备信息**：模拟设备信息

## 运行流程

1. 检查是否需要在当天执行任务
2. 生成随机打卡时间
3. 执行 [main.py](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/main.py) 中的 [execute_tasks()](file:///d%3A/disk/GongXueYunAutoCheckIn_CodeVersion-master/GongXueYunAutoCheckIn_CodeVersion-master/main.py#L27-L48) 函数
4. 依次执行登录、获取计划、打卡、发送邮件等步骤
5. 记录操作日志
6. 验证成功后运行gong_xue_yun.py,设置定时任务


## 在GitHub Actions上部署

要在GitHub Actions上自动运行打卡任务，需要配置以下环境变量作为GitHub Secrets：

### 用户配置方式

您可以选择以下三种配置方式之一：

#### 1. 单用户配置
添加以下环境变量：
- `GX_USER_PHONE` - 工学云账号手机号
- `GX_USER_PASSWORD` - 工学云账号密码

#### 2. 多用户配置
添加以下环境变量（多个用户用逗号分隔）：
- `GX_USER_PHONES` - 多用户手机号列表（逗号分隔）
- `GX_USER_PASSWORDS` - 多用户密码列表（逗号分隔）

#### 3. JSON格式配置（推荐）
添加以下环境变量：
- `USER` - 完整的JSON格式配置（支持单用户和多用户）

JSON格式示例：

**单用户配置**：
```json
{
  "config": {
    "user": {
      "phone": "工学云手机号",
      "password": "工学云密码"
    },
    "clockIn": {
      "mode": "daily",
      "location": {
        "address": "打卡地址",
        "latitude": "纬度",
        "longitude": "经度",
        "province": "省份",
        "city": "城市",
        "area": "区域"
      },
      "customDays": [1, 3, 5]
    },
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
}
```

### SMTP邮件通知配置

系统支持两种方式配置SMTP邮件通知：

#### 方式一：使用SEND环境变量（推荐）

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

#### 方式二：使用单独的SMTP环境变量

在GitHub仓库的Settings > Secrets and variables > Actions中添加以下环境变量：

- `GX_SMTP_ENABLE`: 是否启用SMTP（true/false）
- `GX_SMTP_HOST`: SMTP服务器地址（如：smtp.qq.com）
- `GX_SMTP_PORT`: SMTP服务器端口（如：465）
- `GX_SMTP_USERNAME`: SMTP用户名（邮箱地址）
- `GX_SMTP_PASSWORD`: SMTP密码（QQ邮箱使用授权码）
- `GX_SMTP_FROM`: 发件人名称（如：gongxueyun）
- `GX_SMTP_TO`: 收件人邮箱地址（多个地址用逗号分隔）

### 位置信息配置

添加以下环境变量（可选）：
- `GX_LOCATION_ADDRESS`: 打卡地址
- `GX_LOCATION_LATITUDE`: 纬度
- `GX_LOCATION_LONGITUDE`: 经度
- `GX_LOCATION_PROVINCE`: 省份
- `GX_LOCATION_CITY`: 城市
- `GX_LOCATION_AREA`: 区域

### 其他配置

添加以下环境变量（可选）：
- `GX_CLOCKIN_MODE`: 打卡模式（everyday/weekday/customize）
- `GX_HOLIDAYS_CLOCKIN`: 节假日是否打卡（true/false）
- `GX_TIME_START`: 上班打卡时间（默认：8:30）
- `GX_TIME_END`: 下班打卡时间（默认：18:00）
- `GX_TIME_FLOAT`: 打卡时间浮动（分钟，默认：1）
- `GX_CUSTOM_DAYS`: 自定义打卡日（逗号分隔，如：1,2,3,4,5）
- `GX_DEVICE_INFO`: 设备信息

## 故障排除

如果系统日志显示"环境变量 SEND 未设置"，请检查：

1. 确保已在GitHub仓库的Settings > Secrets and variables > Actions中添加了SEND环境变量
2. 确保SEND环境变量的值是有效的JSON格式
3. 确保JSON中包含了所有必需的字段：enable, host, port, username, password, from, to

可以使用提供的测试脚本验证配置：

```bash
python test_send_env.py
```

也可以使用配置生成器创建正确的SEND环境变量：

```bash
python util/generate_send_config.py
```

更多详细信息请参考 [SMTP_CONFIG.md](SMTP_CONFIG.md) 文件。
      "host": "smtp服务地址",
      "port": 465,
      "username": "发件人邮箱",
      "password": "smtp密码",
      "from": "发件人名称",
      "to": ["收件人邮箱"]
    }
  }
}
```

**多用户配置**：
```json
[
  {
    "config": {
      "user": {
        "phone": "工学云手机号1",
        "password": "工学云密码1"
      },
      "clockIn": {
        "mode": "daily",
        "location": {
          "address": "打卡地址1",
          "latitude": "纬度1",
          "longitude": "经度1",
          "province": "省份1",
          "city": "城市1",
          "area": "区域1"
        },
        "customDays": [1, 3, 5]
      },
      "smtp": {
        "enable": true,
        "host": "smtp服务地址",
        "port": 465,
        "username": "发件人邮箱",
        "password": "smtp密码",
        "from": "发件人名称",
        "to": ["收件人邮箱"]
      }
    }
  },
  {
    "config": {
      "user": {
        "phone": "工学云手机号2",
        "password": "工学云密码2"
      },
      "clockIn": {
        "mode": "daily",
        "location": {
          "address": "打卡地址2",
          "latitude": "纬度2",
          "longitude": "经度2",
          "province": "省份2",
          "city": "城市2",
          "area": "区域2"
        },
        "customDays": [2, 4]
      },
      "smtp": {
        "enable": true,
        "host": "smtp服务地址",
        "port": 465,
        "username": "发件人邮箱",
        "password": "smtp密码",
        "from": "发件人名称",
        "to": ["收件人邮箱"]
      }
    }
  }
]
```

### 完整环境变量列表

| 环境变量 | 描述 | 示例值 |
|---------|------|--------|
| **用户认证信息** | | |
| `GX_USER_PHONE` | 工学云账号手机号（单用户） | 13800138000 |
| `GX_USER_PASSWORD` | 工学云账号密码（单用户） | yourpassword |
| `GX_USER_PHONES` | 多用户手机号列表（逗号分隔） | 13800138000,13900139000 |
| `GX_USER_PASSWORDS` | 多用户密码列表（逗号分隔） | password1,password2 |
| **打卡位置信息** | | |
| `GX_LOCATION_ADDRESS` | 打卡地址 | 四川省 · 资阳市 · 乐至县 · 友谊路南段与川西环线交叉口东北300米 |
| `GX_LOCATION_LATITUDE` | 纬度 | 30.428727249834488 |
| `GX_LOCATION_LONGITUDE` | 经度 | 104.90286311986283 |
| `GX_LOCATION_PROVINCE` | 省份 | 四川省 |
| `GX_LOCATION_CITY` | 城市 | 资阳市 |
| `GX_LOCATION_AREA` | 区域 | 乐至县 |
| **打卡设置** | | |
| `GX_CLOCKIN_MODE` | 打卡模式 | weekday/everyday/customize |
| `GX_HOLIDAYS_CLOCKIN` | 节假日是否打卡 | true/false |
| `GX_TIME_START` | 上班打卡时间 | 08:30 |
| `GX_TIME_END` | 下班打卡时间 | 18:00 |
| `GX_TIME_FLOAT` | 时间浮动范围（分钟） | 1 |
| **邮件通知设置**（可选） | | |
| `GX_SMTP_ENABLE` | 是否启用邮件通知 | true/false |
| `GX_SMTP_HOST` | SMTP服务器地址 | smtp.qq.com |
| `GX_SMTP_PORT` | SMTP端口 | 465 |
| `GX_SMTP_USERNAME` | SMTP用户名 | youremail@example.com |
| `GX_SMTP_PASSWORD` | SMTP密码 | yourpassword |
| `GX_SMTP_FROM` | 发件人名称 | gongxueyun |
| `GX_SMTP_TO` | 收件人列表 | 2154335573@qq.com |
| **JSON格式SMTP配置**（可选） | | |
| `SEND` | JSON格式的SMTP配置 | 参见下方示例 |

#### SEND环境变量JSON格式示例：
```json
{
  "smtp": {
    "enable": true,
    "host": "smtp.qq.com",
    "port": 465,
    "username": "your-email@qq.com",
    "password": "your-smtp-password",
    "from": "gongxueyun",
    "to": ["recipient@example.com"]
  }
}
```
| **设备信息** | | |
| `GX_DEVICE_INFO` | 模拟设备信息 | {brand: phone, systemVersion: 16, Platform: Android, isPhysicalDevice: true, incremental: V2352A} |
### 配置步骤：

1. 登录GitHub仓库
2. 进入 **Settings** -> **Secrets and variables** -> **Actions**
3. 点击 **New repository secret** 添加环境变量
4. 根据您的需求选择配置方式：
   - **单用户配置**：添加 `GX_USER_PHONE` 和 `GX_USER_PASSWORD`
   - **多用户配置**：添加 `GX_USER_PHONES` 和 `GX_USER_PASSWORDS`（多个用户用逗号分隔）
   - **JSON格式配置（推荐）**：添加 `USER` 环境变量，值为完整的JSON配置
5. 根据需要添加其他可选环境变量（位置信息、邮件通知等）
   - 对于邮件通知，可以选择使用单独的SMTP环境变量或使用 `SEND` 环境变量提供JSON格式的SMTP配置
6. 提交并推送修改后的`.github/workflows/auto-checkin.yml`文件到仓库

### 注意事项：

- 配置文件不会被提交到仓库，所有敏感信息都通过GitHub Secrets管理
- 定时任务在北京时间8:30和18:00执行，可在工作流文件中修改
- GitHub Actions运行在UTC时间，配置中的cron表达式已考虑时区转换
- 多用户配置时，确保手机号和密码的顺序一致，且数量相同
- 如果同时配置了单用户和多用户环境变量，系统将优先使用多用户配置
## 安全性考虑

- 用户密码使用AES加密存储
- 请求参数加密处理
- 自动处理各种验证机制
- 本地存储敏感信息，避免泄露

## 扩展性

- 模块化设计，易于扩展功能
- 配置化管理，灵活调整参数
- 日志记录完整，便于调试

有问题需要讨论


| 交流讨论 | 赞赏 |
|-------|-------|
| <img src="/image/1.png" width="200" alt="alt text"> | <img src="/image/2.jpg" width="200" alt="alt text"> |