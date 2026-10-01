import asyncio
import os
from aiogram import Bot
from aiogram.types import BufferedInputFile

from app.config.settings import get_settings
from app.media.renderer import (
    render_mpl_id_result,
    render_mpl_id_upcoming,
    render_mpl_ph_result,
    render_mpl_ph_upcoming,
)
from app.ai.formatter import PostFormatter


async def main():
    settings = get_settings()
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    admin_id = settings.admin_ids[0] if settings.admin_ids else 6534784826

    print(f"Sending sample 1200x675 match graphics to Telegram Admin: {admin_id}")

    # 1. MPL ID Result
    data_id_res = {
        "league": "MPL ID",
        "season": "Season 17",
        "week": 4,
        "team_a": "RRQ",
        "team_b": "ONIC",
        "score_a": 2,
        "score_b": 1,
        "status": "FINAL",
        "mvp": "Skylar",
        "date": "29 September",
        "time": "15:00"
    }
    png_id_res = render_mpl_id_result(data_id_res)
    cap_id_res = PostFormatter.format_mpl_id_result(
        team_a="RRQ",
        score_a=2,
        score_b=1,
        team_b="ONIC",
        date_str="29 September",
        week=4,
        mvp="Skylar"
    )
    await bot.send_photo(
        chat_id=admin_id,
        photo=BufferedInputFile(png_id_res, filename="mpl_id_result_1200x675.png"),
        caption=cap_id_res,
        parse_mode="HTML"
    )
    print("Sent MPL ID Result")

    # 2. MPL ID Upcoming
    data_id_up = {
        "league": "MPL ID",
        "season": "Season 17",
        "week": 4,
        "team_a": "RRQ",
        "team_b": "ONIC",
        "status": "UPCOMING",
        "date": "29 SEPTEMBER",
        "time": "15:00",
        "series": "BO3"
    }
    png_id_up = render_mpl_id_upcoming(data_id_up)
    cap_id_up = (
        "🇮🇩 <b>MPL ID — KUTILAYOTGAN O‘YIN</b>\n\n"
        "<b>RRQ 🆚 ONIC</b>\n\n"
        "🕐 15:00 (WIB)\n"
        "📌 Week 4 • BO3\n"
        "📅 29 September\n\n"
        "#MPLID #MLBB"
    )
    await bot.send_photo(
        chat_id=admin_id,
        photo=BufferedInputFile(png_id_up, filename="mpl_id_upcoming_1200x675.png"),
        caption=cap_id_up,
        parse_mode="HTML"
    )
    print("Sent MPL ID Upcoming")

    # 3. MPL PH Result
    data_ph_res = {
        "league": "MPL PH",
        "season": "Season 14",
        "week": 4,
        "team_a": "FNOP",
        "team_b": "TLPH",
        "score_a": 2,
        "score_b": 1,
        "status": "FINAL",
        "mvp": "Kelra",
        "date": "September 29",
        "time": "17:00"
    }
    png_ph_res = render_mpl_ph_result(data_ph_res)
    cap_ph_res = PostFormatter.format_mpl_ph_result(
        team_a="FNOP",
        score_a=2,
        score_b=1,
        team_b="TLPH",
        date_str="September 29",
        week=4,
        mvp="Kelra"
    )
    await bot.send_photo(
        chat_id=admin_id,
        photo=BufferedInputFile(png_ph_res, filename="mpl_ph_result_1200x675.png"),
        caption=cap_ph_res,
        parse_mode="HTML"
    )
    print("Sent MPL PH Result")

    # 4. MPL PH Upcoming
    data_ph_up = {
        "league": "MPL PH",
        "season": "Season 14",
        "week": 4,
        "team_a": "FNOP",
        "team_b": "TLPH",
        "status": "UPCOMING",
        "date": "SEPTEMBER 29",
        "time": "17:00",
        "series": "BO3"
    }
    png_ph_up = render_mpl_ph_upcoming(data_ph_up)
    cap_ph_up = (
        "🇵🇭 <b>MPL PH — KUTILAYOTGAN O‘YIN</b>\n\n"
        "<b>FNOP 🆚 TLPH</b>\n\n"
        "🕐 17:00 (PHT)\n"
        "📌 Week 4 • BO3\n"
        "📅 September 29\n\n"
        "#MPLPH #MLBB"
    )
    await bot.send_photo(
        chat_id=admin_id,
        photo=BufferedInputFile(png_ph_up, filename="mpl_ph_upcoming_1200x675.png"),
        caption=cap_ph_up,
        parse_mode="HTML"
    )
    print("Sent MPL PH Upcoming")

    await bot.session.close()
    print("All 4 sample graphics successfully delivered to Telegram Admin!")


if __name__ == "__main__":
    asyncio.run(main())
