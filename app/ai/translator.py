import re
from typing import Dict, List


class UzbekTranslator:
    """
    Translates and localizes MLBB terms, sentences, and announcements into natural Uzbek.
    """

    MONTHS: Dict[str, str] = {
        "january": "Yanvar",
        "february": "Fevral",
        "march": "Mart",
        "april": "Aprel",
        "may": "May",
        "june": "Iyun",
        "july": "Iyul",
        "august": "Avgust",
        "september": "Sentyabr",
        "october": "Oktyabr",
        "november": "Noyabr",
        "december": "Dekabr",
    }

    ROLES: Dict[str, str] = {
        "assassin/fighter": "Qotil / Jangchi",
        "fighter/assassin": "Jangchi / Qotil",
        "marksman": "O‘qchi (Marksman)",
        "mage": "Sehrgar (Mage)",
        "tank": "Tank",
        "support": "Yordamchi (Support)",
        "assassin": "Qotil (Assassin)",
        "fighter": "Jangchi (Fighter)",
    }

    PATTERNS = [
        # Match results & schedules
        (r"secures a (\d+)\s*-\s*(\d+) victory over (.+?)\.", r"\3 ustidan \1 — \2 hisobida ishonchli g‘alabaga erishdi."),
        (r"defeats (.+?) with a score of (\d+)\s*-\s*(\d+)\.", r"\1 jamoasini \2 — \3 hisobida mag‘lubiyatga uchratdi."),
        (r"Regular Season Match", r"Muntazam mavsum uchrashuvi"),
        (r"Upcoming Regular Season match between (.+?) and (.+?)\.", r"\1 va \2 jamoalari o‘rtasidagi kutilayotgan uchrashuv."),
        (r"Final score:\s*(.+?)\s*\((\d+)\)\s*vs\s*(.+?)\s*\((\d+)\)", r"Yakuniy hisob: \1 (\2) — (\4) \3"),
        (r"Star MVP:\s*(.+?)\.", r"Uchrashuvning eng yaxshi o‘yinchisi (MVP): \1."),
        (r"MVP:\s*(.+?)\s*with\s*(.+?)\.", r"MVP: \1 (\2 qahramoni bilan)."),

        # Skins & Events
        (r"New Collector Skin '([^']+)' for ([a-zA-Z\s]+) will be released on ([a-zA-Z\s0-9,]+)\.",
         r"\2 uchun yangi '\1' Collector skini \3 da rasman o‘yinga qo‘shiladi."),
        (r"Available in Grand Collection event for approximately ([\d,]+)\s*(?:Diamonds)?.*",
         r"Grand Collection tadbiri orqali taxminan \1 olmos evaziga qo‘lga kiritish mumkin."),
        (r"Featuring celestial particle effects, cosmic voice lines, and unique recall animations\.",
         r"Unda samoviy zarralar effekti, yangi kosmik ovozlar va maxsus qaytish (recall) animatsiyasi mavjud."),

        # Hero spotlights & revamps
        (r"is the newest ([a-zA-Z/]+) arriving in the Land of Dawn\.",
         r"Land of Dawn jang maydoniga kirib kelayotgan eng yangi qahramon."),
        (r"Possesses dual forms:\s*Mortal stance for agility and Immortal stance for raw crushing power\.",
         r"U ikki xil jangovar holatga ega: chaqqonlik uchun Oddiy holat va kuchli zarba uchun O‘lmas holat."),
        (r"Skill 1:\s*([^,]+),\s*Skill 2:\s*([^,]+),\s*Ultimate:\s*([^\.]+)\.",
         r"1-qobiliyat: \1, 2-qobiliyat: \2, Ult qobiliyati: \3."),

        # Patch Notes Balance
        (r"Mobile Legends: Bang Bang Patch ([\d\.]+) is now live!",
         r"Mobile Legends: Bang Bang \1 yangilanishi o‘yinga rasman chiqarildi!"),
        (r"energy recovery increased from (\d+) to (\d+) per cable hit",
         r"arqon har zarbasida energiya tiklanishi \1 dan \2 ga oshirildi"),
        (r"Shadow Kill damage increased by (\d+)%",
         r"Shadow Kill zarari \1% ga oshirildi"),
        (r"damage increased by (\d+)%",
         r"zarari \1% ga oshirildi"),
        (r"cooldown increased from (\d+s) to (\d+s)",
         r"qayta tiklanish vaqti \1 dan \2 ga uzaytirildi"),
        (r"passive rift energy generation reduced slightly",
         r"passiv qobiliyatining energiya to‘plashi biroz kamaytirildi"),
        (r"basic attack animation smoothed and physical scaling optimized",
         r"asosiy hujum animatsiyasi ravonlashtirildi va jismoniy ko‘rsatkichlari optimallashtirildi"),
        (r"Battlefield visual updates and bug fixes for jungle creeps",
         r"Jang maydoni vizual yangilanishlari va o‘rmon maxluqlari xatoliklari tuzatildi"),

        # Esports & Tournaments
        (r"Moonton Games has officially announced the (.+?)!",
         r"Moonton Games rasman \1 boshlanishini e'lon qildi!"),
        (r"The pinnacle MLBB esports tournament will take place in ([^.]+)\.",
         r"MLBB bo‘yicha nufuzli chempionat \1 mezbonligida o‘tkaziladi."),
        (r"Total prize pool:\s*([^\.]+)\.",
         r"Umumiy mukofot jamg‘armasi: \1."),
        (r"Features Wildcard stage and Swiss Stage format for the first time in M-series history\.",
         r"M-Series tarixida birinchi marta Wildcard va Shveysarcha tizim (Swiss Stage) formati qo‘llaniladi."),
        (r"12 top Southeast Asian and international teams compete for ([^\s]+) in ([^.]+)\.",
         r"Janubi-sharqiy Osiyo va xalqaro 12 ta kuchli jamoa \2 da \1 sovrin jamg‘armasi uchun kurash olib boradi."),
        (r"Matches commence on ([^.]+)\.",
         r"Uchrashuvlar \1 sanasida boshlanadi.")
    ]

    TERM_REPLACEMENTS: Dict[str, str] = {
        "patch notes": "yangilanish tafsilotlari",
        "original server": "asosiy server",
        "advanced server": "sinov serveri",
        "hero adjustments": "qahramonlar balansi",
        "buff": "kuchaytirildi",
        "nerf": "zaiflashtirildi",
        "adjustment": "moslashtirildi",
        "new hero": "yangi qahramon",
        "new skin": "yangi skin",
        "collector skin": "Collector skini",
        "diamonds": "olmos",
        "diamond": "olmos",
        "regular season": "muntazam mavsum",
        "playoffs": "pley-off bosqichi",
        "upcoming match": "kutilayotgan o‘yin",
        "match result": "o‘yin natijasi",
        "schedule": "o‘yinlar jadvali",
        "world championship": "jahon chempionati",
        "prize pool": "mukofot jamg‘armasi",
        "defend": "himoyalash",
        "victory": "g‘alaba",
        "defeat": "mag‘lubiyat",
    }

    @classmethod
    def translate_sentence(cls, text: str) -> str:
        """
        Translates raw gaming announcements and phrases into natural Uzbek.
        """
        if not text:
            return ""

        result = text.strip()

        # Apply higher-level sentence patterns first
        for pattern, replacement in cls.PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        # Translate months
        for en_m, uz_m in cls.MONTHS.items():
            result = re.sub(rf"\b{en_m}\b", uz_m, result, flags=re.IGNORECASE)

        # Translate roles
        for en_r, uz_r in cls.ROLES.items():
            result = re.sub(rf"\b{re.escape(en_r)}\b", uz_r, result, flags=re.IGNORECASE)

        # Term replacements
        for en, uz in cls.TERM_REPLACEMENTS.items():
            result = re.sub(rf"\b{re.escape(en)}\b", uz, result, flags=re.IGNORECASE)

        # Clean excess spaces
        result = re.sub(r"\s+", " ", result).strip()
        return result

    @classmethod
    def localize_term(cls, text: str) -> str:
        return cls.translate_sentence(text)

    @classmethod
    def clean_gaming_text(cls, text: str) -> str:
        cleaned = re.sub(r"©\s*\d{4}\s*Moonton.*", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"All rights reserved.*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"Terms of Service.*", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()
