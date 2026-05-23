import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiohttp import web
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# yt-dlp uchun eng yangi va ishonchli sozlamalar
def get_ydl_opts(video_filename: str) -> dict:
    opts = {
        "outtmpl": video_filename,
        # Avval audio+video, keyin fallback
        "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "source_address": "0.0.0.0",

        # ✅ ASOSIY YECHIM: YouTube blokdan o'tish
        "extractor_args": {
            "youtube": {
                # po_token o'rniga web_creator client ishlatamiz (2024-2025 da eng ishonchli)
                "player_client": ["web_creator", "android", "web"],
                "player_skip": ["webpage"],
            }
        },

        # Bot emasligimizni ko'rsatish uchun real browser headerlar
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Sec-Fetch-Mode": "navigate",
        },

        # Tarmoq xatoliklarida qayta urinish
        "retries": 3,
        "fragment_retries": 3,
        "file_access_retries": 3,

        # Katta fayllar uchun (Telegram 50MB limit)
        "max_filesize": 45 * 1024 * 1024,  # 45 MB
    }

    # Agar cookies.txt fayli mavjud bo'lsa, ishlatamiz
    # (Brauzerdan export qilish: chrome extension "Get cookies.txt LOCALLY")
    cookies_path = os.path.join(os.path.dirname(__file__), "cookies.txt")
    if os.path.exists(cookies_path):
        opts["cookiefile"] = cookies_path
        logger.info("cookies.txt topildi, ishlatilmoqda")

    return opts


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Salom! 🤖\n"
        "Menga TikTok, Instagram, YouTube, Facebook yoki Twitter (X) havolasini yuboring.\n\n"
        "⚠️ YouTube videolari max 45MB bo'lishi kerak."
    )


@dp.message(F.text)
async def link_handler(message: types.Message):
    url = message.text.strip()

    valid_domains = [
        "tiktok.com", "instagram.com",
        "youtube.com", "youtu.be",
        "facebook.com", "fb.watch",
        "twitter.com", "x.com",
    ]

    if not any(domain in url for domain in valid_domains):
        await message.answer(
            "Iltimos, faqat TikTok, Instagram, YouTube, Facebook yoki Twitter havolalarini yuboring! ❌"
        )
        return

    status_message = await message.answer("Video yuklab olinmoqda... ⏳")
    video_filename = f"{DOWNLOAD_DIR}/{message.from_user.id}_{message.message_id}.mp4"

    try:
        loop = asyncio.get_event_loop()
        ydl_opts = get_ydl_opts(video_filename)

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info

        info = await loop.run_in_executor(None, download)

        # ffmpeg merge qilganda fayl nomi o'zgarishi mumkin, tekshiramiz
        actual_file = video_filename
        if not os.path.exists(actual_file):
            # Ba'zan .webm yoki boshqa kengaytma bilan saqlanadi
            base = video_filename.rsplit(".", 1)[0]
            for ext in ["mp4", "webm", "mkv", "avi"]:
                candidate = f"{base}.{ext}"
                if os.path.exists(candidate):
                    actual_file = candidate
                    break

        if os.path.exists(actual_file):
            file_size = os.path.getsize(actual_file)
            logger.info(f"Fayl yuklanди: {actual_file}, hajmi: {file_size / 1024 / 1024:.1f} MB")

            if file_size > 50 * 1024 * 1024:
                await message.answer(
                    "❌ Video Telegram limitidan (50MB) katta. "
                    "Qisqaroq yoki sifati past video sinab ko'ring."
                )
            else:
                video_file = FSInputFile(actual_file)
                title = info.get("title", "") if info else ""
                caption = f"🎬 {title[:200]}" if title else "Video muvaffaqiyatli yuklandi! 🎉"
                await message.reply_video(video=video_file, caption=caption)
            os.remove(actual_file)
        else:
            await message.answer(
                "❌ Videoni yuklashda xatolik yuz berdi.\n"
                "Havolani tekshirib ko'ring yoki boshqa video sinab ko'ring."
            )

    except yt_dlp.utils.DownloadError as e:
        err = str(e).lower()
        logger.error(f"yt-dlp xatolik: {e}")

        if "sign in" in err or "login" in err or "bot" in err:
            await message.answer(
                "⚠️ YouTube bu videoni cheklagan.\n"
                "Sabab: server IP bloklanishi yoki yosh cheklovi.\n"
                "Boshqa video sinab ko'ring."
            )
        elif "private" in err:
            await message.answer("❌ Bu video xususiy (private). Ochiq videoni yuboring.")
        elif "not available" in err:
            await message.answer("❌ Bu video mavjud emas yoki o'chirilgan.")
        elif "too large" in err or "filesize" in err:
            await message.answer("❌ Video juda katta (50MB limitdan oshadi).")
        else:
            await message.answer(
                f"⚠️ Yuklab bo'lmadi.\n"
                "TikTok, Instagram yoki boshqa saytdan video sinab ko'ring."
            )

    except Exception as e:
        logger.error(f"Kutilmagan xatolik: {e}", exc_info=True)
        await message.answer("⚠️ Xatolik yuz berdi. Keyinroq qayta urinib ko'ring.")

    finally:
        try:
            await status_message.delete()
        except Exception:
            pass
        # Qolgan vaqtinchalik fayllarni tozalash
        base = video_filename.rsplit(".", 1)[0]
        for ext in ["mp4", "webm", "mkv", "avi", "part"]:
            f = f"{base}.{ext}"
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass


# Render uyg'oq tutish
async def handle(request):
    return web.Response(text="Bot is running!")


async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    asyncio.create_task(site.start())
    logger.info("Bot ishga tushdi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
