import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================================
# 用户配置区域 - 修改这里的内容
# ============================================================

SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = ""                    # QQ邮箱地址
SMTP_PASSWORD = ""                # QQ邮箱授权码
EMAIL_TO = ""                     # 接收通知的邮箱
EMAIL_SUBJECT = "TG消息通知"

# 这里写你要发送的内容，可以加emoji
EMAIL_CONTENT = """
TG消息通知

收到新的Telegram消息！
"""

# ============================================================
# 主逻辑 - 不需要修改
# ============================================================

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
