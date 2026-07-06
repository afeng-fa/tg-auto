# TG Auto - Telegram 监听 + 邮件通知

基于 Docker 的 Telegram 消息监听服务，收到私聊消息后自动触发青龙执行邮件脚本。

## 目录结构

```
tg-auto/
├── main.py                     # TG 容器主程序
├── docker-compose.example.yml  # docker-compose 模板
├── config.example.json         # 配置文件模板
├── .env.example                # 环境变量模板
├── create_instance.sh          # 创建新实例脚本
├── email_script.example.py     # 邮件脚本模板
└── README.md
```

## 工作原理

```
TG 收到私聊消息（排除自己发的）
    ↓
用 client_id + client_secret 获取青龙 token
    ↓
根据 config 中的 script 名匹配青龙定时任务 cron_id
    ↓
调用 /open/crons/run 触发执行
    ↓
青龙执行邮件脚本发送邮件
```

## 前置条件

- Docker + Docker Compose
- 青龙面板（已部署并运行）
- Telegram 账号的 API_ID 和 API_HASH（从 my.telegram.org 获取）
- QQ 邮箱 SMTP 授权码

## 快速开始

### 1. 创建实例

```bash
# 在服务器上执行
cd /opt/docker/telegram-auto-send
./create_instance.sh 1    # 创建 inst-1
```

### 2. 配置青龙

1. 在青龙面板创建应用（设置 → 应用设置）
   - 权限勾选：**脚本管理**、**定时任务**
   - 记录 `client_id` 和 `client_secret`

2. 上传邮件脚本到青龙
   - 将 `email_script.example.py` 上传到青龙脚本管理
   - 重命名为 `tg-auto-1_发邮件.py`
   - 修改 SMTP 配置

3. 创建定时任务
   - 命令：`task tg-auto-1_发邮件.py`
   - 定时：`0 0 1 1 *`（每年1月1日，实际由 TG 触发）

### 3. 配置 TG 容器

编辑 `config.json`：

```json
{
  "qinglong_url": "http://qinglong:5700",
  "qinglong_client_id": "你的client_id",
  "qinglong_client_secret": "你的client_secret",
  "script": "tg-auto-1_发邮件.py",
  "listeners": [
    {
      "name": "私聊监听",
      "chat_type": "private",
      "keyword": "",
      "enabled": true
    }
  ]
}
```

### 4. 启动服务

```bash
cd /opt/docker/telegram-auto-send/inst-1
sudo docker-compose up -d
```

### 5. 首次登录（如需要）

如果 session 文件不存在，需要交互式登录：

```bash
sudo docker-compose run --rm tg-service python main.py
```

## 多实例部署

```bash
# 创建新实例
./create_instance.sh 2    # 创建 inst-2
./create_instance.sh 3    # 创建 inst-3

# 每个实例需要：
# 1. 独立的 config.json（不同的青龙凭证）
# 2. 独立的 session 文件
# 3. 青龙中独立的脚本和定时任务
```

## 配置说明

### config.json

| 字段 | 说明 |
|------|------|
| qinglong_url | 青龙面板地址 |
| qinglong_client_id | 青龙应用 Client ID |
| qinglong_client_secret | 青龙应用 Client Secret |
| script | 对应青龙中的脚本名（自动匹配 cron_id） |
| listeners | 监听规则列表 |

### listeners 配置

| 字段 | 说明 | 可选值 |
|------|------|--------|
| name | 监听名称 | 任意 |
| chat_type | 监听类型 | private / group |
| keyword | 关键词过滤 | 空=监听所有 |
| enabled | 是否启用 | true / false |

## 常用命令

```bash
# 查看日志
sudo docker logs tg-auto-1 -f

# 重启实例
sudo docker restart tg-auto-1

# 停止实例
sudo docker stop tg-auto-1

# 重启所有实例
sudo docker restart tg-auto-1 tg-auto-2
```

## 注意事项

1. **自己发的消息不会触发** - 已过滤 `event.message.out`
2. **cron_id 自动匹配** - 根据脚本名自动查找，无需手动填写
3. **session 文件** - 包含登录状态，需妥善保管
4. **局域网部署** - 建议不要暴露到外网

## License

MIT
