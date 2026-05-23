import os
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiohttp import web
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Salom! 🤖\nMenga TikTok, Instagram, YouTube, Facebook yoki Twitter (X) havolasini yuboring."
    )


@dp.message(F.text)
async def link_handler(message: types.Message):
    url = message.text.strip()

    # Yangi tarmoqlarni (facebook va twitter/x) filtrga qo'shdik
    valid_domains = [
        "tiktok.com", "instagram.com", 
        "youtube.com", "youtu.be", 
        "facebook.com", "fb.watch",
        "twitter.com", "x.com"
    ]

    if not any(domain in url for domain in valid_domains):
        await message.answer("Iltimos, faqat TikTok, Instagram, YouTube, Facebook yoki Twitter havolalarini yuboring! ❌")
        return

    status_message = await message.answer("Video yuklab olinmoqda... ⏳")
    video_filename = f"{DOWNLOAD_DIR}/{message.from_user.id}_{message.message_id}.mp4"

    # Bloklarni aylanib o'tish uchun eng optimal va mukammal sozlamalar
    ydl_opts = {
        "outtmpl": video_filename,
        # Eng yuqori video va audio sifatni oladi, ffmpeg esa ularni avtomatik mp4 qilib birlashtiradi
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", 
        "cookiefile": "cookies.txt",
        "no_warnings": True,
        "quiet": True,
        "source_address": "0.0.0.0",
        "nocheckcertificate": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
    }

    try:
        # Kod bloklanib qolmasligi uchun asinxron oqimga chiqaramiz
        loop = asyncio.get_event_loop()
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        await loop.run_in_executor(None, download)

        # Fayl yuklandimi yoki yo'q tekshiramiz
        if os.path.exists(video_filename):
            video_file = FSInputFile(video_filename)
            await message.reply_video(video=video_file, caption="Video muvaffaqiyatli yuklandi! 🎉")
            os.remove(video_filename)  # Serverda joy to'lmasligi uchun faylni o'chiramiz
        else:
            await message.answer("Videoni yuklashda xatolik yuz berdi. Havolani tekshirib ko'ring. ❌")

    except Exception as e:
        print(f"Xatolik: {e}")
        await message.answer("Xatolik yuz berdi. Bu video formati qo'llab-quvvatlanmasligi mumkin. ⚠️")

    finally:
        try:
            await status_message.delete()
        except:
            pass


# Render serverini uyg'oq tutish uchun kichik veb-interfeys
async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    # Render portini tinglash (fonda ishlaydi va uyquga ketishdan asraydi)
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    asyncio.create_task(site.start())

    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
