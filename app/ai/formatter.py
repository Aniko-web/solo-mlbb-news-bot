from typing import Dict, Any, List, Optional
from app.utils.validators import CategoryEnum
from app.config.settings import get_settings

settings = get_settings()
CHANNEL_FOOTER = getattr(
    settings,
    "CHANNEL_FOOTER",
    (
        "💬 Telegram sahifamiz: <a href=\"https://t.me/murodalievgg\">Murodalievgg</a>\n"
        "📹 Instagram sahifamiz: <a href=\"https://instagram.com/murodalievgg\">Murodalievgg</a>\n"
        "📹 Youtube sahifamiz: <a href=\"https://youtube.com/@murodalievgg\">Murodalievgg</a>\n"
        "😍 Donat Uchun:  <a href=\"https://t.me/playdomuz_bot\">Playdom</a>"
    )
)


class PostFormatter:
    """
    Standardized templates for Telegram posts in Uzbek according to specification.
    """

    @staticmethod
    def format_news(
        title: str,
        summary: str,
        key_points: List[str],
        source_url: str
    ) -> str:
        points_block = ""
        if key_points:
            points_block = "\n📌 <b>Muhim:</b>\n" + "\n".join(f"• {pt}" for pt in key_points)

        return (
            f"🔥 <b>MLBB YANGILIGI</b>\n\n"
            f"<b>{title}</b>\n\n"
            f"{summary}"
            f"{points_block}\n\n"
            f"🔗 <b>Manba:</b> <a href=\"{source_url}\">Rasmiy havola</a>\n\n"
            f"#MLBB #Yangilik\n\n"
            f"{CHANNEL_FOOTER}"
        )

    @staticmethod
    def format_skin(
        hero: str,
        skin_name: str,
        price: str,
        release_date: str,
        description: str,
        source_url: str
    ) -> str:
        return (
            f"✨ <b>YANGI SKIN</b>\n\n"
            f"🦸 <b>Hero:</b> {hero}\n"
            f"🎨 <b>Skin:</b> {skin_name}\n"
            f"💎 <b>Narxi:</b> {price}\n"
            f"📅 <b>Chiqish sanasi:</b> {release_date}\n\n"
            f"{description}\n\n"
            f"🔗 <b>Manba:</b> <a href=\"{source_url}\">Batafsil</a>\n\n"
            f"#MLBB #Skin\n\n"
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
        revamps: Optional[List[str]] = None
    ) -> str:
        lines = [
            "🛠 <b>MLBB PATCH NOTES YANGILANISHI</b>\n",
            f"📌 <b>Versiya:</b> {version}\n"
        ]

        if summary:
            clean_summary = summary.strip()
            lines.append(f"📝 <b>Tavsif:</b>\n{clean_summary}\n")

        has_changes = bool(buffs or nerfs or adjustments or revamps)
        if has_changes:
            lines.append("⚔️ <b>Qahramonlar o‘zgarishlari:</b>")

            if revamps:
                rev_str = ", ".join(revamps) if isinstance(revamps, list) else str(revamps)
                lines.append(f"🟣 <b>REVAMP:</b> {rev_str}")

            if buffs:
                if len(buffs) <= 4 and any(" " in b for b in buffs):
                    lines.append("🟢 <b>BUFF:</b>")
                    for b in buffs:
                        lines.append(f"• {b}")
                else:
                    lines.append(f"🟢 <b>BUFF:</b> {', '.join(buffs)}")

            if nerfs:
                if len(nerfs) <= 4 and any(" " in n for n in nerfs):
                    lines.append("🔴 <b>NERF:</b>")
                    for n in nerfs:
                        lines.append(f"• {n}")
                else:
                    lines.append(f"🔴 <b>NERF:</b> {', '.join(nerfs)}")

            if adjustments:
                if len(adjustments) <= 4 and any(" " in a for a in adjustments):
                    lines.append("🟡 <b>ADJUSTMENT:</b>")
                    for a in adjustments:
                        lines.append(f"• {a}")
                else:
                    lines.append(f"🟡 <b>ADJUSTMENT:</b> {', '.join(adjustments)}")

        lines.append(f"\n🔗 <b>Batafsil ma'lumot:</b> <a href=\"{source_url}\">Rasmiy havola</a>\n")
        lines.append("#MLBB #Patch #Yangilanish #MobileLegends\n")
        lines.append(CHANNEL_FOOTER)

        return "\n".join(lines)

    @staticmethod
    def format_hero(
        hero_name: str,
        role: str,
        description: str,
        skills: Optional[List[str]] = None,
        source_url: str = ""
    ) -> str:
        lines = [
            "🦸 <b>YANGI QAHRAMON / REVAMP</b>\n",
            f"👤 <b>Qahramon:</b> {hero_name}",
            f"🎭 <b>Roli:</b> {role}\n",
            f"{description}"
        ]
        if skills:
            lines.append("\n⚡️ <b>Asosiy qobiliyatlar:</b>")
            for sk in skills[:3]:
                lines.append(f"• {sk}")
        if source_url:
            lines.append(f"\n🔗 <b>Batafsil:</b> <a href=\"{source_url}\">Ko‘rish</a>\n")
        lines.append("#MLBB #Hero #Yangilik\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @staticmethod
    def format_event(
        title: str,
        description: str,
        rewards: Optional[List[str]] = None,
        duration: Optional[str] = None,
        source_url: str = ""
    ) -> str:
        lines = [
            "🎉 <b>MAXSUS TADBIR (EVENT)</b>\n",
            f"🎪 <b>{title}</b>\n"
        ]
        if duration:
            lines.append(f"📅 <b>Muddati:</b> {duration}\n")
        lines.append(f"{description}")
        if rewards:
            lines.append("\n🎁 <b>Mukofotlar va imkoniyatlar:</b>")
            for rw in rewards[:4]:
                lines.append(f"• {rw}")
        if source_url:
            lines.append(f"\n🔗 <b>Batafsil:</b> <a href=\"{source_url}\">Rasmiy manba</a>\n")
        lines.append("#MLBB #Event #Tadbir\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @staticmethod
    def format_mpl_id_schedule(
        date_str: str,
        matches: List[Dict[str, str]]
    ) -> str:
        lines = [
            f"🇮🇩 <b>MPL ID — BUGUNGI O‘YINLAR</b>\n",
            f"📅 <b>{date_str}</b>\n"
        ]
        for m in matches:
            lines.append(f"🎮 <b>{m.get('team_a', 'Team A')}</b> 🆚 <b>{m.get('team_b', 'Team B')}</b>")
            lines.append(f"🕐 {m.get('time', 'TBD')}\n")

        lines.append("#MPLID #MLBB\n")
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
            "🇮🇩 <b>MPL ID — NATIJA</b>\n",
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
            lines.append(f"🔗 <b>Batafsil:</b> <a href=\"{source_url}\">Havola</a>\n")

        lines.append("#MPLID #MLBB @murodalievgg\n")
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
            "🇵🇭 <b>MPL PH — NATIJA</b>\n",
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
            lines.append(f"🔗 <b>Batafsil:</b> <a href=\"{source_url}\">Havola</a>\n")

        lines.append("#MPLPH #MLBB @murodalievgg\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @classmethod
    def format_match_result_from_data(
        cls,
        match_data: Dict[str, Any],
        source_url: Optional[str] = None
    ) -> str:
        """Format Uzbek caption dynamically from structured match data."""
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
    def format_mpl_id_upcoming(
        team_a: str,
        team_b: str,
        time_str: str = "15:00",
        date_str: str = "",
        week: Optional[Any] = None,
        series: str = "BO3",
        source_url: Optional[str] = None,
        countdown_str: Optional[str] = None
    ) -> str:
        lines = [
            "🇮🇩 <b>MPL ID — KUTILAYOTGAN O‘YIN</b>\n",
            f"<b>{team_a} 🆚 {team_b}</b>\n"
        ]
        info_lines = []
        if time_str:
            time_clean = time_str if ("WIB" in time_str or "UZ" in time_str) else f"{time_str} (WIB)"
            info_lines.append(f"🕐 <b>Vaqt:</b> {time_clean}")
        if countdown_str and countdown_str != "Tugagan":
            info_lines.append(f"⏳ <b>O‘yinga qolgan vaqt:</b> {countdown_str}")
        if week:
            week_text = f"Week {week}" if str(week).isdigit() else str(week)
            info_lines.append(f"📌 {week_text} • {series}")
        elif series:
            info_lines.append(f"📌 {series}")
        if date_str:
            info_lines.append(f"📅 {date_str}")
        if info_lines:
            lines.append("\n".join(info_lines) + "\n")

        if source_url:
            lines.append(f"🔗 <b>Batafsil:</b> <a href=\"{source_url}\">Liquipedia</a>\n")

        lines.append("#MPLID #MLBB @murodalievgg\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @staticmethod
    def format_mpl_ph_upcoming(
        team_a: str,
        team_b: str,
        time_str: str = "17:00",
        date_str: str = "",
        week: Optional[Any] = None,
        series: str = "BO3",
        source_url: Optional[str] = None,
        countdown_str: Optional[str] = None
    ) -> str:
        lines = [
            "🇵🇭 <b>MPL PH — KUTILAYOTGAN O‘YIN</b>\n",
            f"<b>{team_a} 🆚 {team_b}</b>\n"
        ]
        info_lines = []
        if time_str:
            time_clean = time_str if ("PHT" in time_str or "UZ" in time_str) else f"{time_str} (PHT)"
            info_lines.append(f"🕐 <b>Vaqt:</b> {time_clean}")
        if countdown_str and countdown_str != "Tugagan":
            info_lines.append(f"⏳ <b>O‘yinga qolgan vaqt:</b> {countdown_str}")
        if week:
            week_text = f"Week {week}" if str(week).isdigit() else str(week)
            info_lines.append(f"📌 {week_text} • {series}")
        elif series:
            info_lines.append(f"📌 {series}")
        if date_str:
            info_lines.append(f"📅 {date_str}")
        if info_lines:
            lines.append("\n".join(info_lines) + "\n")

        if source_url:
            lines.append(f"🔗 <b>Batafsil:</b> <a href=\"{source_url}\">Liquipedia</a>\n")

        lines.append("#MPLPH #MLBB @murodalievgg\n")
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @classmethod
    def format_match_upcoming_from_data(
        cls,
        match_data: Dict[str, Any],
        source_url: Optional[str] = None
    ) -> str:
        """Format Uzbek caption dynamically for an upcoming match."""
        league = str(match_data.get("league", "MPL ID")).upper()
        team_a = match_data.get("team_a", "Team A")
        team_b = match_data.get("team_b", "Team B")
        time_str = match_data.get("time", "15:00")
        date_str = match_data.get("date_display") or match_data.get("date", "")
        week = match_data.get("week")
        series = match_data.get("series", "BO3")
        countdown_str = match_data.get("countdown_str")

        if "PH" in league or "PHILIPPINES" in league:
            return cls.format_mpl_ph_upcoming(
                team_a=team_a,
                team_b=team_b,
                time_str=time_str,
                date_str=date_str,
                week=week,
                series=series,
                source_url=source_url,
                countdown_str=countdown_str
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
                countdown_str=countdown_str
            )

    @staticmethod
    def format_esports(
        title: str,
        summary: str,
        tournament: Optional[str],
        source_url: str
    ) -> str:
        tourney_line = f"🏆 <b>Turnir:</b> {tournament}\n" if tournament else ""
        return (
            f"🌍 <b>ESPORTS YANGILIGI</b>\n\n"
            f"<b>{title}</b>\n\n"
            f"{tourney_line}"
            f"{summary}\n\n"
            f"🔗 <b>Batafsil:</b> <a href=\"{source_url}\">Rasmiy manba</a>\n\n"
            f"#Esports #MLBB\n\n"
            f"{CHANNEL_FOOTER}"
        )
