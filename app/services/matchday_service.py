import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

from app.utils.logger import logger
from app.config.settings import get_settings
from app.services.liquipedia_parser import LiquipediaParserService, UZ_MONTHS
from app.media.renderer import render_matchday_schedule
from app.ai.analyzer import AIAnalyzer

settings = get_settings()

TASHKENT_TZ = timezone(timedelta(hours=5))


class MatchdayService:
    """
    Orchestrates daily matchday schedules for MPL ID and MPL PH:
    1. Aggregates all matches scheduled for the day.
    2. Identifies the Match of the Day (Kunning eng muhim o'yini) using AI.
    3. Generates captivating, hype-filled Uzbek analysis and commentary.
    4. Renders broadcast 1200x675 HD Matchday Schedule Card.
    """

    @classmethod
    def get_current_date_tashkent(cls) -> str:
        """Returns current date in Tashkent as YYYY-MM-DD."""
        return datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d")

    @classmethod
    def format_uzbek_date_header(cls, date_str: str) -> str:
        """Format 2026-10-01 to '01-OKTABR, PAYSHANBA'."""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day = dt.strftime("%d")
            month_num = dt.strftime("%m")
            month_uz = UZ_MONTHS.get(month_num, "oy").upper()
            
            weekdays = {
                0: "DUSHANBA",
                1: "SESHANBA",
                2: "CHORSHANBA",
                3: "PAYSHANBA",
                4: "JUMA",
                5: "SHANBA",
                6: "YAKSHANBA"
            }
            wd = weekdays.get(dt.weekday(), "")
            return f"{day}-{month_uz}, {wd}"
        except Exception:
            return date_str

    REST_DAY_SITUATIONAL_HUMORS = {
        "tomorrow": [
            "Buguncha prolar bazada dam olar emish... Ertangi shiddatli to‘qnashuvlar oldidan nafas rostlayapmiz. Solo rankda asabni asrang! 😉",
            "Arenalarda bo‘ron oldidan sokinlik! Ertaga haqiqiy to‘qnashuvlar boshlanadi, bugun esa manalarni 100% to‘ldirib olamiz. 🔋⚡️",
            "Lord va Tortillar bugun xotirjam — hech kim Retribution bilan o‘g‘irlagani kelmaydi! Ertaga turnir qaytadi. 🐢👑",
            "Ertangi derbilar oldidan pro-klanlar bazada yangi metani sinab ko‘rmoqda. Bugun solo rankda fiderlardan ehtiyot bo‘ling! 📱🎮",
            "Kustda pusib yotishga 1 kunlik tanaffus! Ertaga esa Season 18 ning qaynoq bahslariga start beriladi. 🔥",
        ],
        "multiday": [
            "Season 18 da hafta o‘rtasidagi tanaffus! O‘yinchilar solo rankda yulduz tushirib asabni buzmaslik uchun dam olyapti shekilli... 😂",
            "Prolar bazada choy ichib, yangi taktikalar chizishmoqda. Turnir janglari dam olish kunlarida davom etadi! ☕️📋",
            "Kibersport arenalari bir muddat jimjit. Siz ham bugun telefonni bir chetga surib, nafas rostlab oling! 🧘‍♂️✨",
            "Barcha qahramonlar bazada regeneratsiya jarayonida. Keyingi qizg‘in bahslarga kuch yig‘yapmiz! 🛡⚔️",
        ],
        "general": [
            "Bugun arenalarda rasmiy tanaffus! Prolar dam olmoqda, sizga esa solo rankda yuqori winrate va aqlli timmeytlar tilaymiz! 🚀",
            "Retribution tugmalari sovumoqda — bugun rasmiy o‘yinlar yo‘q. Yangi kuch bilan keyingi o‘yin kunini kutamiz! 🕹",
            "Bugun pro-arena sokin. Solo rankda telefonni devorga urmasdan, o‘yindan maroqli zavq oling! 📱😉"
        ]
    }

    REST_DAY_HUMORS = (
        REST_DAY_SITUATIONAL_HUMORS["tomorrow"]
        + REST_DAY_SITUATIONAL_HUMORS["multiday"]
        + REST_DAY_SITUATIONAL_HUMORS["general"]
    )

    @classmethod
    async def generate_rest_day_humor(
        cls,
        league: str,
        today_date: str,
        next_matchday: Optional[Dict[str, Any]] = None,
        analyzer: Optional[AIAnalyzer] = None
    ) -> str:
        """
        Generates dynamic, context-aware, witty rest-day comment in authentic Uzbek gamer slang.
        Varies by season, day of week, time to next match, and upcoming matchups.
        """
        import random
        is_ph = "PH" in league.upper()
        league_title = "MPL Philippines" if is_ph else "MPL Indonesia"
        today_dt = None
        try:
            today_dt = datetime.strptime(today_date, "%Y-%m-%d")
        except Exception:
            pass

        days_until_next = None
        next_date_str = ""
        upcoming_teams_str = ""
        if next_matchday and next_matchday.get("date"):
            try:
                next_dt = datetime.strptime(next_matchday["date"], "%Y-%m-%d")
                if today_dt:
                    days_until_next = (next_dt - today_dt).days
                next_date_str = next_matchday.get("date_display") or next_matchday["date"]
                if next_matchday.get("matches"):
                    teams = [f"{m['team_a']} vs {m['team_b']}" for m in next_matchday["matches"][:3]]
                    upcoming_teams_str = ", ".join(teams)
            except Exception:
                pass

        # 1. If analyzer available, use Gemini LLM for unique dynamic humor
        if analyzer and analyzer.client:
            try:
                context_notes = [
                    f"Musobaqa: {league_title} (Season 18)",
                    f"Bugun: {cls.format_uzbek_date_header(today_date)} (o'yinlar yo'q, rasmiy tanaffus kuni)"
                ]
                if days_until_next == 1:
                    context_notes.append(f"Keyingi o'yin: ERTAGA ({next_date_str}). Kutilayotgan o'yinlar: {upcoming_teams_str}")
                elif days_until_next and days_until_next > 1:
                    context_notes.append(f"Keyingi o'yin: {days_until_next} kundan keyin ({next_date_str}). Kutilayotgan o'yinlar: {upcoming_teams_str}")
                else:
                    context_notes.append("Keyingi o'yin sanasi hozircha e'lon qilinmagan.")

                prompt = (
                    "Sen Mobile Legends: Bang Bang (MLBB) bo'yicha eng mashhur o'zbek Telegram kanali (@murodalievgg) muallifisan.\n"
                    f"Holat:\n" + "\n".join(context_notes) + "\n\n"
                    "VAZIFA:\n"
                    "Bugun ligada o'yin yo'qligi (dam olish kuni) haqida o'yinchilar tilida (gamer slang, yoshlarcha, samimiy, hazilsimon) "
                    "JUDA QISQA sharh yoz.\n"
                    "Qat'iy talablar:\n"
                    "1. MAKSIMAL 1-2 TA QISQA JUMLA (12-25 ta so'z)! Ortiqcha gap, cho'zish va rasmiyatchilik umuman bo'lmasin.\n"
                    "2. Mavsum (Season 18) va vaziyatga (o'yin ertagami, bir necha kundan keyinmi, qaysi jamoalar to'qnash keladi) qarab HAR SAFAR TURLICHA, original bo'lsin.\n"
                    "3. O'yin terminlaridan (Lord, Tortil, Retri, mana to'ldirish, kustda pusish, solo rank, fiderlar, yulduz tushirish) tabiiy va kulgili foydalan.\n"
                    "4. 'Buguncha pro-o'yinchilar dam olar emish...' jumlasini har safar bir xil takrorlama, har safar yangi va qiziqarli gaplar tuz!\n"
                    "5. FAQAT bitta qisqa sharh matnini qaytar (qo'shtirnoqsiz, JSONsiz, sarlavhasiz)."
                )

                response = await analyzer.client.chat.completions.create(
                    model=analyzer.model,
                    messages=[
                        {"role": "system", "content": "Sen Mobile Legends o'yinini yaxshi biladigan o'zbek geymerisan. Faqat 1-2 qisqa jumlali hazil/sharh qaytarasan."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.85,
                    max_tokens=80
                )
                generated = response.choices[0].message.content.strip().strip('"').strip("'")
                if generated and len(generated) > 10:
                    return generated
            except Exception as ai_err:
                logger.warning(f"AI Rest Day Humor generation failed, falling back to situational templates: {ai_err}")

        # 2. Fallback: select from situational pool based on context
        if days_until_next == 1:
            pool = cls.REST_DAY_SITUATIONAL_HUMORS["tomorrow"]
        elif days_until_next and days_until_next > 1:
            pool = cls.REST_DAY_SITUATIONAL_HUMORS["multiday"]
        else:
            pool = cls.REST_DAY_SITUATIONAL_HUMORS["general"]

        return random.choice(pool)

    @classmethod
    async def get_matches_for_day(
        cls,
        league: str = "MPL ID",
        target_date: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]], bool, Optional[Dict[str, Any]]]:
        """
        Retrieves matches for target_date.
        Returns:
            (selected_date, matches_list, is_rest_day, next_matchday_info)
        """
        # 1. First attempt to load matches from local DB
        all_matches = []
        try:
            from app.database.database import get_session
            from app.database.repositories import MatchRepository
            normalized_league = "MPL PH" if "PH" in league.upper() else "MPL ID"
            async with get_session() as session:
                db_matches = await MatchRepository.get_all_matches_by_league(session, normalized_league)
                if db_matches:
                    all_matches = db_matches
        except Exception as db_err:
            logger.warning(f"Could not load matches from DB for {league}: {db_err}")

        # 2. Fallback to Liquipedia API if local DB is empty
        if not all_matches:
            is_ph = "PH" in league.upper()
            if is_ph:
                all_matches = await LiquipediaParserService.fetch_and_parse_mpl_ph(18)
            else:
                all_matches = await LiquipediaParserService.fetch_and_parse_mpl_id(18)

        by_date: Dict[str, List[Any]] = {}
        for m in all_matches:
            if m.date and m.date != "TBD":
                by_date.setdefault(m.date, []).append(m)

        today = target_date or cls.get_current_date_tashkent()

        # If today has matches, return today's matches
        if today in by_date and by_date[today]:
            raw_list = by_date.get(today, [])
            formatted_matches: List[Dict[str, Any]] = []
            for i, m in enumerate(raw_list):
                formatted_matches.append({
                    "match_num": i + 1,
                    "team_a": m.team_a,
                    "team_b": m.team_b,
                    "time": m.time if ("Toshkent" in m.time or "(UZ)" in m.time) else f"{m.time} (Toshkent)",
                    "series": m.series or "BO3",
                    "status": m.status.upper(),
                    "score_a": m.score_a,
                    "score_b": m.score_b,
                    "is_motd": False
                })
            return today, formatted_matches, False, None

        # If no matches today, it's a rest day! Find next matchday
        upcoming_dates = [d for d in sorted(by_date.keys()) if d > today]
        next_matchday_info = None
        if upcoming_dates:
            next_date = upcoming_dates[0]
            next_raw = by_date.get(next_date, [])
            formatted_next: List[Dict[str, Any]] = []
            for i, m in enumerate(next_raw):
                formatted_next.append({
                    "match_num": i + 1,
                    "team_a": m.team_a,
                    "team_b": m.team_b,
                    "time": m.time if ("Toshkent" in m.time or "(UZ)" in m.time) else f"{m.time} (Toshkent)",
                    "series": m.series or "BO3",
                    "status": m.status.upper(),
                    "score_a": m.score_a,
                    "score_b": m.score_b,
                    "is_motd": False
                })
            next_matchday_info = {
                "date": next_date,
                "date_display": cls.format_uzbek_date_header(next_date),
                "matches": formatted_next
            }

        return today, [], True, next_matchday_info

    @classmethod
    async def select_motd_and_generate_hype(
        cls,
        league: str,
        date_str: str,
        matches: List[Dict[str, Any]],
        analyzer: Optional[AIAnalyzer] = None
    ) -> Dict[str, Any]:
        """
        Selects Match of the Day (Kunning markaziy o'yini) and generates engaging Uzbek hype commentary.
        """
        if not matches:
            return {
                "motd_index": 0,
                "motd_team_a": "TEAM A",
                "motd_team_b": "TEAM B",
                "hype_text": "Bugungi bahslarda murosasiz janglar kutilmoqda!"
            }

        # 1. Try LLM generation if available
        if analyzer and analyzer.client:
            try:
                matches_summary = "\n".join([
                    f"{idx}. {m['team_a']} vs {m['team_b']} (Vaqti: {m['time']})"
                    for idx, m in enumerate(matches)
                ])
                prompt = (
                    f"Sen Mobile Legends: Bang Bang (MLBB) e-sporti bo'yicha mashhur o'zbek sharhlovchisisan.\n"
                    f"Musobaqa: {league}\n"
                    f"Bugungi o'yinlar ro'yxati:\n{matches_summary}\n\n"
                    f"VAZIFA:\n"
                    f"1. Ushbu o'yinlar ichidan KUNNING ENG MUHIM, ENG QIZIQARLI BAHSI (Match of the Day)ni tanla.\n"
                    f"2. Ushbu markaziy o'yin uchun JUDA QISQA va JOZIBALI sharh (anons) yoz (Maksimal 1-2 qisqa jumla, 15-25 ta so'z!). Cho'zma!\n"
                    f"Misol:\n"
                    f"- 'Bugun ONIC jamoasi o‘tgan mag‘lubiyat uchun qasos olish va peshqadamlikni qaytarish uchun ajoyib imkoniyatga ega!'\n"
                    f"- 'Titanlar to‘qnashuvi! Har ikki jamoa uchun bu bahsda mag‘lubiyatga o‘rin yo‘q.'\n\n"
                    f"FAQAT quyidagi JSON formatida javob ber:\n"
                    f"{{\n"
                    f'  "motd_index": 0,\n'
                    f'  "hype_text": "qisqa 1-2 jumlali sharh..."\n'
                    f"}}"
                )

                response = await analyzer.client.chat.completions.create(
                    model=analyzer.model,
                    messages=[
                        {"role": "system", "content": "You output only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                raw_text = response.choices[0].message.content.strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()

                parsed = json.loads(raw_text)
                idx = int(parsed.get("motd_index", 0))
                if 0 <= idx < len(matches):
                    matches[idx]["is_motd"] = True
                    return {
                        "motd_index": idx,
                        "motd_team_a": matches[idx]["team_a"],
                        "motd_team_b": matches[idx]["team_b"],
                        "hype_text": parsed.get("hype_text", "").strip()
                    }
            except Exception as e:
                logger.warning(f"LLM Match of the Day analysis failed, using deterministic hype generator: {e}")

        # 2. Deterministic Fallback: Score matchups by popularity and rivalry
        rivalry_weights = {
            # ID
            ("ONIC ID", "RRQ HOSHI"): 100,
            ("EVOS GLORY", "RRQ HOSHI"): 95,
            ("ONIC ID", "BIGETRON ALPHA"): 90,
            ("TEAM LIQUID ID", "ONIC ID"): 88,
            ("ALTER EGO", "RRQ HOSHI"): 85,
            ("EVOS GLORY", "ONIC ID"): 85,
            # PH
            ("ONIC PH", "AP.BREN"): 100,
            ("TEAM FALCONS", "AP.BREN"): 98,
            ("TEAM LIQUID PH", "ONIC PH"): 95,
            ("AURORA GAMING", "ONIC PH"): 90,
            ("SMART OMEGA", "AP.BREN"): 85,
        }

        best_idx = 0
        best_score = -1

        for idx, m in enumerate(matches):
            ta = m["team_a"]
            tb = m["team_b"]
            score = rivalry_weights.get((ta, tb), rivalry_weights.get((tb, ta), 0))
            if "ONIC" in ta or "ONIC" in tb:
                score += 30
            if "RRQ" in ta or "RRQ" in tb:
                score += 25
            if "AP.BREN" in ta or "AP.BREN" in tb:
                score += 25
            if score > best_score:
                best_score = score
                best_idx = idx

        # If none specifically matched, take the last match (often the prime-time main event)
        if best_score <= 0 and len(matches) > 1:
            best_idx = len(matches) - 1

        matches[best_idx]["is_motd"] = True
        motd_a = matches[best_idx]["team_a"]
        motd_b = matches[best_idx]["team_b"]

        # Engaging contextual Uzbek hype templates (short & punchy 1-2 sentences)
        if ("ONIC" in motd_a or "ONIC" in motd_b) and ("RRQ" in motd_a or "RRQ" in motd_b):
            hype_text = f"Klassik Royal Derby! {motd_a} o‘tgan mag‘lubiyat uchun qasos olish va revansh qilishga shay!"
        elif "ONIC" in motd_a or "ONIC" in motd_b:
            hype_text = f"Bugun {motd_a} jamoasi {motd_b}ga qarshi o‘z qasosini olish va ochko yo‘qotmaslik uchun jangga kirishadi!"
        elif "AP.BREN" in motd_a or "AP.BREN" in motd_b:
            hype_text = f"Titanlar to‘qnashuvi! {motd_a} va {motd_b} o‘rtasida murosasiz shiddatli jang kutilmoqda."
        else:
            hype_text = f"Kunning eng muhim bahsi! Har ikki jamoa uchun bu to‘qnashuvda faqat g‘alaba zarur."

        return {
            "motd_index": best_idx,
            "motd_team_a": motd_a,
            "motd_team_b": motd_b,
            "hype_text": hype_text
        }

    @classmethod
    def format_matchday_caption(
        cls,
        league: str,
        date_str: str,
        matches: List[Dict[str, Any]],
        motd_info: Dict[str, Any]
    ) -> str:
        """
        Builds compliant, aesthetically formatted Telegram HTML caption.
        """
        is_ph = "PH" in league.upper()
        league_title = "MPL PHILIPPINES" if is_ph else "MPL INDONESIA"
        date_display = cls.format_uzbek_date_header(date_str)
        hashtag = "#MPLPH" if is_ph else "#MPLID"

        lines = [
            f"📅 <b>BUGUNGI O‘YINLAR DASTURI — {league_title}</b>",
            f"🗓 <i>Sana: {date_display}</i>",
            "",
            "⚔️ <b>Bugungi to‘qnashuvlar:</b>"
        ]

        numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        display_list = matches[:5]
        for i, m in enumerate(display_list):
            num_emoji = numbers[i] if i < len(numbers) else f"{i+1}."
            m_time = m.get("time", "15:00")
            ta = m.get("team_a")
            tb = m.get("team_b")
            series = m.get("series", "BO3")
            star = " ⭐" if m.get("is_motd") else ""
            lines.append(f"{num_emoji} <b>{m_time}</b> — <b>{ta} vs {tb}</b> [{series}]{star}")

        if len(matches) > 5:
            lines.append(f"<i>...va yana {len(matches) - 5} ta qiziqarli o‘yin!</i>")

        lines.append("")
        lines.append("⭐ <b>KUNNING MARKAZIY BAHSI:</b>")
        lines.append(f"👑 <b>{motd_info.get('motd_team_a')} ⚔️ {motd_info.get('motd_team_b')}</b>")
        
        hype = motd_info.get("hype_text", "").strip()
        if hype:
            lines.append(f"🎙 <i>{hype}</i>")

        lines.append("")
        lines.append("📺 <i>Jonli efir va o‘yin natijalarini kanalimizda kuzatib boring!</i>")
        lines.append(f"\n{hashtag} #MLBB #Esports #Jadval @murodalievgg\n")
        from app.ai.formatter import CHANNEL_FOOTER
        lines.append(CHANNEL_FOOTER)

        return "\n".join(lines)

    @classmethod
    def format_rest_day_caption(
        cls,
        league: str,
        today_date: str,
        next_matchday: Optional[Dict[str, Any]] = None,
        humor_text: Optional[str] = None
    ) -> str:
        """
        Builds a concise, authentic gamer-slang post for a rest day without boilerplate.
        """
        import random
        is_ph = "PH" in league.upper()
        league_title = "MPL PHILIPPINES" if is_ph else "MPL INDONESIA"
        hashtag = "#MPLPH" if is_ph else "#MPLID"
        today_display = cls.format_uzbek_date_header(today_date)

        if not humor_text:
            pool = cls.REST_DAY_SITUATIONAL_HUMORS.get("general", [])
            humor_text = random.choice(pool) if pool else "Bugun arenalarda rasmiy tanaffus! Solo rankda asabni asrang. 😉"

        lines = [
            f"🏖 <b>BUGUN TANAFFUS — {league_title}!</b>",
            f"🗓 <i>Sana: {today_display}</i>",
            "",
            f"<i>{humor_text}</i>",
            ""
        ]

        if next_matchday and next_matchday.get("matches"):
            next_date_str = next_matchday.get("date_display") or next_matchday.get("date")
            lines.append(f"📅 <b>Keyingi o‘yinlar ({next_date_str}):</b>")
            for m in next_matchday["matches"]:
                ta = m.get("team_a")
                tb = m.get("team_b")
                raw_time = m.get("time", "")
                m_time = raw_time.split(" / ")[0].replace("(UZ)", "").strip()
                if "Toshkent" not in m_time:
                    m_time = f"{m_time} (Toshkent)"
                lines.append(f"• <b>{ta} vs {tb}</b> — ⏰ {m_time}")
            lines.append("")

        lines.append(f"{hashtag} #MLBB #Esports @murodalievgg\n")
        from app.ai.formatter import CHANNEL_FOOTER
        lines.append(CHANNEL_FOOTER)
        return "\n".join(lines)

    @classmethod
    async def generate_matchday_post(
        cls,
        league: str = "MPL ID",
        target_date: Optional[str] = None,
        analyzer: Optional[AIAnalyzer] = None
    ) -> Dict[str, Any]:
        """
        Main entry point:
        Fetches matches, selects MOTD with AI hype, renders 1200x675 card, or returns witty rest day post.
        """
        date_str, matches, is_rest_day, next_matchday = await cls.get_matches_for_day(league, target_date)

        if is_rest_day:
            date_display = cls.format_uzbek_date_header(date_str)
            humor = await cls.generate_rest_day_humor(
                league=league,
                today_date=date_str,
                next_matchday=next_matchday,
                analyzer=analyzer
            )
            caption = cls.format_rest_day_caption(
                league=league,
                today_date=date_str,
                next_matchday=next_matchday,
                humor_text=humor
            )
            return {
                "success": True,
                "is_rest_day": True,
                "league": league,
                "date": date_str,
                "date_display": date_display,
                "matches": [],
                "motd": {},
                "image_bytes": None,
                "caption": caption,
                "message": caption,
                "next_matchday": next_matchday
            }

        if not matches:
            return {
                "success": False,
                "is_rest_day": False,
                "message": f"{league} uchun hozirda rejalashtirilgan o‘yinlar topilmadi."
            }

        # Analyze MOTD and generate hype
        motd_info = await cls.select_motd_and_generate_hype(league, date_str, matches, analyzer=analyzer)

        # Prepare render data
        date_display = cls.format_uzbek_date_header(date_str)
        render_data = {
            "league": league,
            "season": "SEASON 18",
            "date_display": date_display,
            "matches": matches
        }

        image_bytes = render_matchday_schedule(render_data)
        caption = cls.format_matchday_caption(league, date_str, matches, motd_info)
        from app.utils.html_utils import safe_trim_html
        caption = safe_trim_html(caption, max_len=1020)

        return {
            "success": True,
            "is_rest_day": False,
            "league": league,
            "date": date_str,
            "date_display": date_display,
            "matches": matches,
            "motd": motd_info,
            "image_bytes": image_bytes,
            "caption": caption
        }
