from datetime import datetime
from typing import Optional, Dict
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties

from app.config.settings import get_settings
from app.utils.logger import logger
from app.utils.validators import utc_now
from app.database.database import get_session
from app.database.repositories import (
    PostRepository,
    SourceRepository,
    SystemLogRepository
)
from app.telegram.admin import admin_router, is_authorized_admin
from app.telegram.publisher import TelegramPublisher

settings = get_settings()
bot_router = Router(name="bot_router")

# Track execution stats
STATE = {
    "is_paused": False,
    "last_checks": {
        "MLBB": None,
        "MPL ID": None,
        "MPL PH": None,
        "Esports": None
    }
}


def time_ago_str(dt: Optional[datetime]) -> str:
    if not dt:
        return "Never"
    diff = int((utc_now() - dt).total_seconds())
    if diff < 60:
        return f"{diff}s ago"
    minutes = diff // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    return f"{hours}h ago"


@bot_router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    is_adm = await is_authorized_admin(user_id)
    text = (
        "👋 <b>Assalomu alaykum! MLBB News AI Agent botiga xush kelibsiz!</b>\n\n"
        "Men Mobile Legends: Bang Bang bo‘yicha rasmiy yangiliklar, patch notes, "
        "qahramonlar balansi, yangi skinlar va MPL ID/PH o‘yin natijalarini kuzatib boruvchi AI agentman.\n\n"
        f"🆔 <b>Sizning Telegram ID:</b> <code>{user_id}</code>\n\n"
        "📌 <b>Asosiy buyruqlar:</b>\n"
        "/status — Tizim holatini ko‘rish\n"
        "/latest — So‘nggi yangiliklar\n"
        "/test — Test xabarni tekshirish\n"
    )
    if is_adm:
        text += (
            "\n👑 <b>Admin buyruqlari:</b>\n"
            "/admins — Barcha administratorlar ro‘yxati\n"
            "/addadmin &lt;id&gt; — Yangi admin qo‘shish\n"
            "/deladmin &lt;id&gt; — Adminni o‘chirish\n"
            "/newpatch — Yangi Patch posti va infografikasini yaratish\n"
            "/fastpatch — Patchni to‘g‘ridan-to‘g‘ri kanalga chiqarish\n"
            "/check_news — Yangiliklarni zudlik bilan tekshirish (05:00 cron)\n"
            "/today — Bugungi o‘yinlar dasturi va markaziy bahs anonsi\n"
            "/today_id — MPL ID bugungi matchday kartasi va AI tahlili\n"
            "/today_ph — MPL PH bugungi matchday kartasi va AI tahlili\n"
            "/mpl_id — Liquipedia rasmiy MPL ID jadvali va kartasi\n"
            "/mpl_ph — Liquipedia rasmiy MPL PH jadvali va kartasi\n"
            "/pause — Avtomatik yangilik yig‘ishni to‘xtatish\n"
            "/resume — Yangilik yig‘ishni davom ettirish\n"
            "/send &lt;id&gt; — Postni kanalga chiqarish\n"
            "/fun — MLBB fakt yoki hazil postini zudlik bilan yaratish\n"
            "/channels — Ulangan kanallar va ularni tekshirish\n"
        )
    await message.reply(text, parse_mode="HTML")


@bot_router.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message)


@bot_router.message(Command("status"))
async def cmd_status(message: Message):
    async with get_session() as session:
        posts_today = await PostRepository.count_today_posts(session)
        errors_today = await SystemLogRepository.count_errors_today(session)

    status_icon = "⏸ Paused" if STATE["is_paused"] else "🟢 Online"
    mlbb_ago = time_ago_str(STATE["last_checks"]["MLBB"])
    mpl_id_ago = time_ago_str(STATE["last_checks"]["MPL ID"])
    mpl_ph_ago = time_ago_str(STATE["last_checks"]["MPL PH"])

    status_report = (
        f"🤖 <b>MLBB NEWS AGENT</b>\n"
        f"Status: {status_icon}\n"
        f"Mode: {'Auto Publish' if settings.AUTO_PUBLISH else f'Admin Approval (Avto-uzatish: {settings.APPROVAL_TIMEOUT_MINUTES} daq)'}\n\n"
        f"⏰ <b>Jadvallar:</b>\n"
        f"• Ertalabki yangiliklar: Har kuni {settings.DAILY_NEWS_HOUR:02d}:{settings.DAILY_NEWS_MINUTE:02d} (max {settings.MAX_DAILY_NEWS_COUNT} ta)\n"
        f"• Jonli o‘yinlar: Har {settings.CHECK_INTERVAL_MPL_ID_MIN} daqiqada (Oldin + Natija)\n\n"
        f"Oxirgi tekshiruvlar:\n"
        f"MLBB: {mlbb_ago}\n"
        f"MPL ID: {mpl_id_ago}\n"
        f"MPL PH: {mpl_ph_ago}\n\n"
        f"Bugungi postlar: {posts_today}\n"
        f"Xatoliklar: {errors_today}"
    )
    await message.reply(status_report, parse_mode="HTML")


@bot_router.message(Command("latest"))
async def cmd_latest(message: Message):
    async with get_session() as session:
        posts = await PostRepository.get_latest_posts(session, limit=5)

    if not posts:
        await message.reply("Hozircha saqlangan postlar mavjud emas.")
        return

    lines = ["📋 <b>So‘nggi 5 ta yangilik/post:</b>\n"]
    for p in posts:
        pub = p.published_at.strftime("%Y-%m-%d %H:%M") if p.published_at else "Chiqarilmagan"
        lines.append(f"#{p.id} [{p.category}] <b>{p.title[:40]}</b>\nHolat: {p.status} | Sana: {pub}\n")

    await message.reply("\n".join(lines), parse_mode="HTML")


@bot_router.message(Command("channels"))
async def cmd_channels(message: Message, bot: Bot):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Faqat admin uchun ruxsat berilgan.")
        return

    channel_ids = settings.channel_ids
    if not channel_ids:
        await message.reply(
            "⚠️ <b>Hozircha hech qanday kanal ulanmagan.</b>\n\n"
            ".env fayliga <code>TELEGRAM_CHANNEL_ID=-100xxxxxxxxxx</code> ni kiriting.",
            parse_mode="HTML"
        )
        return

    lines = ["📢 <b>Ulangan Telegram Kanallar:</b>\n"]
    for idx, cid in enumerate(channel_ids, 1):
        if str(bot.id) in str(cid):
            lines.append(f"{idx}. ⚠️ <code>{cid}</code> — <i>Xatolik: Bu botning o‘z ID si! Kanal ID si -100 bilan boshlanishi kerak.</i>\n")
            continue
        try:
            chat = await bot.get_chat(cid)
            lines.append(f"{idx}. ✅ <b>{chat.title}</b> (<code>{cid}</code>)\n   Turi: {chat.type} | Ulanish: Muvaffaqiyatli\n")
        except Exception as e:
            lines.append(f"{idx}. ❌ <code>{cid}</code> — <i>Ulanib bo‘lmadi ({e}). Botingiz kanalda Admin ekanligini tekshiring!</i>\n")

    lines.append("💡 <i>Yangi kanal qo‘shish uchun: yangi kanaldan istalgan postni ushbu botga forward qiling yoki uning ID sini .env dagi TELEGRAM_CHANNEL_ID ga vergul bilan qo‘shing.</i>")
    await message.reply("\n".join(lines), parse_mode="HTML")


@bot_router.message(F.forward_from_chat)
async def handle_forwarded_chat(message: Message, bot: Bot):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        return

    chat = message.forward_from_chat
    if not chat:
        return

    chat_type = chat.type or "noma'lum"
    title = chat.title or chat.username or "Nomsiz"
    lines = [
        f"📢 <b>Telegram {chat_type.capitalize()} aniqlandi!</b>\n",
        f"📌 Nomi: <b>{title}</b>",
        f"🆔 Kanal ID: <code>{chat.id}</code>",
    ]
    if chat.username:
        lines.append(f"🔗 Username: @{chat.username}")

    lines.append(
        "\n✅ <b>Ushbu kanalga postlar chiqarish uchun:</b>\n"
        "1. Botingizni ushbu kanalga <b>Admin</b> (post joylash huquqi bilan) qilib qo‘shing.\n"
        "2. <code>.env</code> faylidagi <code>TELEGRAM_CHANNEL_ID</code> ga vergul bilan qo‘shing:\n"
        f"<code>TELEGRAM_CHANNEL_ID={settings.TELEGRAM_CHANNEL_ID}, {chat.id}</code>\n\n"
        "Shundan so‘ng bot avtomatik ravishda yangiliklarni ushbu kanalga ham yuboradi!"
    )
    await message.reply("\n".join(lines), parse_mode="HTML")


@bot_router.message(F.text.regexp(r"^-?\d{8,15}$"))
async def handle_numeric_id_query(message: Message, bot: Bot):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        return

    raw_id = (message.text or "").strip()
    if str(bot.id) in raw_id:
        await message.reply(
            f"⚠️ <code>{raw_id}</code> — <b>Bu sizning botingizning o‘z ID raqami!</b>\n\n"
            "Bot o‘z-o‘ziga kanal sifatida xabar yubora olmaydi.\n"
            "Telegram kanal ID lari har doim <code>-100</code> bilan boshlanadi (masalan: <code>-1002503816147</code>).\n\n"
            "💡 <b>Kanal ID sini bilishning oson yo‘li:</b>\n"
            "Kanalga botni Admin qilib qo‘shing va o‘sha kanaldan istalgan postni ushbu botga forward qiling!",
            parse_mode="HTML"
        )
        return

    cid = f"-100{raw_id}" if not raw_id.startswith("-") else raw_id
    try:
        chat = await bot.get_chat(cid)
        await message.reply(
            f"✅ <b>Kanal topildi!</b>\n"
            f"Nomi: <b>{chat.title}</b>\n"
            f"ID: <code>{chat.id}</code>\n\n"
            f"Kanalni ulash uchun: <code>.env</code> dagi <code>TELEGRAM_CHANNEL_ID</code> ga mana shu ID ni kiriting.",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.reply(
            f"ℹ️ <b>Kiritilgan ID:</b> <code>{raw_id}</code>\n"
            f"Telegram serveri ushbu chatni topa olmadi (yoki bot kanalda admin emas).\n\n"
            "💡 <b>Maslahat:</b> Botingizni kanalga Admin qilib qo‘shing va kanaldan birorta xabarni ushbu botga forward qiling.",
            parse_mode="HTML"
        )


@bot_router.message(Command("pause"))
async def cmd_pause(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Faqat admin uchun ruxsat berilgan.")
        return
    STATE["is_paused"] = True
    await message.reply("⏸ Avtomatik scheduler vaqtincha to‘xtatildi.")


@bot_router.message(Command("resume"))
async def cmd_resume(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Faqat admin uchun ruxsat berilgan.")
        return
    STATE["is_paused"] = False
    await message.reply("▶️ Avtomatik scheduler qayta ishga tushirildi.")


@bot_router.message(Command("check_news"))
async def cmd_check_news(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Faqat admin uchun ruxsat berilgan.")
        return
    await message.reply("🔄 <i>MLBB Patch notes va yangiliklar tekshirilmoqda (qat'iy yangilik tekshiruvi: faqat so‘nggi 24 soat ichida chiqqan haqiqiy yangi xabarlar)...</i>", parse_mode="HTML")
    from app.scheduler.jobs import NewsJobManager
    manager = NewsJobManager(bot=message.bot)
    count = await manager.job_mlbb_official()
    if count and count > 0:
        await message.reply(f"✅ <b>Tekshiruv yakunlandi:</b> {count} ta yangi haqiqiy yangilik/patch aniqlandi va post yaratildi.", parse_mode="HTML")
    else:
        await message.reply(
            "✅ <b>Tekshiruv yakunlandi:</b> Hozircha so‘nggi 24 soat ichida chiqqan yangi patch yoki yangilik topilmadi.\n"
            "<i>(Eski va muddati o‘tgan xabarlar kanalga kirmasligi uchun qat'iy tekshiruvdan o‘tkazildi va filtrlandi).</i>",
            parse_mode="HTML"
        )


@bot_router.message(Command("check_matches"))
async def cmd_check_matches(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Faqat admin uchun ruxsat berilgan.")
        return
    await message.reply("🔄 MPL ID va MPL PH o‘yinlari tekshirilmoqda...")
    from app.scheduler.jobs import NewsJobManager
    manager = NewsJobManager(bot=message.bot)
    await manager.job_check_matches()
    await message.reply("✅ O‘yinlar tekshiruvi yakunlandi.")


@bot_router.message(Command("mpl_id"))
async def cmd_mpl_id(message: Message, bot: Bot):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Faqat admin uchun ruxsat berilgan.")
        return

    await message.reply("🔄 <b>Liquipedia</b> dan MPL Indonesia Season 18 jadvallari va natijalari olinmoqda...", parse_mode="HTML")
    from app.services.liquipedia_parser import LiquipediaParserService, compute_countdown
    from app.media.image_processor import ImageProcessor
    from aiogram.types import BufferedInputFile

    try:
        matches = await LiquipediaParserService.fetch_and_parse_mpl_id(season=18)
        if not matches:
            from app.services.mpl_parser import MPLParserService
            matches = await MPLParserService.fetch_and_parse_mpl_id()

        if not matches:
            await message.reply("⚠️ Liquipedia dan o‘yinlar topilmadi.")
            return

        upcoming = [m for m in matches if m.status == "upcoming"]
        finished = [m for m in matches if m.status == "finished"]

        text_lines = [
            f"🇮🇩 <b>MPL ID SEASON 18 — LIQUIPEDIA JADVALI</b>\n",
            f"📊 Jami o‘yinlar: <b>{len(matches)}</b> ta | Kutilayotgan: <b>{len(upcoming)}</b> | Tugagan: <b>{len(finished)}</b>\n"
        ]

        if upcoming:
            text_lines.append("⏳ <b>Yaqinlashib kelayotgan o‘yinlar:</b>")
            for m in upcoming[:4]:
                dt_str = m.date
                text_lines.append(f"• <b>{m.team_a}</b> vs <b>{m.team_b}</b> | 📅 {dt_str} {m.time} ({m.week}-hafta)")
            text_lines.append("")

        if finished:
            text_lines.append("🏆 <b>So‘nggi o‘yin natijalari:</b>")
            for m in finished[-2:]:
                sc = f"{m.score_a} : {m.score_b}" if m.score_a is not None else "Tugagan"
                mvp_str = f" (MVP: {m.mvp})" if m.mvp else ""
                text_lines.append(f"• <b>{m.team_a}</b> {sc} <b>{m.team_b}</b>{mvp_str} | {m.week}-hafta")

        text_lines.append("\n💡 <i>O‘yin kartasini avtomatik chiqarish uchun /check_matches buyrug‘idan foydalaning.</i>")
        report_text = "\n".join(text_lines)

        from app.utils.html_utils import safe_trim_html

        target_match = upcoming[0] if upcoming else (finished[-1] if finished else None)
        if target_match:
            match_dict = {
                "league": "MPL ID",
                "team_a": target_match.team_a,
                "team_b": target_match.team_b,
                "score_a": target_match.score_a,
                "score_b": target_match.score_b,
                "status": "FINAL" if target_match.status == "finished" else "UPCOMING",
                "mvp": target_match.mvp,
                "date": target_match.date,
                "time": target_match.time,
                "week": target_match.week,
                "season": target_match.season,
                "series": target_match.series
            }
            if target_match.status == "finished":
                img_bytes = ImageProcessor.render_match_result(match_dict)
            else:
                img_bytes = ImageProcessor.render_match_upcoming(match_dict)

            photo = BufferedInputFile(img_bytes, filename="mpl_id_preview.png")
            safe_caption = safe_trim_html(report_text, max_len=1020)
            try:
                await message.reply_photo(photo=photo, caption=safe_caption, parse_mode="HTML")
            except Exception as photo_err:
                logger.warning(f"Reply photo failed ({photo_err}), sending fallback")
                brief_cap = f"🇮🇩 <b>MPL ID — {target_match.team_a} vs {target_match.team_b}</b>"
                await message.reply_photo(photo=photo, caption=brief_cap, parse_mode="HTML")
                await message.reply(safe_trim_html(report_text, max_len=4000), parse_mode="HTML")
        else:
            await message.reply(safe_trim_html(report_text, max_len=4000), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in cmd_mpl_id: {e}", exc_info=True)
        await message.reply(f"❌ Xatolik yuz berdi: {e}")


@bot_router.message(Command("mpl_ph"))
async def cmd_mpl_ph(message: Message, bot: Bot):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Faqat admin uchun ruxsat berilgan.")
        return

    await message.reply("🔄 <b>Liquipedia</b> dan MPL Philippines Season 18 jadvallari va natijalari olinmoqda...", parse_mode="HTML")
    from app.services.liquipedia_parser import LiquipediaParserService, compute_countdown
    from app.media.image_processor import ImageProcessor
    from aiogram.types import BufferedInputFile

    try:
        matches = await LiquipediaParserService.fetch_and_parse_mpl_ph(season=18)
        if not matches:
            from app.services.mpl_parser import MPLParserService
            matches = await MPLParserService.fetch_and_parse_mpl_ph()

        if not matches:
            await message.reply("⚠️ Liquipedia dan o‘yinlar topilmadi.")
            return

        upcoming = [m for m in matches if m.status == "upcoming"]
        finished = [m for m in matches if m.status == "finished"]

        text_lines = [
            f"🇵🇭 <b>MPL PH SEASON 18 — LIQUIPEDIA JADVALI</b>\n",
            f"📊 Jami o‘yinlar: <b>{len(matches)}</b> ta | Kutilayotgan: <b>{len(upcoming)}</b> | Tugagan: <b>{len(finished)}</b>\n"
        ]

        if upcoming:
            text_lines.append("⏳ <b>Yaqinlashib kelayotgan o‘yinlar:</b>")
            for m in upcoming[:4]:
                dt_str = m.date
                text_lines.append(f"• <b>{m.team_a}</b> vs <b>{m.team_b}</b> | 📅 {dt_str} {m.time} ({m.week}-hafta)")
            text_lines.append("")

        if finished:
            text_lines.append("🏆 <b>So‘nggi o‘yin natijalari:</b>")
            for m in finished[-2:]:
                sc = f"{m.score_a} : {m.score_b}" if m.score_a is not None else "Tugagan"
                mvp_str = f" (MVP: {m.mvp})" if m.mvp else ""
                text_lines.append(f"• <b>{m.team_a}</b> {sc} <b>{m.team_b}</b>{mvp_str} | {m.week}-hafta")

        text_lines.append("\n💡 <i>O‘yin kartasini avtomatik chiqarish uchun /check_matches buyrug‘idan foydalaning.</i>")
        report_text = "\n".join(text_lines)

        from app.utils.html_utils import safe_trim_html

        target_match = upcoming[0] if upcoming else (finished[-1] if finished else None)
        if target_match:
            match_dict = {
                "league": "MPL PH",
                "team_a": target_match.team_a,
                "team_b": target_match.team_b,
                "score_a": target_match.score_a,
                "score_b": target_match.score_b,
                "status": "FINAL" if target_match.status == "finished" else "UPCOMING",
                "mvp": target_match.mvp,
                "date": target_match.date,
                "time": target_match.time,
                "week": target_match.week,
                "season": target_match.season,
                "series": target_match.series
            }
            if target_match.status == "finished":
                img_bytes = ImageProcessor.render_match_result(match_dict)
            else:
                img_bytes = ImageProcessor.render_match_upcoming(match_dict)

            photo = BufferedInputFile(img_bytes, filename="mpl_ph_preview.png")
            safe_caption = safe_trim_html(report_text, max_len=1020)
            try:
                await message.reply_photo(photo=photo, caption=safe_caption, parse_mode="HTML")
            except Exception as photo_err:
                logger.warning(f"Reply photo failed ({photo_err}), sending fallback")
                brief_cap = f"🇵🇭 <b>MPL PH — {target_match.team_a} vs {target_match.team_b}</b>"
                await message.reply_photo(photo=photo, caption=brief_cap, parse_mode="HTML")
                await message.reply(safe_trim_html(report_text, max_len=4000), parse_mode="HTML")
        else:
            await message.reply(safe_trim_html(report_text, max_len=4000), parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in cmd_mpl_ph: {e}", exc_info=True)
        await message.reply(f"❌ Xatolik yuz berdi: {e}")


@bot_router.message(Command("today"))
@bot_router.message(Command("matchday"))
async def cmd_today_all(message: Message, bot: Bot):
    """
    Shows today's matchday status or schedule for both MPL ID and MPL PH.
    """
    from app.services.matchday_service import MatchdayService

    today = MatchdayService.get_current_date_tashkent()
    today_display = MatchdayService.format_uzbek_date_header(today)

    from app.ai.analyzer import AIAnalyzer
    analyzer = AIAnalyzer()

    res_id = await MatchdayService.generate_matchday_post("MPL ID", analyzer=analyzer)
    res_ph = await MatchdayService.generate_matchday_post("MPL PH", analyzer=analyzer)

    id_rest = res_id.get("is_rest_day", False)
    ph_rest = res_ph.get("is_rest_day", False)

    if id_rest and ph_rest:
        # Both leagues are having a rest day!
        humor = await MatchdayService.generate_rest_day_humor(
            league="MPL",
            today_date=today,
            next_matchday=res_id.get("next_matchday"),
            analyzer=analyzer
        )

        lines = [
            f"🏖 <b>BUGUN TANAFFUS — MPL ID & MPL PH!</b>",
            f"🗓 <i>Sana: {today_display}</i>",
            "",
            f"<i>{humor}</i>",
            "",
            "📅 <b>KEYINGI O‘YINLAR:</b>"
        ]

        next_id = res_id.get("next_matchday")
        if next_id and next_id.get("matches"):
            lines.append(f"\n🇮🇩 <b>MPL ID ({next_id.get('date_display')}):</b>")
            for m in next_id["matches"]:
                m_time = m.get("time", "").split(" / ")[0].replace("(UZ)", "").strip()
                lines.append(f"• <b>{m['team_a']} vs {m['team_b']}</b> — ⏰ {m_time}")

        next_ph = res_ph.get("next_matchday")
        if next_ph and next_ph.get("matches"):
            lines.append(f"\n🇵🇭 <b>MPL PH ({next_ph.get('date_display')}):</b>")
            for m in next_ph["matches"]:
                m_time = m.get("time", "").split(" / ")[0].replace("(UZ)", "").strip()
                lines.append(f"• <b>{m['team_a']} vs {m['team_b']}</b> — ⏰ {m_time}")

        lines.append("\n#MPLID #MPLPH #MLBB @murodalievgg")

        await message.reply("\n".join(lines), parse_mode="HTML")
        return

    # If one or both have games today
    status_lines = [
        "📅 <b>BUGUNGI O‘YINLAR DASTURI</b>",
        f"🗓 <i>Sana: {today_display}</i>\n"
    ]
    if id_rest:
        status_lines.append("🇮🇩 <b>MPL Indonesia:</b> Bugun dam olish kuni! 🏖 (/today_id)")
    else:
        status_lines.append("🇮🇩 <b>MPL Indonesia:</b> Bugun o‘yinlar bor! 🔥 (/today_id)")

    if ph_rest:
        status_lines.append("🇵🇭 <b>MPL Philippines:</b> Bugun dam olish kuni! 🏖 (/today_ph)")
    else:
        status_lines.append("🇵🇭 <b>MPL Philippines:</b> Bugun o‘yinlar bor! 🔥 (/today_ph)")

    status_lines.append("\nBatafsil jadval va kartani ko‘rish uchun yuqoridagi buyruqlarni bosing!")
    await message.reply("\n".join(status_lines), parse_mode="HTML")


@bot_router.message(Command("today_id"))
async def cmd_today_id(message: Message, bot: Bot):
    """
    Generates and returns today's MPL ID Matchday Broadcast Card or witty Rest Day message.
    """
    await message.reply("🎨 <i>MPL Indonesia bugungi holati tekshirilmoqda...</i>", parse_mode="HTML")
    from app.services.matchday_service import MatchdayService
    from app.ai.analyzer import AIAnalyzer
    from app.utils.html_utils import safe_trim_html
    from aiogram.types import BufferedInputFile

    try:
        analyzer = AIAnalyzer()
        res = await MatchdayService.generate_matchday_post("MPL ID", analyzer=analyzer)
        if not res.get("success"):
            await message.reply(res.get("message") or "O‘yinlar topilmadi.")
            return

        if res.get("is_rest_day"):
            await message.reply(res["caption"], parse_mode="HTML")
            return

        caption = safe_trim_html(res["caption"], max_len=1020)
        photo = BufferedInputFile(res["image_bytes"], filename="matchday_mpl_id.png")

        try:
            await message.reply_photo(
                photo=photo,
                caption=caption,
                parse_mode="HTML"
            )
        except Exception as photo_err:
            logger.warning(f"Reply matchday photo failed ({photo_err}), sending fallback")
            await message.reply_photo(photo=photo, caption="🇮🇩 <b>MPL INDONESIA • BUGUNGI O‘YINLAR DASTURI</b>", parse_mode="HTML")
            await message.reply(safe_trim_html(res["caption"], max_len=4000), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in cmd_today_id: {e}", exc_info=True)
        await message.reply(f"❌ Xatolik yuz berdi: {e}")


@bot_router.message(Command("today_ph"))
async def cmd_today_ph(message: Message, bot: Bot):
    """
    Generates and returns today's MPL PH Matchday Broadcast Card or witty Rest Day message.
    """
    await message.reply("🎨 <i>MPL Philippines bugungi holati tekshirilmoqda...</i>", parse_mode="HTML")
    from app.services.matchday_service import MatchdayService
    from app.ai.analyzer import AIAnalyzer
    from app.utils.html_utils import safe_trim_html
    from aiogram.types import BufferedInputFile

    try:
        analyzer = AIAnalyzer()
        res = await MatchdayService.generate_matchday_post("MPL PH", analyzer=analyzer)
        if not res.get("success"):
            await message.reply(res.get("message") or "O‘yinlar topilmadi.")
            return

        if res.get("is_rest_day"):
            await message.reply(res["caption"], parse_mode="HTML")
            return

        caption = safe_trim_html(res["caption"], max_len=1020)
        photo = BufferedInputFile(res["image_bytes"], filename="matchday_mpl_ph.png")

        try:
            await message.reply_photo(
                photo=photo,
                caption=caption,
                parse_mode="HTML"
            )
        except Exception as photo_err:
            logger.warning(f"Reply matchday photo failed ({photo_err}), sending fallback")
            await message.reply_photo(photo=photo, caption="🇵🇭 <b>MPL PHILIPPINES • BUGUNGI O‘YINLAR DASTURI</b>", parse_mode="HTML")
            await message.reply(safe_trim_html(res["caption"], max_len=4000), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in cmd_today_ph: {e}", exc_info=True)
        await message.reply(f"❌ Xatolik yuz berdi: {e}")


@bot_router.message(Command("test"))
async def cmd_test(message: Message, bot: Bot):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Faqat admin uchun ruxsat berilgan.")
        return

    await message.reply("🔄 Test patch/yangilik ma'lumotlari tahlil qilinmoqda...")

    from app.collectors import MLBBCollector
    from app.ai.analyzer import AIAnalyzer
    from app.media.image_processor import ImageProcessor
    from aiogram.types import BufferedInputFile

    collector = MLBBCollector()
    items = await collector.fetch()
    if not items:
        await message.reply("Collector orqali ma'lumot olinmadi.")
        return

    analyzer = AIAnalyzer()
    out = await analyzer.analyze(items[0])

    # Try attaching image
    img_bytes = None
    if out.category.value == "PATCH":
        recap_data = items[0].metadata.get("patch_recap_data")
        if not recap_data:
            from app.utils.hero_matcher import extract_heroes_from_text
            recap_data = extract_heroes_from_text(items[0].raw_content, items[0].title)
            items[0].metadata["patch_recap_data"] = recap_data
        try:
            img_bytes = ImageProcessor.render_patch_recap(recap_data)
        except Exception as e:
            logger.warning(f"Test patch recap generation failed: {e}")

    if not img_bytes and out.image_url:
        try:
            img_bytes = await ImageProcessor.download_and_optimize(out.image_url)
        except Exception:
            pass

    if not img_bytes:
        img_bytes = ImageProcessor.generate_news_graphic(
            title=out.title,
            category=out.category.value,
            summary=out.summary_uz,
            highlights=out.key_points
        )

    full_text = f"<b>[TEST POST PREVIEW - {out.category.value}]</b>\n\n{out.formatted_post}"
    from app.telegram.publisher import _split_caption
    caption_part, rest_part = _split_caption(full_text)

    if img_bytes:
        try:
            photo = BufferedInputFile(img_bytes, filename="test_preview.png")
            await message.reply_photo(
                photo=photo,
                caption=caption_part,
                parse_mode="HTML"
            )
            if rest_part:
                await message.reply(rest_part, parse_mode="HTML")
            return
        except Exception as e:
            logger.warning(f"Test photo send failed: {e}")

    await message.reply(
        full_text,
        parse_mode="HTML"
    )


@bot_router.message(Command("send"))
async def cmd_send(message: Message, bot: Bot):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Faqat admin uchun ruxsat berilgan.")
        return

    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("Foydalanish: /send <post_id> [ixtiyoriy yangi matn]")
        return

    post_id = int(parts[1])
    custom_text = parts[2] if len(parts) > 2 else None

    async with get_session() as session:
        post = await PostRepository.get_by_id(session, post_id)
        if not post:
            await message.reply(f"Post #{post_id} topilmadi.")
            return

        text_to_send = custom_text or post.formatted_post or post.title

        publisher = TelegramPublisher(bot=bot)
        msg_id = await publisher.publish_post(
            post_id=post.id,
            formatted_text=text_to_send,
            image_url=post.image_url
        )

    if msg_id:
        await message.reply(f"✅ <b>Post #{post_id} kanalga yuborildi!</b> (Xabar ID: <code>{msg_id}</code>)", parse_mode="HTML")
    else:
        await message.reply(
            f"❌ <b>Post #{post_id} kanalga yuborilmadi!</b>\n\n"
            "Sabablari:\n"
            "1. <code>.env</code> faylida <code>TELEGRAM_CHANNEL_ID</code> to‘g‘ri kiritilmagan bo‘lishi mumkin.\n"
            "2. Bot ko‘rsatilgan kanalda <b>Admin</b> emas yoki kanaldan chiqarib yuborilgan.\n\n"
            "💡 Tekshirish uchun /status buyrug‘ini bosing.",
            parse_mode="HTML"
        )


@bot_router.message(Command("fun"))
@bot_router.message(Command("fact"))
@bot_router.message(Command("joke"))
async def cmd_generate_fun(message: Message, bot: Bot):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Ruxsat berilmagan.")
        return

    await message.reply("🎨 <i>MLBB bo‘yicha qiziqarli fakt/hazil yaratilmoqda va infografikasi chizilmoqda...</i>", parse_mode="HTML")

    import os
    from app.ai.fun_generator import FunContentGenerator
    from app.telegram.admin import AdminNotifier
    from app.utils.hashing import generate_content_hash
    from app.utils.validators import PostStatus

    try:
        gen = FunContentGenerator()
        data = await gen.generate_fun_post()

        # Save card locally
        generated_dir = os.path.join(os.getcwd(), "assets", "generated")
        os.makedirs(generated_dir, exist_ok=True)
        card_filename = f"fun_admin_{int(datetime.now().timestamp())}.png"
        card_path = os.path.join(generated_dir, card_filename)
        with open(card_path, "wb") as f:
            f.write(data["image_bytes"])

        content_hash = generate_content_hash(data["title"], data["content"])

        async with get_session() as session:
            post = await PostRepository.create_post(
                session=session,
                source_url="https://m.mobilelegends.com",
                title=data["title"],
                category=data["topic_type"],
                content_hash=content_hash,
                status=PostStatus.PENDING.value,
                raw_content=data["content"],
                formatted_post=data["formatted_caption"],
                image_url=card_path,
                reliability_score=100,
                confidence_score=1.0,
                published_at=None
            )

        admin_notifier = AdminNotifier(bot=bot)
        await admin_notifier.send_approval_request(
            post_id=post.id,
            category=f"MLBB {data['topic_type']}",
            formatted_post=data["formatted_caption"],
            image_bytes=data["image_bytes"]
        )
    except Exception as e:
        logger.error(f"Error generating fun post on demand: {e}", exc_info=True)
        await message.reply(f"❌ Xatolik yuz berdi: {e}")


def create_bot_and_dispatcher() -> tuple[Optional[Bot], Dispatcher]:
    """
    Factory to construct Bot and Dispatcher instances safely.
    """
    dp = Dispatcher()
    dp.include_router(bot_router)
    dp.include_router(admin_router)

    token = settings.TELEGRAM_BOT_TOKEN
    bot = None
    if token and len(token) > 10 and ":" in token:
        bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not provided or invalid. Bot running in headless mode.")

    return bot, dp
