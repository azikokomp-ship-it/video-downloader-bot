import os
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Salom! 🤖\nMenga TikTok, Instagram yoki YouTube Shorts havolasini yuboring."
    )


@dp.message(F.text)
async def link_handler(message: types.Message):
    url = message.text.strip()

    if not ("tiktok.com" in url or "instagram.com" in url or "youtube.com" in url or "youtu.be" in url):
        await message.answer("Iltimos, faqat TikTok, Instagram yoki YouTube havolalarini yuboring! ❌")
        return

    status_message = await message.answer("Video yuklab olinmoqda... ⏳")
    video_filename = f"{DOWNLOAD_DIR}/{message.from_user.id}_{message.message_id}.mp4"

    # TikTok va Instagram bloklarini aylanib o'tish uchun eng kuchli sozlamalar
    ydl_opts = {
        "outtmpl": video_filename,
        "format": "best[ext=mp4]/best",
        "no_warnings": True,
        "quiet": True,
        # Brauzer bo'lib ko'rinish (User-Agent)
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
        if os.path.exists(video_filename) and os.path.getsize(video_filename) > 0:
            video_file = FSInputFile(video_filename)
            await message.answer_video(video=video_file, caption="Siz so'ragan video tayyor! ✅")
            os.remove(video_filename)
        else:
            await message.answer("Videoni serverga yuklashda muammo bo'ldi (fayl topilmadi). ❌")

    except Exception as e:
        # Terminalga aniq xatolikni chiqarish (buni ko'rib muammoni bilsa bo'ladi)
        print(f"\n[XATOLIK YUZ BERDI]: {e}\n")
        await message.answer("Kechirasiz, ushbu videoni yuklab bo'lmadi. ❌")
        if os.path.exists(video_filename):
            os.remove(video_filename)
            
    finally:
        try:
            await status_message.delete()
        except:
            pass


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())