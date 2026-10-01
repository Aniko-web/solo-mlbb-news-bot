import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import httpx
from bs4 import BeautifulSoup

from app.utils.logger import logger
from app.utils.validators import RawCollectedItem, CategoryEnum, SourceReliability, utc_now

MONTH_MAP_ID = {
    "januari": "01", "februari": "02", "maret": "03", "april": "04",
    "mei": "05", "juni": "06", "juli": "07", "agustus": "08",
    "september": "09", "oktober": "10", "november": "11", "desember": "12",
    "agt": "08", "sep": "09", "okt": "10", "nov": "11", "des": "12"
}

MONTH_MAP_EN = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"
}

UZ_MONTHS = {
    "01": "YANVAR", "02": "FEVRAL", "03": "MART", "04": "APREL",
    "05": "MAY", "06": "IYUN", "07": "IYUL", "08": "AVGUST",
    "09": "SENTYABR", "10": "OKTABR", "11": "NOYABR", "12": "DEKABR"
}

ID_TEAM_NAME_MAP = {
    "EVOS": "EVOS GLORY",
    "RRQ": "RRQ HOSHI",
    "ONIC": "ONIC ID",
    "FNATIC ONIC": "ONIC ID",
    "ONIC ID": "ONIC ID",
    "BTR": "BIGETRON ALPHA",
    "BIGETRON": "BIGETRON ALPHA",
    "GEEK": "GEEK FAM",
    "AE": "ALTER EGO",
    "ALTER EGO": "ALTER EGO",
    "DEWA": "DEWA UNITED",
    "TLID": "TEAM LIQUID ID",
    "NAVI": "NATUS VINCERE",
    "RBL": "REBELLION ESPORTS"
}

PH_TEAM_NAME_MAP = {
    "RORA": "AURORA GAMING",
    "AURORA": "AURORA GAMING",
    "ONIC": "ONIC PH",
    "ONIC PH": "ONIC PH",
    "FNATIC ONIC PH": "ONIC PH",
    "FNATIC ONIC": "ONIC PH",
    "TLPH": "TEAM LIQUID PH",
    "FLCN": "TEAM FALCONS",
    "FALCONS": "TEAM FALCONS",
    "APBR": "AP.BREN",
    "BREN": "AP.BREN",
    "TWIS": "TWISTED MINDS",
    "OMG": "SMART OMEGA",
    "TNC": "TNC PRO TEAM",
    "BLCK": "BLACKLIST INT."
}


def _parse_id_date(raw_date: str) -> Tuple[str, str]:
    """Parse Indonesian date string (e.g. 'Jumat, 2 Oktober 2026') -> (ISO '2026-10-02', Uzbek '2 OKTABR 2026')."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw_date)
    if m:
        day_str = m.group(1)
        month_raw = m.group(2).lower()
        year_str = m.group(3)
        mo = MONTH_MAP_ID.get(month_raw, "10")
        iso = f"{year_str}-{mo}-{int(day_str):02d}"
        uz = f"{int(day_str)} {UZ_MONTHS.get(mo, 'OKTABR')} {year_str}"
        return iso, uz
    return utc_now().strftime("%Y-%m-%d"), raw_date


def _parse_ph_date(raw_date: str) -> Tuple[str, str]:
    """Parse Philippine/English date string (e.g. 'Friday, 21 August 2026') -> (ISO '2026-08-21', Uzbek '21 AVGUST 2026')."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw_date)
    if m:
        day_str = m.group(1)
        month_raw = m.group(2).lower()
        year_str = m.group(3)
        mo = MONTH_MAP_EN.get(month_raw, "08")
        iso = f"{year_str}-{mo}-{int(day_str):02d}"
        uz = f"{int(day_str)} {UZ_MONTHS.get(mo, 'AVGUST')} {year_str}"
        return iso, uz
    return utc_now().strftime("%Y-%m-%d"), raw_date


class MPLParserService:
    """
    Official Parser for MPL Indonesia (id-mpl.com) and MPL Philippines (ph-mpl.com).
    Converts live schedule/results DOM directly into Normalized JSON for Telegram Schedule & Result cards.
    """

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8"
    }

    @classmethod
    async def fetch_and_parse_mpl_id(cls, base_url: str = "https://id-mpl.com") -> List[Dict[str, Any]]:
        """
        Scrape https://id-mpl.com/schedule and return Normalized JSON for all matches.
        """
        schedule_url = f"{base_url.rstrip('/')}/schedule"
        try:
            async with httpx.AsyncClient(timeout=20.0, headers=cls.HEADERS, follow_redirects=True) as client:
                resp = await client.get(schedule_url)
                if resp.status_code != 200:
                    logger.warning(f"[MPL ID Parser] id-mpl.com returned status {resp.status_code}")
                    return []
                return cls.parse_mpl_id_html(resp.text, schedule_url)
        except Exception as e:
            logger.error(f"[MPL ID Parser] Failed to fetch {schedule_url}: {e}")
            return []

    @classmethod
    def parse_mpl_id_html(cls, html_content: str, source_url: str = "https://id-mpl.com/schedule") -> List[Dict[str, Any]]:
        """
        Parse raw HTML from id-mpl.com/schedule into structured Normalized JSON list.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        normalized_matches: List[Dict[str, Any]] = []

        # Detect Season from title (e.g. 'MPL Indonesia Season 14' or 'Season 17')
        season_label = "SEASON 14"
        title_text = soup.title.string if soup.title else ""
        sm = re.search(r"Season\s+(\d+)", title_text, re.IGNORECASE)
        if sm:
            season_label = f"SEASON {sm.group(1)}"

        # Search week containers: t-week-1 ... t-week-9
        for w_num in range(1, 12):
            w_el = soup.find(id=f"t-week-{w_num}")
            if not w_el:
                continue

            week_label = f"WEEK {w_num}"
            matches = w_el.find_all("div", class_=lambda c: c and "match" in c and "position-relative" in c)

            for m in matches:
                t1_el = m.find("div", class_=lambda c: c and "team1" in c)
                t2_el = m.find("div", class_=lambda c: c and "team2" in c)
                if not t1_el or not t2_el:
                    continue

                raw_t1 = t1_el.find(class_="name").get_text(strip=True) if t1_el.find(class_="name") else ""
                raw_t2 = t2_el.find(class_="name").get_text(strip=True) if t2_el.find(class_="name") else ""

                if not raw_t1 or not raw_t2:
                    continue

                team_a = ID_TEAM_NAME_MAP.get(raw_t1.upper(), raw_t1)
                team_b = ID_TEAM_NAME_MAP.get(raw_t2.upper(), raw_t2)

                t1_logo = t1_el.find("img")["src"] if t1_el.find("img") and "src" in t1_el.find("img").attrs else ""
                t2_logo = t2_el.find("img")["src"] if t2_el.find("img") and "src" in t2_el.find("img").attrs else ""

                # Scores
                scores = [s.get_text(strip=True) for s in m.find_all(class_="score")]
                score_a: Optional[int] = None
                score_b: Optional[int] = None
                if len(scores) >= 2 and scores[0].isdigit() and scores[1].isdigit():
                    score_a = int(scores[0])
                    score_b = int(scores[1])

                # Match Time (e.g. 15:00)
                time_el = m.find(class_="time")
                time_str = "15:00"
                if time_el:
                    pt1 = time_el.find(class_=lambda c: c and "pt-1" in c)
                    if pt1 and re.search(r"\b\d{1,2}:\d{2}\b", pt1.get_text()):
                        time_str = pt1.get_text(strip=True)
                    else:
                        tm = re.search(r"\b(\d{1,2}:\d{2})\b", time_el.get_text())
                        if tm:
                            time_str = tm.group(1)

                # Match Date
                date_el = m.find_previous_sibling(class_=lambda c: c and "date" in c)
                raw_date = date_el.get_text(strip=True) if date_el else ""
                iso_date, uz_date = _parse_id_date(raw_date)

                is_finished = score_a is not None and score_b is not None and (score_a >= 2 or score_b >= 2)
                status = "finished" if is_finished else "upcoming"

                winner = None
                if is_finished:
                    winner = team_a if score_a > score_b else team_b

                match_id = f"mpl_id_s{season_label.replace('SEASON ', '')}_w{w_num}_{raw_t1.lower()}_{raw_t2.lower()}_{iso_date.replace('-', '')}"

                normalized_matches.append({
                    "league": "MPL ID",
                    "season": season_label,
                    "stage": "REGULAR SEASON",
                    "week": week_label,
                    "match_id": match_id,
                    "team_a": team_a,
                    "team_a_code": raw_t1,
                    "team_a_logo": t1_logo,
                    "team_b": team_b,
                    "team_b_code": raw_t2,
                    "team_b_logo": t2_logo,
                    "score_a": score_a,
                    "score_b": score_b,
                    "winner": winner,
                    "date": iso_date,
                    "date_display": uz_date,
                    "time": f"{time_str} WIB",
                    "status": status,
                    "series": "BO3",
                    "source_url": source_url
                })

        return normalized_matches

    @classmethod
    async def fetch_and_parse_mpl_ph(cls, base_url: str = "https://ph-mpl.com") -> List[Dict[str, Any]]:
        """
        Scrape https://ph-mpl.com/schedule and return Normalized JSON for all matches.
        """
        schedule_url = f"{base_url.rstrip('/')}/schedule"
        try:
            async with httpx.AsyncClient(timeout=20.0, headers=cls.HEADERS, follow_redirects=True) as client:
                resp = await client.get(schedule_url)
                if resp.status_code != 200:
                    logger.warning(f"[MPL PH Parser] ph-mpl.com returned status {resp.status_code}")
                    return []
                return cls.parse_mpl_ph_html(resp.text, schedule_url)
        except Exception as e:
            logger.error(f"[MPL PH Parser] Failed to fetch {schedule_url}: {e}")
            return []

    @classmethod
    def parse_mpl_ph_html(cls, html_content: str, source_url: str = "https://ph-mpl.com/schedule") -> List[Dict[str, Any]]:
        """
        Parse raw HTML from ph-mpl.com/schedule into structured Normalized JSON list.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        normalized_matches: List[Dict[str, Any]] = []

        season_label = "SEASON 14"
        title_text = soup.title.string if soup.title else ""
        sm = re.search(r"Season\s+(\d+)", title_text, re.IGNORECASE)
        if sm:
            season_label = f"SEASON {sm.group(1)}"

        rows = soup.find_all(class_=lambda c: c and "col-12" in c and "col-lg-4" in c)

        for row in rows:
            day_no_el = row.find(class_="match-category-day-no")
            day_no_str = day_no_el.get_text(strip=True) if day_no_el else "DAY 1"

            day_date_el = row.find(class_=lambda c: c and "match-category-day" in c and "day-no" not in c)
            raw_date = day_date_el.get_text(strip=True) if day_date_el else ""
            iso_date, uz_date = _parse_ph_date(raw_date)

            for item in row.find_all(class_=lambda c: c and "schedule-item" in c):
                teams = [t.get_text(strip=True) for t in item.find_all(class_="team-name")]
                if len(teams) < 2:
                    continue

                raw_t1, raw_t2 = teams[0], teams[1]
                if raw_t1.upper() == "TBD" and raw_t2.upper() == "TBD":
                    continue

                team_a = PH_TEAM_NAME_MAP.get(raw_t1.upper(), raw_t1)
                team_b = PH_TEAM_NAME_MAP.get(raw_t2.upper(), raw_t2)

                imgs = item.find_all("img")
                t1_logo = imgs[0]["src"] if len(imgs) >= 1 and "src" in imgs[0].attrs else ""
                t2_logo = imgs[1]["src"] if len(imgs) >= 2 and "src" in imgs[1].attrs else ""

                time_el = item.find(style=lambda s: s and "0.9rem" in str(s))
                time_str = time_el.get_text(strip=True) if time_el else "5:00 PM"

                center_div = item.find("div", style=lambda s: s and ("1.5rem" in str(s) or "margin-top" in str(s)))
                center_text = center_div.get_text(strip=True) if center_div else ""

                score_a: Optional[int] = None
                score_b: Optional[int] = None
                score_match = re.search(r"(\d+)\s*:\s*(\d+)", center_text)
                if score_match:
                    score_a = int(score_match.group(1))
                    score_b = int(score_match.group(2))

                is_finished = score_a is not None and score_b is not None and (score_a >= 2 or score_b >= 2)
                status = "finished" if is_finished else "upcoming"

                winner = None
                if is_finished:
                    winner = team_a if score_a > score_b else team_b

                # Link
                link_el = item.find("a", href=True)
                match_link = link_el["href"] if link_el else source_url

                match_id = f"mpl_ph_s{season_label.replace('SEASON ', '')}_{day_no_str.lower().replace(' ', '')}_{raw_t1.lower()}_{raw_t2.lower()}_{iso_date.replace('-', '')}"

                normalized_matches.append({
                    "league": "MPL PH",
                    "season": season_label,
                    "stage": "REGULAR SEASON",
                    "week": day_no_str.upper(),
                    "match_id": match_id,
                    "team_a": team_a,
                    "team_a_code": raw_t1,
                    "team_a_logo": t1_logo,
                    "team_b": team_b,
                    "team_b_code": raw_t2,
                    "team_b_logo": t2_logo,
                    "score_a": score_a,
                    "score_b": score_b,
                    "winner": winner,
                    "date": iso_date,
                    "date_display": uz_date,
                    "time": f"{time_str} PHT",
                    "status": status,
                    "series": "BO3",
                    "source_url": match_link
                })

        return normalized_matches

    @classmethod
    def match_to_raw_collected_item(cls, match: Dict[str, Any]) -> RawCollectedItem:
        """
        Convert Normalized JSON dict into standard RawCollectedItem for scheduler processing.
        """
        league = match["league"]
        team_a = match["team_a"]
        team_b = match["team_b"]
        status = match["status"]
        date_str = match.get("date_display") or match.get("date")
        time_str = match.get("time", "")

        if status == "finished":
            title = f"{league} Natija: {team_a} {match.get('score_a', 0)} - {match.get('score_b', 0)} {team_b}"
            content = f"{league} {match.get('season', '')} | O'yin yakunlandi: {team_a} ({match.get('score_a', 0)}) vs {team_b} ({match.get('score_b', 0)}). G'olib: {match.get('winner', team_a)}."
        else:
            title = f"{league} Kutilayotgan o'yin: {team_a} vs {team_b}"
            content = f"{league} {match.get('season', '')} {match.get('week', '')} | Bo'lib o'tadi: {date_str} soat {time_str}."

        return RawCollectedItem(
            source_url=match.get("source_url", "https://id-mpl.com"),
            title=title,
            raw_content=content,
            category_hint=CategoryEnum.MPL_ID if "ID" in league else CategoryEnum.MPL_PH,
            source_name=f"Official {league}",
            source_type="OFFICIAL_MPL",
            reliability_score=SourceReliability.OFFICIAL_MPL,
            published_at=utc_now(),
            metadata=match
        )
