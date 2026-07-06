import os
import json
import logging
import asyncio
import aiohttp
import base64
from datetime import datetime
from aiohttp import web
from telethon import TelegramClient, events, functions, types
from telethon.tl.tlobject import TLObject

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SESSION_DIR = "/app/sessions"
SESSION_NAME = "tg_session"
CONFIG_FILE = "/app/config.json"
HTTP_PORT = int(os.getenv("HTTP_PORT", 8080))

os.makedirs(SESSION_DIR, exist_ok=True)
session_path = os.path.join(SESSION_DIR, SESSION_NAME)
session_file = session_path + ".session"

if os.path.exists(session_file):
    API_ID = int(os.getenv("API_ID", "12345678"))
    API_HASH = os.getenv("API_HASH", "hash123456")
else:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")

client = TelegramClient(session_path, API_ID, API_HASH)

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Load config error: {e}")
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Save config error: {e}")

async def get_qinglong_token(config):
    client_id = config.get("qinglong_client_id", "")
    client_secret = config.get("qinglong_client_secret", "")
    if not client_id or not client_secret:
        return None
    try:
        qinglong_url = config.get("qinglong_url", "http://qinglong:5700")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{qinglong_url}/open/auth/token",
                params={"client_id": client_id, "client_secret": client_secret},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("code") == 200:
                        return data["data"]["token"]
    except Exception as e:
        logger.error(f"Get qinglong token error: {e}")
    return None

async def find_cron_id(config, token):
    script_name = config.get("script", "")
    if not script_name or not token:
        return None
    try:
        qinglong_url = config.get("qinglong_url", "http://qinglong:5700")
        headers = {"Authorization": f"Bearer {token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{qinglong_url}/open/crons",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    crons = data.get("data", {}).get("data", [])
                    for cron in crons:
                        command = cron.get("command", "")
                        cron_id = cron.get("id")
                        if script_name in command and cron_id:
                            return cron_id
    except Exception as e:
        logger.error(f"Find cron error: {e}")
    return None

async def notify_qinglong(token, cron_id):
    try:
        config = load_config()
        qinglong_url = config.get("qinglong_url", "http://qinglong:5700")
        headers = {"Authorization": f"Bearer {token}"}
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{qinglong_url}/open/crons/run",
                headers=headers,
                json=[cron_id],
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("code") == 200:
                        logger.info(f"Notify qinglong success: cron_id={cron_id}")
                        return True
                    else:
                        logger.error(f"Notify qinglong failed: {data}")
    except Exception as e:
        logger.error(f"Notify qinglong error: {e}")
    return False

def match_listener(message, config):
    for listener in config.get("listeners", []):
        if not listener.get("enabled", True):
            continue
        chat_type = listener.get("chat_type", "private")
        keyword = listener.get("keyword", "")
        chat_id = listener.get("chat_id")
        sender_id = listener.get("sender_id")
        if chat_type == "private" and not message.is_private:
            continue
        if chat_type == "group" and message.is_private:
            continue
        if chat_id and message.chat_id != chat_id:
            continue
        if sender_id and message.sender_id != sender_id:
            continue
        if keyword and keyword not in (message.text or ""):
            continue
        return listener
    return None

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, bytes):
            return list(obj)
        if isinstance(obj, TLObject):
            return obj.to_dict()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        return super().default(obj)

async def update_profile(**kwargs):
    try:
        valid_args = ["about", "first_name", "last_name"]
        request_args = {k: v for k, v in kwargs.items() if k in valid_args}
        if not request_args:
            return "No valid parameters"
        await client(functions.account.UpdateProfileRequest(**request_args))
        return "Profile updated"
    except Exception as e:
        logger.error(f"Error in update_profile: {e}")
        raise e

async def send_file(entity, file, caption=""):
    try:
        IMAGES_DIR = "/app/images"
        if isinstance(file, str):
            if file.startswith("http://") or file.startswith("https://"):
                pass
            elif not os.path.exists(file):
                file_path = os.path.join(IMAGES_DIR, file)
                if os.path.exists(file_path):
                    file = file_path
                else:
                    file_path = os.path.join(IMAGES_DIR, os.path.basename(file))
                    if os.path.exists(file_path):
                        file = file_path
        await client.send_file(entity, file, caption=caption)
        return "File sent"
    except Exception as e:
        logger.error(f"Error in send_file: {e}")
        raise e

CUSTOM_METHODS = {"update_profile": update_profile, "send_file": send_file}

async def handle_call(request):
    try:
        data = await request.json()
        method_name = data.get("method")
        params = data.get("params", {})
        if not method_name:
            return web.json_response({"status": "error", "error": "Method name is required"}, status=400)
        if method_name in CUSTOM_METHODS:
            method = CUSTOM_METHODS[method_name]
            result = await method(**params) if asyncio.iscoroutinefunction(method) else method(**params)
        elif hasattr(client, method_name):
            method = getattr(client, method_name)
            if not callable(method):
                return web.json_response({"status": "error", "error": f"{method_name} not callable"}, status=400)
            result = await method(**params) if asyncio.iscoroutinefunction(method) else method(**params)
        else:
            return web.json_response({"status": "error", "error": f"Method {method_name} not found"}, status=404)
        return web.json_response({"status": "success", "result": result}, dumps=lambda x: json.dumps(x, cls=DateTimeEncoder))
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return web.json_response({"status": "error", "error": str(e)}, status=500)

@client.on(events.NewMessage)
async def on_new_message(event):
    try:
        if event.message.out:
            return
        config = load_config()
        listener = match_listener(event.message, config)
        if listener:
            listener_name = listener.get("name", "")
            logger.info(f"Listener matched: {listener_name}")
            token = await get_qinglong_token(config)
            if token:
                cron_id = await find_cron_id(config, token)
                if cron_id:
                    await notify_qinglong(token, cron_id)
                else:
                    logger.error("Cron not found")
            else:
                logger.error("Token error")
    except Exception as e:
        logger.error(f"Message handler error: {e}")

async def init_app():
    app = web.Application()
    app.router.add_post("/api/call", handle_call)
    return app

async def start_client():
    logger.info("Starting Telegram Client...")
    if os.path.exists(session_file):
        await client.start()
    else:
        PHONE_NUMBER = os.getenv("PHONE_NUMBER")
        await client.start(phone=PHONE_NUMBER)
    logger.info("Telegram Client started and authorized.")

async def main():
    await start_client()
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    logger.info(f"Starting HTTP server on port {HTTP_PORT}")
    await site.start()
    try:
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Client disconnected: {e}")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
