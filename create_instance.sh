#!/bin/bash

# 配置区 - 部署时修改这里
QL_URL="http://qinglong:5700"
QL_USERNAME="你的青龙用户名"
QL_PASSWORD="你的青龙密码"

INST_NUM=${1:-1}
BASE_DIR="/opt/docker/telegram-auto-send"
INST_DIR="${BASE_DIR}/inst-${INST_NUM}"
CONTAINER_NAME="tg-auto-${INST_NUM}"
SCRIPT_NAME="tg-auto-${INST_NUM}_发邮件.py"
CRON_NAME="TG邮件通知-${INST_NUM}"

if [ -d "$INST_DIR" ]; then
    echo "错误: 实例 inst-${INST_NUM} 已存在"
    exit 1
fi

echo "创建实例 inst-${INST_NUM}..."

mkdir -p "${INST_DIR}/sessions"

cat > "${INST_DIR}/docker-compose.yml" << EOF
services:
  tg-service:
    image: tg-service:latest
    container_name: ${CONTAINER_NAME}
    restart: unless-stopped
    networks:
      - switch
    volumes:
      - ${INST_DIR}/config.json:/app/config.json
      - ${INST_DIR}/sessions:/app/sessions
    environment:
      - HTTP_PORT=8080
      - TZ=Asia/Shanghai
    logging:
      driver: json-file
      options:
        max-size: 10m
        max-file: 3

networks:
  switch:
    external: true
EOF

cat > "${INST_DIR}/.env" << EOF
API_ID=你的API_ID
API_HASH=你的API_HASH
PHONE_NUMBER=+86你的手机号
EOF

cat > "${INST_DIR}/config.json" << EOF
{
  "qinglong_url": "${QL_URL}",
  "qinglong_client_id": "",
  "qinglong_client_secret": "",
  "script": "${SCRIPT_NAME}",
  "listeners": [
    {
      "name": "私聊监听",
      "chat_type": "private",
      "keyword": "",
      "enabled": true
    }
  ]
}
EOF

QL_SCRIPT_PATH="/tmp/${SCRIPT_NAME}"
cat > "${QL_SCRIPT_PATH}" << QLEOF
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = ""
SMTP_PASSWORD = ""
EMAIL_TO = ""
EMAIL_SUBJECT = "TG消息通知 - ${CONTAINER_NAME}"

EMAIL_CONTENT = """
TG消息通知

收到新的Telegram消息！
"""

def send_email():
    if not SMTP_USER or not SMTP_PASSWORD or not EMAIL_TO:
        print("Error: SMTP configuration incomplete")
        return
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = EMAIL_SUBJECT
    msg.attach(MIMEText(EMAIL_CONTENT, "plain", "utf-8"))
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, EMAIL_TO, msg.as_string())
        server.quit()
        print(f"Email sent to {EMAIL_TO}")
    except Exception as e:
        print(f"Send email error: {e}")

if __name__ == "__main__":
    send_email()
QLEOF

sudo docker cp "${QL_SCRIPT_PATH}" qinglong:"/ql/data/scripts/${SCRIPT_NAME}"
rm -f "${QL_SCRIPT_PATH}"

TOKEN=$(curl -s "${QL_URL}/api/user/login" -H "Content-Type: application/json" -d "{\"username\":\"${QL_USERNAME}\",\"password\":\"${QL_PASSWORD}\"}" | jq -r '.data.token')
RESULT=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "${QL_URL}/api/crons" -d "{\"name\":\"${CRON_NAME}\",\"command\":\"task ${SCRIPT_NAME}\",\"schedule\":\"0 0 1 1 *\"}")
CRON_ID=$(echo $RESULT | jq -r '.data.id')

echo ""
echo "=== 实例 inst-${INST_NUM} 创建完成 ==="
echo "青龙脚本: ${SCRIPT_NAME}"
echo "青龙定时任务: ${CRON_NAME} (ID: ${CRON_ID})"
echo ""
echo "下一步:"
echo "1. 填写 .env: nano ${INST_DIR}/.env"
echo "2. 填写邮件脚本 SMTP: 在青龙面板编辑 ${SCRIPT_NAME}"
echo "3. 填写 config.json 青龙凭证: nano ${INST_DIR}/config.json"
echo "4. 首次登录: cd ${INST_DIR} && sudo docker-compose run --rm tg-service python main.py"
echo "5. 启动: cd ${INST_DIR} && sudo docker-compose up -d"
