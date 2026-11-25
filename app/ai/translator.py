import re
from typing import Dict, List, Optional


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


class RussianTranslator:
    """
    Translates and localizes MLBB terms, sentences, and announcements into natural Russian.
    """

    MONTHS: Dict[str, str] = {
        "january": "Января",
        "february": "Февраля",
        "march": "Марта",
        "april": "Апреля",
        "may": "Мая",
        "june": "Июня",
        "july": "Июля",
        "august": "Августа",
        "september": "Сентября",
        "october": "Октября",
        "november": "Ноября",
        "december": "Декабря",
    }

    ROLES: Dict[str, str] = {
        "assassin/fighter": "Убийца / Боец",
        "fighter/assassin": "Боец / Убийца",
        "marksman": "Стрелок (Marksman)",
        "mage": "Маг (Mage)",
        "tank": "Танк (Tank)",
        "support": "Поддержка (Support)",
        "assassin": "Убийца (Assassin)",
        "fighter": "Боец (Fighter)",
    }

    PATTERNS = [
        # Match results & schedules
        (r"secures a (\d+)\s*-\s*(\d+) victory over (.+?)\.", r"Одерживает победу над \3 со счетом \1 — \2."),
        (r"defeats (.+?) with a score of (\d+)\s*-\s*(\d+)\.", r"Побеждает команду \1 со счетом \2 — \3."),
        (r"Regular Season Match", r"Матч регулярного сезона"),
        (r"Upcoming Regular Season match between (.+?) and (.+?)\.", r"Предстоящий матч регулярного сезона между \1 и \2."),
        (r"Final score:\s*(.+?)\s*\((\d+)\)\s*vs\s*(.+?)\s*\((\d+)\)", r"Итоговый счет: \1 (\2) — (\4) \3"),
        (r"Star MVP:\s*(.+?)\.", r"Лучший игрок матча (MVP): \1."),
        (r"MVP:\s*(.+?)\s*with\s*(.+?)\.", r"MVP матча: \1 (герой \2)."),

        # Skins & Events
        (r"New Collector Skin '([^']+)' for ([a-zA-Z\s]+) will be released on ([a-zA-Z\s0-9,]+)\.",
         r"Новый скин Collector '\1' для героя \2 выходит \3."),
        (r"Available in Grand Collection event for approximately ([\d,]+)\s*(?:Diamonds)?.*",
         r"Доступен в событии Grand Collection примерно за \1 алмазов."),
        (r"Featuring celestial particle effects, cosmic voice lines, and unique recall animations\.",
         r"Включает космические визуальные эффекты, новые реплики и уникальную анимацию возвращения."),

        # Hero spotlights & revamps
        (r"is the newest ([a-zA-Z/]+) arriving in the Land of Dawn\.",
         r"Новейший герой, прибывающий на поля сражений Land of Dawn."),
        (r"Possesses dual forms:\s*Mortal stance for agility and Immortal stance for raw crushing power\.",
         r"Обладает двумя формами: форма ловкости и форма сокрушительной мощи."),
        (r"Skill 1:\s*([^,]+),\s*Skill 2:\s*([^,]+),\s*Ultimate:\s*([^\.]+)\.",
         r"1-й навык: \1, 2-й навык: \2, Ультимейт: \3."),

        # Patch Notes Balance
        (r"Mobile Legends: Bang Bang Patch ([\d\.]+) is now live!",
         r"Обновление Mobile Legends: Bang Bang \1 официально вышло на серверах!"),
        (r"energy recovery increased from (\d+) to (\d+) per cable hit",
         r"восстановление энергии увеличено с \1 до \2 за попадание тросом"),
        (r"Shadow Kill damage increased by (\d+)%",
         r"урон Shadow Kill увеличен на \1%"),
        (r"damage increased by (\d+)%",
         r"урон увеличен на \1%"),
        (r"cooldown increased from (\d+s) to (\d+s)",
         r"время перезарядки увеличено с \1 до \2"),
        (r"passive rift energy generation reduced slightly",
         r"накопление энергии пассивного навыка немного уменьшено"),
        (r"basic attack animation smoothed and physical scaling optimized",
         r"анимация базовой атаки сглажена и оптимизировано физическое масштабирование"),
        (r"Battlefield visual updates and bug fixes for jungle creeps",
         r"Визуальные обновления поля боя и исправления лесных монстров"),

        # Esports & Tournaments
        (r"Moonton Games has officially announced the (.+?)!",
         r"Moonton Games официально объявили о начале \1!"),
        (r"The pinnacle MLBB esports tournament will take place in ([^.]+)\.",
         r"Главный киберспортивный турнир по MLBB пройдет в \1."),
        (r"Total prize pool:\s*([^\.]+)\.",
         r"Общий призовой фонд: \1."),
        (r"Features Wildcard stage and Swiss Stage format for the first time in M-series history\.",
         r"Впервые в истории серии турниров применяется этап Wildcard и швейцарская система."),
        (r"Matches commence on ([^.]+)\.",
         r"Матчи начнутся: \1.")
    ]

    TERM_REPLACEMENTS: Dict[str, str] = {
        "patch notes": "список изменений обновления",
        "original server": "основной сервер",
        "advanced server": "тестовый сервер",
        "hero adjustments": "баланс героев",
        "buff": "усилен (бафф)",
        "nerf": "ослаблен (нерф)",
        "adjustment": "корректировка",
        "new hero": "новый герой",
        "new skin": "новый скин",
        "collector skin": "скин Collector",
        "diamonds": "алмазов",
        "diamond": "алмаз",
        "regular season": "регулярный сезон",
        "playoffs": "плей-офф",
        "upcoming match": "предстоящий матч",
        "match result": "результат матча",
        "schedule": "расписание матчей",
        "world championship": "чемпионат мира",
        "prize pool": "призовой фонд",
        "defend": "защита",
        "victory": "победа",
        "defeat": "поражение",
    }

    HERO_RU_MAP: Dict[str, str] = {
        "aamon": "Аамон",
        "akai": "Акай",
        "aldous": "Алдос",
        "alice": "Алиса",
        "alpha": "Альфа",
        "alucard": "Алукард",
        "angela": "Ангела",
        "argus": "Аргус",
        "arlott": "Арлотт",
        "atlas": "Атлас",
        "aulus": "Аулус",
        "aurora": "Аврора",
        "badang": "Баданг",
        "balmond": "Бальмонд",
        "bane": "Бейн",
        "barats": "Баратс",
        "baxia": "Баксий",
        "beatrix": "Беатрис",
        "belerick": "Белерик",
        "benedetta": "Бенедетта",
        "brody": "Броуди",
        "bruno": "Бруно",
        "carmilla": "Кармилла",
        "cecilion": "Сесилион",
        "change": "Чан'э",
        "chang'e": "Чан'э",
        "chip": "Чип",
        "chou": "Чоу",
        "cici": "Чичи",
        "claude": "Клод",
        "clint": "Клинт",
        "cyclops": "Циклоп",
        "diggie": "Дигги",
        "dyrroth": "Дариус",
        "edith": "Эдит",
        "esmeralda": "Эсмеральда",
        "estes": "Эстес",
        "eudora": "Эйдора",
        "fanny": "Фанни",
        "faramis": "Фарамис",
        "floryn": "Флорин",
        "franco": "Франко",
        "fredrinn": "Фредринн",
        "freya": "Фрея",
        "gatotkaca": "Гатоткача",
        "gloo": "Глу",
        "gord": "Горд",
        "granger": "Грейнджер",
        "grock": "Грок",
        "guinevere": "Гвиневра",
        "gusion": "Госсен",
        "hanabi": "Ханаби",
        "hanzo": "Ханзо",
        "harith": "Харит",
        "harley": "Харли",
        "hayabusa": "Хаябуса",
        "helcurt": "Хелкарт",
        "hilda": "Хильда",
        "hylos": "Хилос",
        "irithel": "Иритель",
        "ixia": "Иксия",
        "jawhead": "Кусака",
        "johnson": "Джонсон",
        "joy": "Джой",
        "julian": "Джулиан",
        "kadita": "Кадита",
        "kagura": "Кагура",
        "kaja": "Кажа",
        "kalea": "Калея",
        "karina": "Карина",
        "karrie": "Кэрри",
        "khaleed": "Халид",
        "khufra": "Хуфра",
        "kimmy": "Кимми",
        "lancelot": "Ланселот",
        "lapu-lapu": "Лапу-Лапу",
        "lapulapu": "Лапу-Лапу",
        "layla": "Лейла",
        "leomord": "Леоморд",
        "lesley": "Лесли",
        "ling": "Линг",
        "lolita": "Лолита",
        "lukas": "Лукас",
        "lunox": "Люнокс",
        "luo-yi": "Ло Йи",
        "luoyi": "Ло Йи",
        "lylia": "Лилия",
        "martis": "Мартис",
        "masha": "Маша",
        "mathilda": "Матильда",
        "melissa": "Мелисса",
        "minotaur": "Минотавр",
        "minsitthar": "Минситтар",
        "miya": "Мия",
        "moskov": "Москов",
        "nana": "Нана",
        "natalia": "Наталья",
        "natan": "Натан",
        "nolan": "Нолан",
        "novaria": "Новария",
        "obsidia": "Обсидия",
        "odette": "Одетта",
        "paquito": "Пакито",
        "pharsa": "Фарса",
        "phoveus": "Фовиус",
        "popol-and-kupa": "Пополь и Купа",
        "popol and kupa": "Пополь и Купа",
        "popolkupa": "Пополь и Купа",
        "rafaela": "Рафаэль",
        "roger": "Роджер",
        "ruby": "Руби",
        "saber": "Сабер",
        "selena": "Селена",
        "silvanna": "Сильвана",
        "sun": "Сан",
        "suyou": "Сую",
        "terizla": "Теризла",
        "thamuz": "Тамуз",
        "tigreal": "Тигриал",
        "uranus": "Уранус",
        "vale": "Вейл",
        "valentina": "Валентина",
        "valir": "Валир",
        "vexana": "Вексана",
        "wanwan": "Ванван",
        "xavier": "Ксавье",
        "x.borg": "Икс.Борг",
        "xborg": "Икс.Борг",
        "yin": "Инь",
        "yi sun-shin": "Ли Сун-син",
        "yisunshin": "Ли Сун-син",
        "yu zhong": "Ю Чжон",
        "yuzhong": "Ю Чжон",
        "yve": "Ив",
        "zhask": "Заск",
        "zhuxin": "Чжусинь",
        "zilong": "Зилонг",
    }

    ITEMS_RU_MAP: Dict[str, str] = {
        # Defense
        "blade armor": "Броня клинка",
        "antique cuirass": "Древняя кираса",
        "wind of nature": "Ветер природы",
        "dominance ice": "Господство льда",
        "athena's shield": "Щит Афины",
        "athenas shield": "Щит Афины",
        "radiant armor": "Сияющая броня",
        "immortality": "Бессмертие",
        "twilight armor": "Сумеречная броня",
        "guardian helmet": "Шлем защитника",
        "brute force breastplate": "Кираса грубой силы",
        "oracle": "Оракул",
        "cursed helmet": "Проклятый шлем",
        "thunder belt": "Пояс грома",
        "queen's wings": "Крылья королевы",
        "queens wings": "Крылья королевы",
        # Physical Attack
        "blade of despair": "Клинок отчаяния",
        "malefic roar": "Злобный рык",
        "demon hunter sword": "Меч охотника на демонов",
        "berserker's fury": "Ярость берсерка",
        "berserkers fury": "Ярость берсерка",
        "endless battle": "Бесконечная битва",
        "windtalker": "Говорящий с ветром",
        "corrosion scythe": "Коса коррозии",
        "golden staff": "Золотой посох",
        "haas's claws": "Когти Хааса",
        "haass claws": "Когти Хааса",
        "haas claws": "Когти Хааса",
        "war axe": "Топор войны",
        "hunter strike": "Удар охотника",
        "bloodlust axe": "Топор кровожадности",
        "sea halberd": "Трезубец",
        "rose gold meteor": "Метеор золотой розы",
        "great dragon spear": "Копье Великого Дракона",
        "sky piercer": "Пронзатель небес",
        "malefic gun": "Злобная пушка",
        # Magic
        "holy crystal": "Священный кристалл",
        "blood wings": "Крылья крови",
        "clock of destiny": "Часы судьбы",
        "lightning truncheon": "Жезл молний",
        "genius wand": "Палочка гения",
        "glowing wand": "Светящийся жезл",
        "divine glaive": "Божественный меч",
        "concentrated energy": "Концентрированная энергия",
        "ice queen wand": "Жезл королевы льда",
        "fleeting time": "Мимолетное время",
        "wishing lantern": "Фонарь желаний",
        "starlium scythe": "Коса Звездного света",
        "feather of heaven": "Райское перо",
        "winter crown": "Зимняя корона",
        "winter truncheon": "Зимний жезл",
        "enchanted talisman": "Зачарованный талисман",
        "necklace of durance": "Ожерелье заточения",
        # Boots
        "warrior boots": "Сапоги воина",
        "tough boots": "Прочные сапоги",
        "swift boots": "Сапоги скорохода",
        "arcane boots": "Сапоги заклинателя",
        "magic shoes": "Магическая обувь",
        "demon shoes": "Обувь демона",
        "rapid boots": "Быстрые сапоги",
    }

    HERO_RU_ALIASES: Dict[str, str] = {
        "и сун-син": "yi-sun-shin",
        "и сун син": "yi-sun-shin",
        "ли сун син": "yi-sun-shin",
        "ли сун-син": "yi-sun-shin",
        "юй чжун": "yu-zhong",
        "юйчжун": "yu-zhong",
        "ю чжун": "yu-zhong",
        "ю чжон": "yu-zhong",
        "иксборг": "xborg",
        "икс борг": "xborg",
        "пополь и купа": "popol-and-kupa",
        "пополь купа": "popol-and-kupa",
        "чан э": "change",
        "чанэ": "change",
        "лапу лапу": "lapu-lapu",
        "лапу-лапу": "lapu-lapu",
        "луо и": "luo-yi",
        "луо-и": "luo-yi",
    }

    HERO_RU_MAP: Dict[str, str] = {
        "aamon": "Аамон",
        "akai": "Акай",
        "aldous": "Алдос",
        "alice": "Алиса",
        "alpha": "Альфа",
        "alucard": "Алукард",
        "angela": "Ангела",
        "argus": "Аргус",
        "arlott": "Арлотт",
        "atlas": "Атлас",
        "aulus": "Аулус",
        "aurora": "Аврора",
        "badang": "Баданг",
        "balmond": "Бальмонд",
        "bane": "Бейн",
        "barats": "Баратс",
        "baxia": "Баксий",
        "beatrix": "Беатрис",
        "belerick": "Белерик",
        "benedetta": "Бенедетта",
        "brody": "Броуди",
        "bruno": "Бруно",
        "carmilla": "Кармилла",
        "cecilion": "Сесилион",
        "change": "Чан'э",
        "chang'e": "Чан'э",
        "chip": "Чип",
        "chou": "Чоу",
        "cici": "Чичи",
        "claude": "Клод",
        "clint": "Клинт",
        "cyclops": "Циклоп",
        "diggie": "Дигги",
        "dyrroth": "Дариус",
        "edith": "Эдит",
        "esmeralda": "Эсмеральда",
        "estes": "Эстес",
        "eudora": "Эйдора",
        "fanny": "Фанни",
        "faramis": "Фарамис",
        "floryn": "Флорин",
        "franco": "Франко",
        "fredrinn": "Фредринн",
        "freya": "Фрея",
        "gatotkaca": "Гатоткача",
        "gloo": "Глу",
        "gord": "Горд",
        "granger": "Грейнджер",
        "grock": "Грок",
        "guinevere": "Гвиневра",
        "gusion": "Госсен",
        "hanabi": "Ханаби",
        "hanzo": "Ханзо",
        "harith": "Харит",
        "harley": "Харли",
        "hayabusa": "Хаябуса",
        "helcurt": "Хелкарт",
        "hilda": "Хильда",
        "hylos": "Хилос",
        "irithel": "Иритель",
        "ixia": "Иксия",
        "jawhead": "Джохед",
        "johnson": "Джонсон",
        "joy": "Джой",
        "julian": "Джулиан",
        "kadita": "Кадита",
        "kagura": "Кагура",
        "kaja": "Каджа",
        "kalea": "Калея",
        "karina": "Карина",
        "karrie": "Кэрри",
        "khaleed": "Халид",
        "khufra": "Хуфра",
        "kimmy": "Кимми",
        "lancelot": "Ланселот",
        "lapu-lapu": "Лапу-Лапу",
        "lapulapu": "Лапу-Лапу",
        "layla": "Лейла",
        "leomord": "Леоморд",
        "lesley": "Лесли",
        "ling": "Линг",
        "lolita": "Лолита",
        "lukas": "Лукас",
        "lunox": "Люнокс",
        "luo-yi": "Ло Йи",
        "luoyi": "Ло Йи",
        "lylia": "Лилия",
        "martis": "Мартис",
        "masha": "Маша",
        "mathilda": "Матильда",
        "melissa": "Мелисса",
        "minotaur": "Минотавр",
        "minsitthar": "Минситтар",
        "miya": "Мия",
        "moskov": "Москов",
        "nana": "Нана",
        "natalia": "Наталья",
        "natan": "Натан",
        "nolan": "Нолан",
        "novaria": "Новария",
        "obsidia": "Обсидия",
        "odette": "Одетта",
        "paquito": "Пакито",
        "pharsa": "Фарса",
        "phoveus": "Фовиус",
        "popol-and-kupa": "Пополь и Купа",
        "popol and kupa": "Пополь и Купа",
        "popolkupa": "Пополь и Купа",
        "rafaela": "Рафаэль",
        "roger": "Роджер",
        "ruby": "Руби",
        "saber": "Сабер",
        "selena": "Селена",
        "silvanna": "Сильвана",
        "sun": "Сан",
        "suyou": "Сую",
        "terizla": "Теризла",
        "thamuz": "Тамуз",
        "tigreal": "Тигриал",
        "uranus": "Уранус",
        "vale": "Вейл",
        "valentina": "Валентина",
        "valir": "Валир",
        "vexana": "Вексана",
        "wanwan": "Ванван",
        "xavier": "Ксавье",
        "x.borg": "Икс.Борг",
        "xborg": "Икс.Борг",
        "yin": "Инь",
        "yi sun-shin": "Ли Сун-син",
        "yisunshin": "Ли Сун-син",
        "yu zhong": "Ю Чжон",
        "yuzhong": "Ю Чжон",
        "yve": "Ив",
        "zhask": "Заск",
        "zhuxin": "Чжусинь",
        "zilong": "Зилонг",
    }

    ITEMS_RU_MAP: Dict[str, str] = {
        # Defense
        "blade armor": "Броня клинка",
        "antique cuirass": "Древняя кираса",
        "wind of nature": "Ветер природы",
        "dominance ice": "Господство льда",
        "athena's shield": "Щит Афины",
        "athenas shield": "Щит Афины",
        "radiant armor": "Сияющая броня",
        "immortality": "Бессмертие",
        "twilight armor": "Сумеречная броня",
        "guardian helmet": "Шлем защитника",
        "brute force breastplate": "Кираса грубой силы",
        "oracle": "Оракул",
        "cursed helmet": "Проклятый шлем",
        "thunder belt": "Пояс грома",
        "queen's wings": "Крылья королевы",
        "queens wings": "Крылья королевы",
        # Physical Attack
        "blade of despair": "Клинок отчаяния",
        "malefic roar": "Злобный рык",
        "demon hunter sword": "Меч охотника на демонов",
        "berserker's fury": "Ярость берсерка",
        "berserkers fury": "Ярость берсерка",
        "endless battle": "Бесконечная битва",
        "windtalker": "Говорящий с ветром",
        "corrosion scythe": "Коса коррозии",
        "golden staff": "Золотой посох",
        "haas's claws": "Когти Хааса",
        "haass claws": "Когти Хааса",
        "haas claws": "Когти Хааса",
        "war axe": "Топор войны",
        "hunter strike": "Удар охотника",
        "bloodlust axe": "Топор кровожадности",
        "sea halberd": "Трезубец",
        "rose gold meteor": "Метеор золотой розы",
        "great dragon spear": "Копье Великого Дракона",
        "sky piercer": "Пронзатель небес",
        "malefic gun": "Злобная пушка",
        # Magic
        "holy crystal": "Священный кристалл",
        "blood wings": "Крылья крови",
        "clock of destiny": "Часы судьбы",
        "lightning truncheon": "Жезл молний",
        "genius wand": "Палочка гения",
        "glowing wand": "Светящийся жезл",
        "divine glaive": "Божественный меч",
        "concentrated energy": "Концентрированная энергия",
        "ice queen wand": "Жезл королевы льда",
        "fleeting time": "Мимолетное время",
        "wishing lantern": "Фонарь желаний",
        "starlium scythe": "Коса Звездного света",
        "feather of heaven": "Райское перо",
        "winter crown": "Зимняя корона",
        "winter truncheon": "Зимний жезл",
        "enchanted talisman": "Зачарованный талисман",
        "necklace of durance": "Ожерелье заточения",
        # Boots
        "warrior boots": "Сапоги воина",
        "tough boots": "Прочные сапоги",
        "swift boots": "Сапоги скорохода",
        "arcane boots": "Сапоги заклинателя",
        "magic shoes": "Магическая обувь",
        "demon shoes": "Обувь демона",
        "rapid boots": "Быстрые сапоги",
    }

    HERO_RU_ALIASES: Dict[str, str] = {
        "и сун-син": "yi-sun-shin",
        "и сун син": "yi-sun-shin",
        "ли сун син": "yi-sun-shin",
        "ли сун-син": "yi-sun-shin",
        "юй чжун": "yu-zhong",
        "юйчжун": "yu-zhong",
        "ю чжун": "yu-zhong",
        "ю чжон": "yu-zhong",
        "иксборг": "xborg",
        "икс борг": "xborg",
        "пополь и купа": "popol-and-kupa",
        "пополь купа": "popol-and-kupa",
        "чан э": "change",
        "чанэ": "change",
        "лапу лапу": "lapu-lapu",
        "лапу-лапу": "lapu-lapu",
        "луо и": "luo-yi",
        "луо-и": "luo-yi",
    }

    @classmethod
    def translate_hero_name(cls, name: str) -> str:
        """Translates MLBB hero name into official Russian name."""
        if not name:
            return ""
        clean = name.strip()
        low = clean.lower()
        if low in cls.HERO_RU_MAP:
            return cls.HERO_RU_MAP[low]
        # Check normalized key without punctuation
        key = low.replace("'", "").replace(".", "").replace("-", "").replace(" ", "")
        for k, ru_name in cls.HERO_RU_MAP.items():
            if k.replace("'", "").replace(".", "").replace("-", "").replace(" ", "") == key:
                return ru_name
        return clean

    @classmethod
    def lookup_hero_by_russian(cls, cyrillic_name: str) -> Optional[str]:
        """Looks up English hero name given a Russian/Cyrillic hero name."""
        if not cyrillic_name:
            return None
        low = cyrillic_name.strip().lower()

        # Check aliases first
        if low in cls.HERO_RU_ALIASES:
            return cls.HERO_RU_ALIASES[low]

        normalized_cyrillic = low.replace("-", " ").replace(".", "").strip()
        if normalized_cyrillic in cls.HERO_RU_ALIASES:
            return cls.HERO_RU_ALIASES[normalized_cyrillic]

        for en_name, ru_name in cls.HERO_RU_MAP.items():
            if ru_name.lower() == low:
                return en_name
        # Substring / partial match fallback
        for en_name, ru_name in cls.HERO_RU_MAP.items():
            if ru_name.lower() in low or low in ru_name.lower():
                return en_name
        return None

    @classmethod
    def translate_items(cls, items_str: str, include_en: bool = True) -> str:
        """
        Translates comma-separated MLBB item names into Russian.
        Example: 'Blade Armor, Antique Cuirass, Wind of Nature' ->
        'Броня клинка (Blade Armor), Древняя кираса (Antique Cuirass), Ветер природы (Wind of Nature)'
        """
        if not items_str:
            return ""
        items_list = [it.strip() for it in items_str.split(",") if it.strip()]
        translated_items = []
        for it in items_list:
            clean_it = it.strip().rstrip(".")
            it_key = clean_it.lower().replace("'", "")
            ru_name = cls.ITEMS_RU_MAP.get(clean_it.lower()) or cls.ITEMS_RU_MAP.get(it_key)
            if ru_name:
                if include_en:
                    translated_items.append(f"{ru_name} ({clean_it})")
                else:
                    translated_items.append(ru_name)
            else:
                translated_items.append(clean_it)
        return ", ".join(translated_items)

    @classmethod
    def translate_sentence(cls, text: str) -> str:
        """
        Translates raw gaming announcements and phrases into natural Russian.
        """
        if not text:
            return ""

        result = text.strip()

        # Apply higher-level sentence patterns first
        for pattern, replacement in cls.PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        # Translate months
        for en_m, ru_m in cls.MONTHS.items():
            result = re.sub(rf"\b{en_m}\b", ru_m, result, flags=re.IGNORECASE)

        # Translate roles
        for en_r, ru_r in cls.ROLES.items():
            result = re.sub(rf"\b{re.escape(en_r)}\b", ru_r, result, flags=re.IGNORECASE)

        # Term replacements
        for en, ru in cls.TERM_REPLACEMENTS.items():
            result = re.sub(rf"\b{re.escape(en)}\b", ru, result, flags=re.IGNORECASE)

        # Clean excess spaces
        result = re.sub(r"\s+", " ", result).strip()
        return result

    @classmethod
    def localize_term(cls, text: str) -> str:
        return cls.translate_sentence(text)
