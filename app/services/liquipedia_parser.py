import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup

from app.utils.logger import logger
from app.utils.validators import MatchItem, RawCollectedItem, CategoryEnum, SourceReliability


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}

API_BASE = "https://liquipedia.net/mobilelegends/api.php"

# Team Name Normalizations to match assets/logos exactly
ID_TEAM_NAME_MAP = {
    "EVOS": "EVOS GLORY",
    "EVOS GLORY": "EVOS GLORY",
    "RRQ": "RRQ HOSHI",
    "RRQ HOSHI": "RRQ HOSHI",
    "ONIC": "ONIC ID",
    "ONIC ID": "ONIC ID",
    "FNATIC ONIC": "ONIC ID",
    "FNATIC ONIC ID": "ONIC ID",
    "FNOP": "ONIC ID",
    "BIGETRON": "BIGETRON ALPHA",
    "BIGETRON ALPHA": "BIGETRON ALPHA",
    "BIGETRON BY VITALITY": "BIGETRON ALPHA",
    "BTR": "BIGETRON ALPHA",
    "GEEK": "GEEK FAM",
    "GEEK FAM": "GEEK FAM",
    "GEEK FAM ID": "GEEK FAM",
    "ALTER EGO": "ALTER EGO",
    "AE": "ALTER EGO",
    "DEWA": "DEWA UNITED",
    "DEWA UNITED": "DEWA UNITED",
    "DEWA UNITED ESPORTS": "DEWA UNITED",
    "TEAM LIQUID ID": "TEAM LIQUID ID",
    "TLID": "TEAM LIQUID ID",
    "NATUS VINCERE": "NATUS VINCERE",
    "NAVI": "NATUS VINCERE",
    "REBELLION": "REBELLION ESPORTS",
    "REBELLION ESPORTS": "REBELLION ESPORTS",
    "RBL": "REBELLION ESPORTS",
}

PH_TEAM_NAME_MAP = {
    "AURORA": "AURORA GAMING",
    "AURORA PH": "AURORA GAMING",
    "AURORA GAMING": "AURORA GAMING",
    "RORA": "AURORA GAMING",
    "ONIC": "ONIC PH",
    "ONIC PH": "ONIC PH",
    "ONIC PHILIPPINES": "ONIC PH",
    "FNATIC ONIC PH": "ONIC PH",
    "FNATIC ONIC": "ONIC PH",
    "FNOP PH": "ONIC PH",
    "ONPH": "ONIC PH",
    "TEAM LIQUID PH": "TEAM LIQUID PH",
    "LIQUID PH": "TEAM LIQUID PH",
    "TLPH": "TEAM LIQUID PH",
    "TEAM FALCONS": "TEAM FALCONS",
    "FALCONS": "TEAM FALCONS",
    "FLCN": "TEAM FALCONS",
    "AP.BREN": "AP.BREN",
    "FALCONS AP.BREN": "AP.BREN",
    "APBR": "AP.BREN",
    "BREN": "AP.BREN",
    "TWISTED MINDS": "TWISTED MINDS",
    "TWISTED MINDS PH": "TWISTED MINDS",
    "TWPH": "TWISTED MINDS",
    "TWIS": "TWISTED MINDS",
    "SMART OMEGA": "SMART OMEGA",
    "SMART OMEGA PH": "SMART OMEGA",
    "OMEGA": "SMART OMEGA",
    "OMG": "SMART OMEGA",
    "TNC PRO TEAM": "TNC PRO TEAM",
    "TNC": "TNC PRO TEAM",
    "BLACKLIST INTERNATIONAL": "BLACKLIST INT.",
    "BLACKLIST": "BLACKLIST INT.",
    "BLCK": "BLACKLIST INT.",
}

UZ_MONTHS = {
    "01": "yanvar", "02": "fevral", "03": "mart", "04": "aprel",
    "05": "may", "06": "iyun", "07": "iyul", "08": "avgust",
    "09": "sentabr", "10": "oktabr", "11": "noyabr", "12": "dekabr"
}


def compute_countdown(target_dt: datetime) -> str:
    """Format human readable Uzbek countdown string."""
    now = datetime.now(timezone.utc)
    diff = int((target_dt - now).total_seconds())
    if diff <= 0:
        if diff > -7200:  # Started within last 2 hours
            return "🔥 O‘yin hozir davom etmoqda!"
        return "Tugagan"

    days = diff // 86400
    hours = (diff % 86400) // 3600
    minutes = (diff % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days} kun")
    if hours > 0 or days > 0:
        parts.append(f"{hours} soat")
    parts.append(f"{minutes} daqiqa")
    return " ".join(parts)


class LiquipediaParserService:
    """
    Parses live official tournament schedules, countdowns, start alerts,
    and match results from Liquipedia MediaWiki API.
    """

    @classmethod
    def normalize_team(cls, name: str, league: str) -> str:
        clean = (name or "").strip()
        upper = clean.upper()
        upper_stripped = upper.replace("FNATIC", "").strip()
        if "PH" in league:
            mapped = PH_TEAM_NAME_MAP.get(upper) or PH_TEAM_NAME_MAP.get(upper_stripped)
            if mapped:
                return mapped
            if "ONIC" in upper:
                return "ONIC PH"
            return clean
        else:
            mapped = ID_TEAM_NAME_MAP.get(upper) or ID_TEAM_NAME_MAP.get(upper_stripped)
            if mapped:
                return mapped
            if "ONIC" in upper:
                return "ONIC ID"
            return clean

    @classmethod
    async def _fetch_page_wikitext(cls, client: httpx.AsyncClient, page_title: str) -> Optional[str]:
        """Fetch raw wikitext of a page via Liquipedia API."""
        try:
            params = {
                "action": "query",
                "titles": page_title,
                "prop": "revisions",
                "rvprop": "content",
                "format": "json"
            }
            r = await client.get(API_BASE, params=params, headers=HEADERS, timeout=20.0)
            if r.status_code == 200:
                data = r.json()
                pages = data.get("query", {}).get("pages", {})
                for p_id, p_info in pages.items():
                    if p_id != "-1":
                        revs = p_info.get("revisions", [])
                        if revs and "*" in revs[0]:
                            return revs[0]["*"]
        except Exception as e:
            logger.warning(f"Failed to fetch wikitext for {page_title}: {e}")
        return None

    @classmethod
    async def _fetch_upcoming_match_infos(cls, client: httpx.AsyncClient, page_title: str) -> List[Dict[str, Any]]:
        """Fetch parsed HTML of main page to extract active match-info boxes with exact unix timestamps."""
        match_infos = []
        try:
            params = {
                "action": "parse",
                "page": page_title,
                "prop": "text",
                "format": "json"
            }
            r = await client.get(API_BASE, params=params, headers=HEADERS, timeout=20.0)
            if r.status_code == 200:
                html = r.json().get("parse", {}).get("text", {}).get("*", "")
                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    boxes = soup.find_all(class_="match-info")
                    for b in boxes:
                        timer = b.find(class_="timer-object")
                        ts = int(timer.get("data-timestamp")) if timer and timer.get("data-timestamp") else None

                        opps = b.find_all(class_="match-info-opponent-identity")
                        t1 = opps[0].get_text(strip=True) if len(opps) > 0 else ""
                        t2 = opps[1].get_text(strip=True) if len(opps) > 1 else ""

                        scores = b.find_all(class_="match-info-opponent-score")
                        s1 = scores[0].get_text(strip=True) if len(scores) > 0 else None
                        s2 = scores[1].get_text(strip=True) if len(scores) > 1 else None

                        match_infos.append({
                            "team_a_short": t1,
                            "team_b_short": t2,
                            "timestamp": ts,
                            "score_a_raw": s1,
                            "score_b_raw": s2,
                        })
        except Exception as e:
            logger.warning(f"Failed to parse match-info for {page_title}: {e}")
        return match_infos

    MONTH_MAP = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "june": 6, "jun": 6,
        "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12
    }

    @classmethod
    def parse_raw_datetime(cls, raw_date: str, league: str) -> tuple[str, str]:
        """
        Extracts ISO date (YYYY-MM-DD) and converts time to Tashkent format:
        '13:00 (UZ) / 15:00 (WIB)' or '14:00 (UZ) / 17:00 (PHT)'.
        """
        clean = re.sub(r"\{\{[^\}]+\}\}", "", raw_date).strip()
        iso_date = ""
        raw_time = "15:00"

        # 1. Match YYYY-MM-DD
        m_iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", clean)
        if m_iso:
            iso_date = f"{m_iso.group(1)}-{m_iso.group(2)}-{m_iso.group(3)}"
        else:
            # 2. Match Month Day, Year (supports 'August 21 , 2026' or 'Sep 11, 2026')
            m_txt = re.search(r"([A-Za-z]+)\s+(\d+)\s*,\s*(\d{4})", clean)
            if m_txt:
                m_name, d_str, y_str = m_txt.groups()
                m_num = cls.MONTH_MAP.get(m_name.lower())
                if m_num:
                    iso_date = f"{int(y_str):04d}-{m_num:02d}-{int(d_str):02d}"

        # Time extraction
        m_time = re.search(r"(\d{1,2}:\d{2})", clean)
        if m_time:
            raw_time = m_time.group(1)

        # Format with Tashkent time
        is_ph = "PH" in league.upper()
        try:
            h, m = map(int, raw_time.split(":"))
            if is_ph:
                # PHT is UTC+8, Tashkent is UTC+5 (-3 hours)
                tashkent_h = (h - 3) % 24
                formatted_time = f"{tashkent_h:02d}:{m:02d} (UZ) / {raw_time} (PHT)"
            else:
                # WIB is UTC+7, Tashkent is UTC+5 (-2 hours)
                tashkent_h = (h - 2) % 24
                formatted_time = f"{tashkent_h:02d}:{m:02d} (UZ) / {raw_time} (WIB)"
        except Exception:
            formatted_time = f"{raw_time} (Toshkent)"

        return iso_date or "TBD", formatted_time

    @classmethod
    def _parse_wikitext_matches(cls, wikitext: str, league: str, season_str: str) -> List[MatchItem]:
        """Parse wikitext matchlist blocks into MatchItem objects."""
        matches: List[MatchItem] = []
        week_blocks = re.findall(r"(\{\{Matchlist.*?)(?=\{\{Matchlist|\Z)", wikitext, re.DOTALL)

        for wb in week_blocks:
            w_match = re.search(r"title=Week\s*(\d+)", wb, re.IGNORECASE)
            week_num = w_match.group(1) if w_match else "1"

            match_templates = re.findall(r"\|M\d+=\s*(\{\{Match\b.*?\n\}\}\n)", wb, re.DOTALL)
            for m_str in match_templates:
                op1 = re.search(r"\|opponent1=\{\{TeamOpponent\|([^\|\}\n]+)", m_str)
                op2 = re.search(r"\|opponent2=\{\{TeamOpponent\|([^\|\}\n]+)", m_str)
                raw_t1 = op1.group(1).strip() if op1 else "Team A"
                raw_t2 = op2.group(1).strip() if op2 else "Team B"

                team_a = cls.normalize_team(raw_t1, league)
                team_b = cls.normalize_team(raw_t2, league)

                d_match = re.search(r"\|date=([^\|\n]+)", m_str)
                raw_date = d_match.group(1).strip() if d_match else ""

                iso_date, time_str = cls.parse_raw_datetime(raw_date, league)

                mvp_m = re.search(r"\|mvp=([^\n\|]*)", m_str)
                mvp = mvp_m.group(1).strip() if mvp_m else None
                if mvp == "":
                    mvp = None

                # Count map wins
                maps = re.findall(r"\|map\d+=\{\{Map\|(.*?)\}\}", m_str, re.DOTALL)
                score_1 = 0
                score_2 = 0
                has_finished_map = False
                for mp in maps:
                    w = re.search(r"\|winner=(\d+)", mp)
                    if w:
                        has_finished_map = True
                        if w.group(1) == "1":
                            score_1 += 1
                        elif w.group(1) == "2":
                            score_2 += 1

                is_finished = (score_1 >= 2 or score_2 >= 2)
                match_status = "finished" if is_finished else "upcoming"

                source_url = (
                    f"https://liquipedia.net/mobilelegends/MPL/{'Indonesia' if 'ID' in league else 'Philippines'}/{season_str.replace(' ', '_')}"
                )

                matches.append(MatchItem(
                    league=league,
                    team_a=team_a,
                    team_b=team_b,
                    date=iso_date,
                    time=time_str,
                    season=season_str,
                    week=week_num,
                    score_a=score_1 if is_finished else None,
                    score_b=score_2 if is_finished else None,
                    status=match_status,
                    mvp=mvp,
                    series="BO3",
                    source_url=source_url
                ))

        return matches

    @classmethod
    async def fetch_and_parse_mpl_id(cls, season: int = 18) -> List[MatchItem]:
        """Fetch and parse all official MPL ID matches from Liquipedia."""
        season_str = f"Season {season}"
        logger.info(f"[Liquipedia] Fetching MPL ID {season_str} from {API_BASE}...")

        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=25.0) as client:
            # 1. Fetch upcoming match-infos with timestamps
            upcoming_infos = await cls._fetch_upcoming_match_infos(client, f"MPL/Indonesia/Season_{season}")

            # 2. Fetch full Regular Season wikitext
            subpage = f"MPL/Indonesia/Season_{season}/Regular_Season"
            wikitext = await cls._fetch_page_wikitext(client, subpage)
            if not wikitext:
                wikitext = await cls._fetch_page_wikitext(client, f"MPL/Indonesia/Season_{season}")

            if not wikitext:
                logger.warning(f"[Liquipedia] Could not fetch wikitext for MPL ID {season_str}")
                return []

            matches = cls._parse_wikitext_matches(wikitext, "MPL ID", season_str)

            # 3. Enhance matches with timestamps from upcoming_infos
            for m in matches:
                for ui in upcoming_infos:
                    # Match by teams
                    u_t1 = cls.normalize_team(ui.get("team_a_short", ""), "MPL ID")
                    u_t2 = cls.normalize_team(ui.get("team_b_short", ""), "MPL ID")
                    if (u_t1 in m.team_a or m.team_a in u_t1) and (u_t2 in m.team_b or m.team_b in u_t2):
                        if ui.get("timestamp"):
                            ts = ui["timestamp"]
                            dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
                            # Convert to Tashkent time (UTC+5)
                            dt_tashkent = dt_utc + timedelta(hours=5)
                            m.date = dt_tashkent.strftime("%Y-%m-%d")
                            # Add Tashkent time info in time string
                            tashkent_time = dt_tashkent.strftime("%H:%M")
                            wib_time = (dt_utc + timedelta(hours=7)).strftime("%H:%M")
                            m.time = f"{tashkent_time} (UZ) / {wib_time} (WIB)"

            logger.info(f"[Liquipedia] Successfully parsed {len(matches)} MPL ID matches from Liquipedia.")
            return matches

    @classmethod
    async def fetch_and_parse_mpl_ph(cls, season: int = 18) -> List[MatchItem]:
        """Fetch and parse all official MPL PH matches from Liquipedia."""
        season_str = f"Season {season}"
        logger.info(f"[Liquipedia] Fetching MPL PH {season_str} from {API_BASE}...")

        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=25.0) as client:
            # 1. Fetch upcoming match-infos with timestamps
            upcoming_infos = await cls._fetch_upcoming_match_infos(client, f"MPL/Philippines/Season_{season}")

            # 2. Fetch full Regular Season wikitext
            subpage = f"MPL/Philippines/Season_{season}/Regular_Season"
            wikitext = await cls._fetch_page_wikitext(client, subpage)
            if not wikitext:
                wikitext = await cls._fetch_page_wikitext(client, f"MPL/Philippines/Season_{season}")

            if not wikitext:
                logger.warning(f"[Liquipedia] Could not fetch wikitext for MPL PH {season_str}")
                return []

            matches = cls._parse_wikitext_matches(wikitext, "MPL PH", season_str)

            # 3. Enhance matches with timestamps from upcoming_infos
            for m in matches:
                for ui in upcoming_infos:
                    u_t1 = cls.normalize_team(ui.get("team_a_short", ""), "MPL PH")
                    u_t2 = cls.normalize_team(ui.get("team_b_short", ""), "MPL PH")
                    if (u_t1 in m.team_a or m.team_a in u_t1) and (u_t2 in m.team_b or m.team_b in u_t2):
                        if ui.get("timestamp"):
                            ts = ui["timestamp"]
                            dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
                            dt_tashkent = dt_utc + timedelta(hours=5)
                            m.date = dt_tashkent.strftime("%Y-%m-%d")
                            tashkent_time = dt_tashkent.strftime("%H:%M")
                            pht_time = (dt_utc + timedelta(hours=8)).strftime("%H:%M")
                            m.time = f"{tashkent_time} (UZ) / {pht_time} (PHT)"

            logger.info(f"[Liquipedia] Successfully parsed {len(matches)} MPL PH matches from Liquipedia.")
            return matches

    @classmethod
    def match_to_raw_collected_item(cls, match: MatchItem) -> RawCollectedItem:
        """Convert MatchItem into RawCollectedItem for scheduler processing."""
        is_finished = match.status == "finished"
        title = (
            f"Natija: {match.team_a} {match.score_a} - {match.score_b} {match.team_b}"
            if is_finished
            else f"Kutilayotgan o'yin: {match.team_a} vs {match.team_b}"
        )

        # Build readable Uzbek date
        date_display = match.date
        try:
            parts = match.date.split("-")
            if len(parts) == 3:
                y, m, d = parts
                uz_m = UZ_MONTHS.get(m, m)
                date_display = f"{int(d)}-{uz_m}, {y}"
        except Exception:
            pass

        # Calculate countdown if upcoming
        countdown_str = None
        if not is_finished and match.date:
            try:
                # Approximate start time dt
                time_only = match.time.split()[0] if match.time else "15:00"
                full_dt_str = f"{match.date} {time_only}"
                target_dt = datetime.strptime(full_dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                countdown_str = compute_countdown(target_dt)
            except Exception:
                pass

        raw_content = (
            f"Liga: {match.league}\n"
            f"Jamoalar: {match.team_a} vs {match.team_b}\n"
            f"Holat: {match.status.upper()}\n"
            f"Hisob: {match.score_a if match.score_a is not None else '-'} : {match.score_b if match.score_b is not None else '-'}\n"
            f"Sana: {date_display} {match.time}\n"
            f"Hafta: {match.week}-hafta\n"
            f"Mavsum: {match.season}\n"
            f"Format: {match.series}\n"
            f"Manba: Liquipedia ({match.source_url})"
        )

        metadata = {
            "league": match.league,
            "team_a": match.team_a,
            "team_b": match.team_b,
            "date": match.date,
            "date_display": date_display,
            "time": match.time,
            "status": match.status,
            "score_a": match.score_a,
            "score_b": match.score_b,
            "mvp": match.mvp,
            "week": match.week,
            "season": match.season,
            "series": match.series,
            "countdown_str": countdown_str,
            "source": "Liquipedia"
        }

        return RawCollectedItem(
            source_url=match.source_url or "https://liquipedia.net/mobilelegends",
            title=title,
            raw_content=raw_content,
            category_hint=CategoryEnum.ESPORTS,
            image_url=None,
            source_name=f"Liquipedia {match.league}",
            source_type="ESPORTS",
            reliability_score=SourceReliability.TRUSTED_ESPORTS,
            published_at=datetime.now(),
            metadata=metadata
        )
