import os
import sys
import random
import requests

# -----------------------------------------------------------------------------
# 👇👇👇 用户配置区域 (请在这里直接修改) 👇👇👇
# -----------------------------------------------------------------------------

# 1. 发送模式
# "text_only"   - 只发文字（从 MESSAGES 中随机选一条）
# "image_only"  - 只发图片（从 IMAGES 中随机选一张）
# "text_image"  - 图文组合（从 TEXT_IMAGE_PAIRS 中随机选一组）
# "random"      - 随机选择上述三种模式之一
SEND_MODE = "random"

# 2. 文本池（支持多条，随机选一条发送）
# 支持换行符 \n
MESSAGES = [
    "你好，这是一条测试消息",
    # "第二条消息\n第二行",
    # "第三条消息",
]

# 3. 图片池（TG 容器会从 /app/images 目录读取文件）
# 只需要填写文件名或任意路径（TG 会自动提取文件名）
IMAGES = [
    "1.jpg",
    "2.jpg",
]

# 4. 图文组合池（每项是一组文字+图片，随机选一组发送）
# 支持换行符 \n
TEXT_IMAGE_PAIRS = [
    # {"text": "这是图片1的说明\n换行测试", "image": "1.jpg"},
    # {"text": "这是图片2的说明", "image": "2.jpg"},
]

# 5. 发送目标
# 支持格式: @username / -100123456 / +8613800000000
TARGET = "@your_username"

# 6. TG 服务地址（容器内部通信，一般不需要修改）
TG_SERVICE_URL = os.getenv("TG_SERVICE_URL", "http://tg-auto-1:8080/api/call")


# -----------------------------------------------------------------------------
# 主逻辑 - 通常不需要修改
# -----------------------------------------------------------------------------

def call_api(method, params):
    """调用 TG 服务 API"""
    payload = {"method": method, "params": params}
    try:
        if "entity" in params:
            entity = params["entity"]
            if isinstance(entity, str):
                if entity.isdigit() or (entity.startswith("-") and entity[1:].isdigit()):
                    try:
                        params["entity"] = int(entity)
                    except ValueError:
                        pass
        resp = requests.post(TG_SERVICE_URL, json=payload, timeout=60)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("status") == "success":
                return True
            else:
                print(f"❌ API 错误: {result.get('error')}")
                return False
        else:
            print(f"❌ HTTP 错误: {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: 无法连接到 TG 服务 ({TG_SERVICE_URL})")
        return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def send_text(target, text):
    """发送纯文本消息"""
    print(f"📝 发送文本 -> {target}")
    return call_api("send_message", {"entity": target, "message": text})


def send_image(target, image_file):
    """发送图片（TG 容器会从 /app/images 目录读取）"""
    print(f"🖼️  发送图片 -> {target}")
    return call_api("send_file", {"entity": target, "file": image_file})


def send_text_image(target, text, image_file):
    """发送图片+文字"""
    print(f"🖼️+📝 发送图文 -> {target}")
    return call_api("send_file", {"entity": target, "file": image_file, "caption": text})


def do_send(target):
    """根据 SEND_MODE 执行发送"""
    if SEND_MODE == "text_only":
        if not MESSAGES:
            print("❌ MESSAGES 为空")
            return False
        return send_text(target, random.choice(MESSAGES))

    elif SEND_MODE == "image_only":
        if not IMAGES:
            print("❌ IMAGES 为空")
            return False
        return send_image(target, random.choice(IMAGES))

    elif SEND_MODE == "text_image":
        if not TEXT_IMAGE_PAIRS:
            print("❌ TEXT_IMAGE_PAIRS 为空")
            return False
        pair = random.choice(TEXT_IMAGE_PAIRS)
        return send_text_image(target, pair["text"], pair["image"])

    elif SEND_MODE == "random":
        choices = []
        if MESSAGES:
            choices.append("text_only")
        if IMAGES:
            choices.append("image_only")
        if TEXT_IMAGE_PAIRS:
            choices.append("text_image")
        if not choices:
            print("❌ 没有可用内容")
            return False
        mode = random.choice(choices)
        print(f"🎲 随机模式: {mode}")
        if mode == "text_only":
            return send_text(target, random.choice(MESSAGES))
        elif mode == "image_only":
            return send_image(target, random.choice(IMAGES))
        elif mode == "text_image":
            pair = random.choice(TEXT_IMAGE_PAIRS)
            return send_text_image(target, pair["text"], pair["image"])
    return False


def main():
    if not TARGET:
        print("❌ 请配置 TARGET")
        return
    print(f"📋 模式: {SEND_MODE} | 目标: {TARGET}")
    success = do_send(TARGET)
    if success:
        print("✅ 发送完成")
    else:
        print("❌ 发送失败")


if __name__ == "__main__":
    main()
