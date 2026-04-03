import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from playwright.async_api import async_playwright
from aiohttp import web

# Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
URL = "https://ielts.idp.com/results/check-your-result"

# Credentials
NAME = "TOSHAK"
SURNAME = "PAL"
DOB = "06/04/2007"
PASSWORD = "NO AD317728"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def delete_message_after(chat_id: int, message_id: int, delay: int = 600):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception as e:
        logger.error(f"Failed to delete message: {e}")

async def check_result():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        screenshot_path = f"screenshot_{int(datetime.now().timestamp())}.png"
        
        try:
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # Fill form
            await page.fill('input[name="givenName"]', NAME)
            await page.fill('input[name="familyName"]', SURNAME)
            await page.fill('input[name="dob"]', DOB)
            await page.fill('input[name="passportNumber"]', PASSWORD)
            
            # Submit
            await page.click('button[type="submit"]')
            await asyncio.sleep(5)
            
            await page.screenshot(path=screenshot_path, full_page=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True, screenshot_path, timestamp, "Check completed."
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            return False, None, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(e)
        finally:
            await browser.close()

async def send_update(chat_id, success, screenshot, timestamp, message):
    try:
        if success and screenshot:
            msg = await bot.send_photo(
                chat_id=chat_id,
                photo=FSInputFile(screenshot),
                caption=f"IELTS Result Check\nTimestamp: {timestamp}\nStatus: {message}"
            )
            os.remove(screenshot)
        else:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=f"IELTS Result Check FAILED\nTimestamp: {timestamp}\nReason: {message}"
            )
        
        asyncio.create_task(delete_message_after(chat_id, msg.message_id))
    except Exception as e:
        logger.error(f"Failed to send update: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Check Result Now", callback_data="check_now")]
    ])
    await message.answer("IELTS Result Bot is active.", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "check_now")
async def process_callback_check_now(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id, text="Checking results...")
    success, screenshot, timestamp, msg = await check_result()
    await send_update(callback_query.from_user.id, success, screenshot, timestamp, msg)

async def scheduler():
    while True:
        if CHAT_ID:
            success, screenshot, timestamp, msg = await check_result()
            await send_update(CHAT_ID, success, screenshot, timestamp, msg)
        await asyncio.sleep(3 * 3600)

async def handle_ping(request):
    return web.Response(text="Bot is alive", status=200)

async def main():
    # HTTP server for ping
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 3000)
    
    # Start tasks
    asyncio.create_task(site.start())
    asyncio.create_task(scheduler())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
