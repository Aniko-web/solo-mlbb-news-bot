from typing import Dict, Any, List, Optional
from app.utils.validators import CategoryEnum
from app.config.settings import get_settings
from app.ai.translator import RussianTranslator, UzbekTranslator

settings = get_settings()
CHANNEL_FOOTER = getattr(
    settings,
    "CHANNEL_FOOTER",
    (
        "<tg-emoji emoji-id=\"5251489485283140234\">✈️</tg-emoji> Telegram sahifamiz: <a href=\"https://t.me/murodalievgg\">Murodalievgg</a>\n"
        "<tg-emoji emoji-id=\"5348533850429470257\">🌐</tg-emoji> Instagram sahifamiz: <a href=\"https://instagram.com/murodalievgg\">Murodalievgg</a>\n"
        "<tg-emoji emoji-id=\"5422837510499739688\">▶️</tg-emoji> Youtube sahifamiz: <a href=\"https://youtube.com/@murodalievgg\">Murodalievgg</a>\n"
        "<tg-emoji emoji-id=\"5427168083074628963\">💎</tg-emoji> Donat Uchun:  <a href=\"https://t.me/playdomuz_bot\">Playdom</a>"
    )
)


class PostFormatter:
    """
    Standardized templates for Telegram posts in Bilingual format (Uzbek + Russian)
    according to specification.
    """

    @staticmethod
    def format_news(
        title: str,
        summary: str,
        key_points: List[str],
        source_url: str,
        title_ru: Optional[str] = None,
        summary_ru: Optional[str] = None,
        key_points_ru: Optional[List[str]] = None
    ) -> str:
        t_uz = title.strip()
        t_ru = (title_ru or RussianTranslator.translate_sentence(title)).strip()
        s_uz = summary.strip()
        s_ru = (summary_ru or RussianTranslator.translate_sentence(summary)).strip()

        pts_uz = key_points or []
        pts_ru = key_points_ru or [RussianTranslator.translate_sentence(p) for p in pts_uz]

        points_block_uz = ""
        if pts_uz:
            points_block_uz = "\n" + "\n".join(f"• {pt}" for pt in pts_uz)

        points_block_ru = ""
        if pts_ru:
            points_block_ru = "\n" + "\n".join(f"• {pt}" for pt in pts_ru)

        return (
            f"🔥 <b>MLBB YANGILIGI</b> | <b>НОВОСТИ MLBB</b>\n\n"
            f"🇺🇿 <b>O‘zbekcha:</b>\n"
            f"<b>{t_uz}</b>\n"
            f"{s_uz}"
            f"{points_block_uz}\n\n"
            f"🇷🇺 <b>Русский:</b>\n"
            f"<b>{t_ru}</b>\n"
            f"{s_ru}"
            f"{points_block_ru}\n\n"
            f"🔗 <b>Manba / Источник:</b> <a href=\"{source_url}\">Rasmiy havola / Ссылка</a>\n\n"
            f"#MLBB #Yangilik #Новости\n\n"
            f"{CHANNEL_FOOTER}"
        )

    @staticmethod
    def format_skin(
        hero: str,
        skin_name: str,
        price: str,
        release_date: str,
        description: str,
        source_url: str,
        price_ru: Optional[str] = None,
        release_date_ru: Optional[str] = None,
        description_ru: Optional[str] = None
    ) -> str:
        p_ru = price_ru or RussianTranslator.translate_sentence(price)
        d_ru = release_date_ru or RussianTranslator.translate_sentence(release_date)
        desc_ru = description_ru or RussianTranslator.translate_sentence(description)

        price_line = f"{price} | {p_ru}" if p_ru and p_ru != price else price
        date_line = f"{release_date} | {d_ru}" if d_ru and d_ru != release_date else release_date

        return (
            f"✨ <b>YANGI SKIN</b> | <b>НОВЫЙ СКИН</b>\n\n"
            f"🦸 <b>Hero / Герой:</b> {hero}\n"
            f"🎨 <b>Skin / Скин:</b> {skin_name}\n"
            f"💎 <b>Narxi / Цена:</b> {price_line}\n"
            f"📅 <b>Sana / Дата:</b> {date_line}\n\n"
            f"🇺🇿 <b>O‘zbekcha:</b>\n{description}\n\n"
            f"🇷🇺 <b>Русский:</b>\n{desc_ru}\n\n"
            f"🔗 <b>Manba / Источник:</b> <a href=\"{source_url}\">Batafsil / Подробнее</a>\n\n"
            f"#MLBB #Skin #Скины\n\n"
            f"{CHANNEL_FOOTER}"
        )

    @staticmethod
    def format_patch(
        version: str,
        buffs: List[str],
        nerfs: List[str],
        adjustments: List[str],
        source_url: str,
        summary: str = "",
        revamps: Optional[List[str]] = None,
        summary_ru: Optional[str] = None
    ) -> str:
        s_ru = summary_ru or RussianTranslator.translate_sentence(summary)

        lines = [
            "🛠 <b>MLBB PATCH NOTES YANGILANISHI</b> | <b>ОБНОВЛЕНИЕ ПАТЧА</b>\n",
            f"📌 <b>Versiya / Версия:</b> {version}\n"
        ]

        if summary:
            clean_summary = summary.strip()
            lines.append("🇺🇿 <b>O‘zbekcha:</b>")
            lines.append(f"{clean_summary}\n")
        if s_ru and s_ru.strip():
            clean_s_ru = s_ru.strip()
            lines.append("🇷🇺 <b>Русский:</b>")
            lines.append(f"{clean_s_ru}\n")

        has_changes = bool(buffs or nerfs or adjustments or revamps)
        if has_changes:
            lines.append("⚔️ <b>Qahramonlar o‘zgarishlari / Изменения героев:</b>")

            if revamps:
                rev_str = ", ".join(revamps) if isinstance(revamps, list) else str(revamps)
                lines.append(f"🟣 <b>REVAMP / РЕВАМП:</b> {rev_str}")

            if buffs:
                if len(buffs) <= 4 and any(" " in b for b in buffs):
                    lines.append("🟢 <b>BUFF / БАФФ:</b>")
                    for b in buffs:
                        lines.append(f"• {b}")
                else:
                    lines.append(f"🟢 <b>BUFF / БАФФ:</b> {', '.join(buffs)}")

            if nerfs:
                if len(nerfs) <= 4 and any(" " in n for n in nerfs):
                    lines.append("🔴 <b>NERF / НЕРФ:</b>")
                    for n in nerfs:
                        lines.append(f"• {n}")
                else:
                    lines.append(f"🔴 <b>NERF / НЕРФ:</b> {', '.join(nerfs)}")

            if adjustments:
                if len(adjustments) <= 4 and any(" " in a for a in adjustments):
                    lines.append("🟡 <b>ADJUSTMENT / КОРРЕКТИРОВКА:</b>")
                    for a in adjustments:
                        lines.append(f"• {a}")
                else:
                    lines.append(f"🟡 <b>ADJUSTMENT / КОРРЕКТИРОВКА:</b> {', '.join(adjustments)}")

        lines.append(f"\n🔗 <b>Batafsil / Подробнее:</b> <a href=\"{source_url}\">Rasmiy havola / Ссылка</a>\n")
        lines.append("#MLBB #Patch #Yangilanish #Обновление #MobileLegends\n")
        lines.append(CHANNEL_FOOTER)

        return "\n".join(lines)

    @staticmethod
    def format_hero(
        hero_name: str,
        role: str,
        description: str,
        skills: Optional[List[str]] = None,
        source_url: str = "",
        role_ru: Optional[str] = None,
        description_ru: Optional[str] = None,
        skills_ru: Optional[List[str]] = None
    ) -> str:
        r_ru = role_ru or RussianTranslator.translate_sentence(role)
        desc_ru = description_ru or RussianTranslator.translate_sentence(description)
        s_ru = skills_ru or ([RussianTranslator.translate_sentence(s) for s in skills] if skills else [])

        role_line = f"{role} | {r_ru}" if r_ru and r_ru != role else role

        lines = [
            "🦸 <b>YANGI QAHRAMON / REVAMP</b> | <b>НОВЫЙ ГЕРОЙ / РЕВАМП</b>\n",
            f"👤 <b>Qahramon / Герой:</b> {hero_name}",
            f"🎭 <b>Roli / Роль:</b> {role_line}\n",
            "🇺🇿 <b>O‘zbekcha:</b>",
            f"{description}"
        ]
        if skills:
            lines.append("⚡️ <i>Qobiliyatlar:</i>")
            for sk in skills[:3]:
                lines.append(f"• {sk}")

        lines.append("\n🇷🇺 <b>Русский:</b>")
        lines.append(f"{desc_ru}")
        if s_ru:
            lines.append("⚡️ <i>Навыки:</i>")
            for sk in s_ru[:3]:
                lines.append(f"• {sk}")

        if source_url:
            lines.append(f"\n🔗 <b>Batafsil / Подробнее:</b> <a href=\"{source_url}\">Ko‘rish / Смотреть</a>\n")
        lines.append("#MLBB #Hero #Герой #Yangilik\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @staticmethod
    def format_event(
        title: str,
        description: str,
        rewards: Optional[List[str]] = None,
        duration: Optional[str] = None,
        source_url: str = "",
        title_ru: Optional[str] = None,
        description_ru: Optional[str] = None,
        rewards_ru: Optional[List[str]] = None,
        duration_ru: Optional[str] = None
    ) -> str:
        t_ru = title_ru or RussianTranslator.translate_sentence(title)
        d_ru = description_ru or RussianTranslator.translate_sentence(description)
        dur_ru = duration_ru or (RussianTranslator.translate_sentence(duration) if duration else "")
        rw_ru = rewards_ru or ([RussianTranslator.translate_sentence(r) for r in rewards] if rewards else [])

        lines = [
            "🎉 <b>MAXSUS TADBIR (EVENT)</b> | <b>СОБЫТИЕ</b>\n",
            f"🎪 <b>{title}</b>\n"
        ]
        if duration:
            dur_display = f"{duration} | {dur_ru}" if dur_ru and dur_ru != duration else duration
            lines.append(f"📅 <b>Muddati / Срок:</b> {dur_display}\n")

        lines.append("🇺🇿 <b>O‘zbekcha:</b>")
        lines.append(f"{description}")
        if rewards:
            lines.append("🎁 <i>Mukofotlar:</i>")
            for rw in rewards[:4]:
                lines.append(f"• {rw}")

        lines.append("\n🇷🇺 <b>Русский:</b>")
        lines.append(f"{d_ru}")
        if rw_ru:
            lines.append("🎁 <i>Награды:</i>")
            for rw in rw_ru[:4]:
                lines.append(f"• {rw}")

        if source_url:
            lines.append(f"\n🔗 <b>Batafsil / Подробнее:</b> <a href=\"{source_url}\">Rasmiy manba / Ссылка</a>\n")
        lines.append("#MLBB #Event #Tadbir #События\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @staticmethod
    def format_mpl_id_schedule(
        date_str: str,
        matches: List[Dict[str, str]]
    ) -> str:
        lines = [
            "🇮🇩 <b>MPL ID — BUGUNGI O‘YINLAR</b> | <b>РАСПИСАНИЕ МАТЧЕЙ</b>\n",
            f"📅 <b>{date_str}</b>\n"
        ]
        for m in matches:
            lines.append(f"🎮 <b>{m.get('team_a', 'Team A')}</b> 🆚 <b>{m.get('team_b', 'Team B')}</b>")
            lines.append(f"🕐 {m.get('time', 'TBD')}\n")

        lines.append("#MPLID #MLBB #Esports\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @staticmethod
    def format_mpl_id_result(
        team_a: str,
        score_a: int,
        score_b: int,
        team_b: str,
        date_str: str,
        week: Optional[Any] = None,
        mvp: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> str:
        lines = [
            "🇮🇩 <b>MPL ID — NATIJA</b> | <b>РЕЗУЛЬТАТ</b>\n",
            f"<b>{team_a} {score_a} — {score_b} {team_b}</b>\n"
        ]
        if mvp and str(mvp).strip() and str(mvp).lower() not in ("unknown", "none", "yo'q", "mavjud emas", "null"):
            lines.append(f"⭐ <b>MVP:</b> {mvp}\n")

        info_lines = []
        if week:
            week_text = f"Week {week}" if str(week).isdigit() else str(week)
            info_lines.append(f"📌 {week_text}")
        if date_str:
            info_lines.append(f"📅 {date_str}")
        if info_lines:
            lines.append("\n".join(info_lines) + "\n")

        if source_url:
            lines.append(f"🔗 <b>Batafsil / Подробнее:</b> <a href=\"{source_url}\">Havola / Ссылка</a>\n")

        lines.append("#MPLID #MLBB @murodalievgg\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @staticmethod
    def format_mpl_my_result(
        team_a: str,
        score_a: int,
        score_b: int,
        team_b: str,
        date_str: str,
        week: Optional[Any] = None,
        mvp: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> str:
        lines = [
            "🇲🇾 <b>MPL MY — NATIJA</b> | <b>РЕЗУЛЬТАТ</b>\n",
            f"<b>{team_a} {score_a} — {score_b} {team_b}</b>\n"
        ]
        if mvp and str(mvp).strip() and str(mvp).lower() not in ("unknown", "none", "yo'q", "mavjud emas", "null"):
            lines.append(f"⭐ <b>MVP:</b> {mvp}\n")

        info_lines = []
        if week:
            week_text = f"Week {week}" if str(week).isdigit() else str(week)
            info_lines.append(f"📌 {week_text}")
        if date_str:
            info_lines.append(f"📅 {date_str}")
        if info_lines:
            lines.append("\n".join(info_lines) + "\n")

        if source_url:
            lines.append(f"🔗 <b>Batafsil / Подробнее:</b> <a href=\"{source_url}\">Havola / Ссылка</a>\n")

        lines.append("#MPLMY #MLBB @murodalievgg\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @staticmethod
    def format_mpl_ph_result(
        team_a: str,
        score_a: int,
        score_b: int,
        team_b: str,
        date_str: str,
        week: Optional[Any] = None,
        mvp: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> str:
        lines = [
            "🇵🇭 <b>MPL PH — NATIJA</b> | <b>РЕЗУЛЬТАТ</b>\n",
            f"<b>{team_a} {score_a} — {score_b} {team_b}</b>\n"
        ]
        if mvp and str(mvp).strip() and str(mvp).lower() not in ("unknown", "none", "yo'q", "mavjud emas", "null"):
            lines.append(f"⭐ <b>MVP:</b> {mvp}\n")

        info_lines = []
        if week:
            week_text = f"Week {week}" if str(week).isdigit() else str(week)
            info_lines.append(f"📌 {week_text}")
        if date_str:
            info_lines.append(f"📅 {date_str}")
        if info_lines:
            lines.append("\n".join(info_lines) + "\n")

        if source_url:
            lines.append(f"🔗 <b>Batafsil / Подробнее:</b> <a href=\"{source_url}\">Havola / Ссылка</a>\n")

        lines.append("#MPLPH #MLBB @murodalievgg\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @classmethod
    def format_match_result_from_data(
        cls,
        match_data: Dict[str, Any],
        source_url: Optional[str] = None
    ) -> str:
        """Format bilingual caption dynamically from structured match data."""
        league = str(match_data.get("league", "MPL ID")).upper()
        team_a = match_data.get("team_a", "Team A")
        team_b = match_data.get("team_b", "Team B")
        score_a = match_data.get("score_a", 0)
        score_b = match_data.get("score_b", 0)
        date_str = match_data.get("date", "")
        week = match_data.get("week")
        mvp = match_data.get("mvp")

        if "PH" in league or "PHILIPPINES" in league:
            return cls.format_mpl_ph_result(
                team_a=team_a,
                score_a=score_a,
                score_b=score_b,
                team_b=team_b,
                date_str=date_str,
                week=week,
                mvp=mvp,
                source_url=source_url
            )
        elif "MY" in league or "MALAYSIA" in league:
            return cls.format_mpl_my_result(
                team_a=team_a,
                score_a=score_a,
                score_b=score_b,
                team_b=team_b,
                date_str=date_str,
                week=week,
                mvp=mvp,
                source_url=source_url
            )
        else:
            return cls.format_mpl_id_result(
                team_a=team_a,
                score_a=score_a,
                score_b=score_b,
                team_b=team_b,
                date_str=date_str,
                week=week,
                mvp=mvp,
                source_url=source_url
            )

    @staticmethod
    def _build_upcoming_body(
        flag: str,
        league_name: str,
        team_a: str,
        team_b: str,
        time_str: str,
        date_str: str,
        week: Optional[Any],
        series: str,
        source_url: Optional[str],
        countdown_str: Optional[str],
        ai_prediction: Optional[Dict[str, Any]],
        hashtag: str
    ) -> str:
        lines = [
            f"{flag} <b>{league_name} — KUTILAYOTGAN O‘YIN</b> | <b>ПРЕДСТОЯЩИЙ МАТЧ</b>\n",
            f"<b>{team_a} 🆚 {team_b}</b>\n"
        ]
        info_lines = []
        if time_str:
            info_lines.append(f"🕐 <b>Vaqt / Время:</b> {time_str}")
        if countdown_str and countdown_str != "Tugagan":
            info_lines.append(f"⏳ <b>O‘yinga qolgan vaqt / До матча:</b> {countdown_str}")
        if week:
            week_text = f"Week {week}" if str(week).isdigit() else str(week)
            info_lines.append(f"📌 {week_text} • {series}")
        elif series:
            info_lines.append(f"📌 {series}")
        if date_str:
            info_lines.append(f"📅 {date_str}")
        if info_lines:
            lines.append("\n".join(info_lines) + "\n")

        # AI Prediction Block
        if ai_prediction:
            sa = ai_prediction.get("predicted_score_a", 2)
            sb = ai_prediction.get("predicted_score_b", 1)
            pa = ai_prediction.get("prob_a", 55)
            pb = ai_prediction.get("prob_b", 45)
            comm_uz = ai_prediction.get("commentary_uz", "").strip()
            comm_ru = ai_prediction.get("commentary_ru", "").strip()
            if not comm_ru and comm_uz:
                comm_ru = RussianTranslator.translate_sentence(comm_uz)

            lines.append("🤖 <b>AI TAHLILI VA TAXMINIY HISOB / AI ПРОГНОЗ:</b>")
            lines.append(f"🎯 <b>Taxminiy hisob / Прогноз счета:</b> <code>{team_a} {sa} — {sb} {team_b}</code>")
            lines.append(f"📊 <b>G‘alaba ehtimoli / Вероятность:</b> {team_a} ({pa}%) | {team_b} ({pb}%)")
            if comm_uz:
                lines.append(f"🎙 🇺🇿 <i>{comm_uz}</i>")
            if comm_ru:
                lines.append(f"🎙 🇷🇺 <i>{comm_ru}</i>")
            lines.append("")

        if source_url:
            lines.append(f"🔗 <b>Batafsil / Подробнее:</b> <a href=\"{source_url}\">Liquipedia</a>\n")

        lines.append(f"{hashtag} #MLBB #AIPrognoz #Прогноз @murodalievgg\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @classmethod
    def format_mpl_id_upcoming(
        cls,
        team_a: str,
        team_b: str,
        time_str: str = "15:00",
        date_str: str = "",
        week: Optional[Any] = None,
        series: str = "BO3",
        source_url: Optional[str] = None,
        countdown_str: Optional[str] = None,
        ai_prediction: Optional[Dict[str, Any]] = None
    ) -> str:
        time_clean = time_str if ("WIB" in time_str or "UZ" in time_str) else f"{time_str} (WIB)"
        return cls._build_upcoming_body(
            flag="🇮🇩",
            league_name="MPL ID",
            team_a=team_a,
            team_b=team_b,
            time_str=time_clean,
            date_str=date_str,
            week=week,
            series=series,
            source_url=source_url,
            countdown_str=countdown_str,
            ai_prediction=ai_prediction,
            hashtag="#MPLID"
        )

    @classmethod
    def format_mpl_ph_upcoming(
        cls,
        team_a: str,
        team_b: str,
        time_str: str = "17:00",
        date_str: str = "",
        week: Optional[Any] = None,
        series: str = "BO3",
        source_url: Optional[str] = None,
        countdown_str: Optional[str] = None,
        ai_prediction: Optional[Dict[str, Any]] = None
    ) -> str:
        time_clean = time_str if ("PHT" in time_str or "UZ" in time_str) else f"{time_str} (PHT)"
        return cls._build_upcoming_body(
            flag="🇵🇭",
            league_name="MPL PH",
            team_a=team_a,
            team_b=team_b,
            time_str=time_clean,
            date_str=date_str,
            week=week,
            series=series,
            source_url=source_url,
            countdown_str=countdown_str,
            ai_prediction=ai_prediction,
            hashtag="#MPLPH"
        )

    @classmethod
    def format_mpl_my_upcoming(
        cls,
        team_a: str,
        team_b: str,
        time_str: str = "15:00",
        date_str: str = "",
        week: Optional[Any] = None,
        series: str = "BO3",
        source_url: Optional[str] = None,
        countdown_str: Optional[str] = None,
        ai_prediction: Optional[Dict[str, Any]] = None
    ) -> str:
        time_clean = time_str if ("MYT" in time_str or "UZ" in time_str) else f"{time_str} (MYT)"
        return cls._build_upcoming_body(
            flag="🇲🇾",
            league_name="MPL MY",
            team_a=team_a,
            team_b=team_b,
            time_str=time_clean,
            date_str=date_str,
            week=week,
            series=series,
            source_url=source_url,
            countdown_str=countdown_str,
            ai_prediction=ai_prediction,
            hashtag="#MPLMY"
        )

    @classmethod
    def format_match_upcoming_from_data(
        cls,
        match_data: Dict[str, Any],
        source_url: Optional[str] = None
    ) -> str:
        """Format bilingual caption dynamically for an upcoming match."""
        league = str(match_data.get("league", "MPL ID")).upper()
        team_a = match_data.get("team_a", "Team A")
        team_b = match_data.get("team_b", "Team B")
        time_str = match_data.get("time", "15:00")
        date_str = match_data.get("date_display") or match_data.get("date", "")
        week = match_data.get("week")
        series = match_data.get("series", "BO3")
        countdown_str = match_data.get("countdown_str")
        ai_prediction = match_data.get("ai_prediction")

        if "PH" in league or "PHILIPPINES" in league:
            return cls.format_mpl_ph_upcoming(
                team_a=team_a,
                team_b=team_b,
                time_str=time_str,
                date_str=date_str,
                week=week,
                series=series,
                source_url=source_url,
                countdown_str=countdown_str,
                ai_prediction=ai_prediction
            )
        elif "MY" in league or "MALAYSIA" in league:
            return cls.format_mpl_my_upcoming(
                team_a=team_a,
                team_b=team_b,
                time_str=time_str,
                date_str=date_str,
                week=week,
                series=series,
                source_url=source_url,
                countdown_str=countdown_str,
                ai_prediction=ai_prediction
            )
        else:
            return cls.format_mpl_id_upcoming(
                team_a=team_a,
                team_b=team_b,
                time_str=time_str,
                date_str=date_str,
                week=week,
                series=series,
                source_url=source_url,
                countdown_str=countdown_str,
                ai_prediction=ai_prediction
            )

    @staticmethod
    def format_esports(
        title: str,
        summary: str,
        tournament: Optional[str],
        source_url: str,
        title_ru: Optional[str] = None,
        summary_ru: Optional[str] = None
    ) -> str:
        t_uz = title.strip()
        t_ru = (title_ru or RussianTranslator.translate_sentence(title)).strip()
        s_uz = summary.strip()
        s_ru = (summary_ru or RussianTranslator.translate_sentence(summary)).strip()

        tourney_line = f"🏆 <b>Turnir / Турнир:</b> {tournament}\n\n" if tournament else ""
        return (
            f"🌍 <b>ESPORTS YANGILIGI | КИБЕРСПОРТ MLBB</b>\n\n"
            f"{tourney_line}"
            f"🇺🇿 <b>O‘zbekcha:</b>\n"
            f"<b>{t_uz}</b>\n"
            f"{s_uz}\n\n"
            f"🇷🇺 <b>Русский:</b>\n"
            f"<b>{t_ru}</b>\n"
            f"{s_ru}\n\n"
            f"🔗 <b>Batafsil / Подробнее:</b> <a href=\"{source_url}\">Rasmiy manba / Ссылка</a>\n\n"
            f"#Esports #MLBB #Киберспорт\n\n"
            f"{CHANNEL_FOOTER}"
        )
