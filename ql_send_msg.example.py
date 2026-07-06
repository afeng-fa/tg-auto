# Licensed under the MIT License. See LICENSE file in the project root for full license information.

###########################################################################
#                           免责声明 (DISCLAIMER)                          #
# ======================================================================= #
# 1. 用途限制：本代码模板仅用于学习、研究和个人非商业用途，严禁用于以下违规场景：
#    - 违反Telegram API使用条款的行为（如批量发送消息、批量加群/拉人、刷屏、骚扰用户）；
#    - 传播违法信息、诈骗、广告营销、侵犯他人隐私等违反法律法规的行为；
#    - 任何损害Telegram平台或第三方合法权益的行为。
#
# 2. 合规要求：使用者必须严格遵守《Telegram API使用条款》(https://core.telegram.org/api/terms)
#    及使用者所在地的所有法律法规，自行承担合规审查义务。
#
# 3. 责任豁免：
#    - 作者不对本代码模板的功能完整性、稳定性、安全性做任何明示或默示的担保；
#    - 作者不承担因使用/修改/分发本代码模板导致的任何直接/间接损失，包括但不限于：
#      Telegram账号封禁、数据泄露、法律纠纷、财产损失、商誉损失等；
#    - 使用者因违规使用本代码模板产生的一切法律责任、经济赔偿，均由使用者自行承担，
#      与代码作者无任何关联。
#
# 4. 衍生作品：基于本模板开发的衍生作品，其使用风险、合规责任均由衍生作品开发者/使用者承担，
#    作者不对衍生作品的任何行为负责。
#
# 5. 风险提示：Telegram官方有权根据使用条款限制/封禁违规账号，违规使用本模板将导致账号
#    永久封禁，且可能触发法律追责，使用者需自行评估风险。
###########################################################################
import os
import sys
import random
import tempfile
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
MESSAGES = [
    "你好，这是一条测试消息",
    # "第二条消息",
    # "第三条消息",
]

# 3. 图片池（本地路径或 HTTP URL，随机选一张发送）
IMAGES = [
    # "/path/to/image1.jpg",
    # "https://example.com/image2.png",
]

# 4. 图文组合池（每项是一组文字+图片，随机选一组发送）
TEXT_IMAGE_PAIRS = [
    # {"text": "这是图片1的说明", "image": "/path/to/img1.jpg"},
    # {"text": "这是图片2的说明", "image": "https://example.com/img2.png"},
]

# 5. 发送目标
# 支持格式: @username / -100123456 / +8613800000000
TARGET = "@your_username"

# 6. TG 服务地址
TG_SERVICE_URL = os.getenv("TG_SERVICE_URL", "http://tg-auto-1:8080/api/call")


# -----------------------------------------------------------------------------
# 主逻辑 - 通常不需要修改
# -----------------------------------------------------------------------------

def is_url(path):
    return path.startswith("http://") or path.startswith("https://")


def download_file(url):
    """下载远程文件到临时目录，返回本地路径"""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        # 从 URL 或 Content-Type 推断扩展名
        content_type = resp.headers.get("Content-Type", "")
        ext = ".jpg"
        if "png" in content_type:
            ext = ".png"
        elif "gif" in content_type:
            ext = ".gif"
        elif "webp" in content_type:
            ext = ".webp"

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(resp.content)
        tmp.close()
        return tmp.name
    except Exception as e:
        print(f"❌ 下载文件失败: {url} - {e}")
        return None


def prepare_file(path_or_url):
    """准备文件：如果是 URL 则下载到本地，返回本地路径"""
    if is_url(path_or_url):
        return download_file(path_or_url)
    return path_or_url


def call_api(method, params):
    """调用 TG 服务 API"""
    payload = {"method": method, "params": params}
    try:
        # target 是纯数字字符串时转为整数
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


def send_image(target, image_path):
    """发送图片"""
    local_path = prepare_file(image_path)
    if not local_path:
        return False
    try:
        print(f"🖼️  发送图片 -> {target}")
        return call_api("send_file", {"entity": target, "file": local_path})
    finally:
        # 清理下载的临时文件
        if is_url(image_path) and local_path and os.path.exists(local_path):
            os.unlink(local_path)


def send_text_image(target, text, image_path):
    """发送图片+文字"""
    local_path = prepare_file(image_path)
    if not local_path:
        return False
    try:
        print(f"🖼️+📝 发送图文 -> {target}")
        return call_api("send_file", {"entity": target, "file": local_path, "caption": text})
    finally:
        if is_url(image_path) and local_path and os.path.exists(local_path):
            os.unlink(local_path)


def do_send(target):
    """根据 SEND_MODE 执行发送"""
    if SEND_MODE == "text_only":
        if not MESSAGES:
            print("❌ MESSAGES 为空，无法发送")
            return False
        return send_text(target, random.choice(MESSAGES))

    elif SEND_MODE == "image_only":
        if not IMAGES:
            print("❌ IMAGES 为空，无法发送")
            return False
        return send_image(target, random.choice(IMAGES))

    elif SEND_MODE == "text_image":
        if not TEXT_IMAGE_PAIRS:
            print("❌ TEXT_IMAGE_PAIRS 为空，无法发送")
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
            print("❌ 没有可用的内容池，请配置 MESSAGES / IMAGES / TEXT_IMAGE_PAIRS")
            return False
        mode = random.choice(choices)
        print(f"🎲 随机模式: {mode}")
        return do_send_with_mode(target, mode)

    else:
        print(f"❌ 未知的 SEND_MODE: {SEND_MODE}")
        return False


def do_send_with_mode(target, mode):
    """按指定模式发送"""
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
        print("❌ 请配置发送目标 TARGET")
        return

    if SEND_MODE == "random" and not MESSAGES and not IMAGES and not TEXT_IMAGE_PAIRS:
        print("❌ 请至少配置一个内容池: MESSAGES / IMAGES / TEXT_IMAGE_PAIRS")
        return

    print(f"📋 模式: {SEND_MODE} | 目标: {TARGET}")
    success = do_send(TARGET)
    if success:
        print("✅ 发送完成")
    else:
        print("❌ 发送失败")


if __name__ == "__main__":
    main()
