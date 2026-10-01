import random
import json
import re
from typing import Dict, Any, Optional, Tuple
from openai import AsyncOpenAI

from app.config.settings import get_settings
from app.utils.logger import logger
from app.media.templates.fun_card import render_fun_card

settings = get_settings()

CURATED_FUN_POOL = [
    # 1. FACTS (Geymercha Qiziqarli Faktlar)
    {
        "topic_type": "FACT",
        "hero_name": "Franco",
        "title": "FRANCONING ENGI ASABBUZAR FINTI",
        "content": "Bilasizmi, bratva? Franco MLBB chiqqanidan beri eng birinchi tanklardan biri. Eng yomon hiylasi — 1-levelda dushman lesnigining ko'k bafini kustga ilib tortib olish! Dushman janglerining asabi tamom bo'lib, butun katka farm qilolmay yig'lab yuradi.",
        "hashtags": ["#mlbb_fakt", "#franco", "#murodalievgg", "#mobilelegends"]
    },
    {
        "topic_type": "FACT",
        "hero_name": "Fanny",
        "title": "FANNY VA SKRIPKACHI BARMOQLAR",
        "content": "Fanny o'ynaydiganlarning barmoqlari haqiqiy pianinochi bo'lsa kerak! Qo'li kelishgan pro-geymer bitta ko'k baf bilan 1 soniyada 4-5 ta tros otib, butun kartani 3 soniyada aylanib chiqadi. Siz 'qayerdan keldi bu?' deb ulgurmasingizdan shota qilib uchib ketgan bo'ladi!",
        "hashtags": ["#mlbb_fakt", "#fanny", "#murodalievgg", "#mobilelegends"]
    },
    {
        "topic_type": "FACT",
        "hero_name": "Layla",
        "title": "LAYLANING CHEKSIZ DISTANSIYASI",
        "content": "Layla 15-level bo'lganda, otish masofasi shunaqa uzoq bo'ladiki, bechora minoraning (turret) o'zi ham hayron qoladi! Hech qanaqa minion kutmasdan, minora zonasiga kirmasdan turib uzoqdan bemalol yorib tashlaydi. Faqat o'yin boshida 0/5 bo'lib fid qilmasa bo'lgani!",
        "hashtags": ["#mlbb_fakt", "#layla", "#murodalievgg", "#marksman"]
    },
    {
        "topic_type": "FACT",
        "hero_name": "Chou",
        "title": "CHOU — ABADIY META QAHRAMONI",
        "content": "Moonton Chouga qancha nerf bermasin, u baribir metada yashab qoladi! Bruce Lee harakatlariga asoslangan bu qahramon 8 yildan beri har qanday turnirda pick qilinadi. Kustda pisib yotib, dushman adksini tepib olib ketish — uning eng sevimli ishi.",
        "hashtags": ["#mlbb_fakt", "#chou", "#murodalievgg", "#esports"]
    },
    {
        "topic_type": "FACT",
        "hero_name": "Johnson",
        "title": "LAND OF DAWN TAXISI",
        "content": "Johnson ulti bosib moshinaga aylanganda, tezligi har qanday Zilong yoki Lingdan ham oshib ketadi. Eng dahshatlisi — unga bitta Kadita yoki Odette o'tirib olsa, dushmanning 5 ta odami bir soniyada bazaga tekin bilet oladi!",
        "hashtags": ["#mlbb_fakt", "#johnson", "#murodalievgg", "#combo"]
    },
    {
        "topic_type": "FACT",
        "hero_name": "Aldous",
        "title": "500 STACKLIK SHOTA",
        "content": "Aldous katka davomida minionlarni erinmay urib 500 ta stak yig'ib olsa, xaritada qochishning umuman foydasi yo'q! Bitta 1-skilli bilan har qanday mage yoki marksman bir zarbada yo'q bo'ladi. Laytda Aldous ulti bosishi — bu eng katta dahshat.",
        "hashtags": ["#mlbb_fakt", "#aldous", "#murodalievgg", "#late_game"]
    },

    # 2. JOKES & MEMES (Real Hayotiy Geymer Memlari)
    {
        "topic_type": "JOKE",
        "hero_name": "Angela",
        "title": "SOLO RANKDAGI ENG KATTA XIYONAT",
        "content": "Kustda 1v4 qolib, joningiz 5% qolganida zo'rg'a urishyapsiz. Jamoadagi Angela ulti bosadi deb duo qilib yotibsiz... Lekin qarasangiz, Angela ultini orqada to'liq joni bilan minion urib turgan do'stiga bosib, ikkalasi bazaga qochib ketvotti! Og'riqni faqat solo rankchilar biladi.",
        "hashtags": ["#mlbb_hazil", "#mem", "#angela", "#murodalievgg"]
    },
    {
        "topic_type": "JOKE",
        "hero_name": "Franco",
        "title": "ILMOG'ING QANI, UKAM?",
        "content": "Dushman Layla qimirlamay turgan paytda: bizning Franco hookni yonidagi tovuqdek minionga uradi. Ammo dushman qochayotganda esa — hook o'zimizning timmeytga tegib qaytadi! Chatda esa standart bahona tayyor: 'Bratva, pingim 120ms bo'lib qoldi, qotib qoldim'!",
        "hashtags": ["#mlbb_hazil", "#franco", "#mem", "#murodalievgg"]
    },
    {
        "topic_type": "JOKE",
        "hero_name": "Layla",
        "title": "MYTHICGA 1 YULDUZ QOLGANDA...",
        "content": "Mythicga chiqishga rosa 1 ta yulduz qolgan: draftda 1-o'yinchi Layla oladi, 2-o'yinchi Miya, 3-o'yinchi esa Hanabi! Tanka o't desangiz — 'men faqat keri o'ynayman, tank o'ynolmayman' deb laynga chopadi. Natijada 10-daqiqada 'Defend base' deb yig'lab o'tirasiz.",
        "hashtags": ["#mlbb_hazil", "#solorank", "#mem", "#murodalievgg"]
    },
    {
        "topic_type": "JOKE",
        "hero_name": "Eudora",
        "title": "KUSTDAN CHIQIB KELGAN SOVG'A",
        "content": "Kustdan o'tayotib 'shu yerda hech kim yo'qdir' deb beparvo yurasiz. Birdaniga butadan Eudora sakrab chiqib 2-1-Ulti prokatkasini yoqadi! Nima bo'lganini tushunmay, telefonni tushirib yuborib qora-oq ekranga 40 soniya tikilib o'tirasiz.",
        "hashtags": ["#mlbb_hazil", "#eudora", "#mem", "#kust"]
    },
    {
        "topic_type": "JOKE",
        "hero_name": "Balmond",
        "title": "LORD VA RETRI FOJIASI",
        "content": "Butun komanda bo'lib 1 daqiqa qiynalib Lordni urib, joni 2 sm qolganida: dushman Balmond kalla tashlab keladi-da, ulti bilan Lordni o'g'irlab ketadi! Bizning lesnikning Retri tugmasi esa shunchaki krasiviy bezak bo'lib qoladi.",
        "hashtags": ["#mlbb_hazil", "#balmond", "#retri", "#lord"]
    },

    # 3. LORE & HISTORY (Qahramonlar Tarixi — Sodda va Jonli)
    {
        "topic_type": "LORE",
        "hero_name": "Dyrroth",
        "title": "DYRROTH VA SILVANNA DRAMASI",
        "content": "Bilasizmi, Dyrroth aslida Moniyan imperiyasining shahzodasi va Silvannaning tug'ishgan ukasi bo'lgan! Kichkinaligida Abyss jinlari o'g'irlab ketib, qorong'ulik kuchlari bilan yovuz qilib tarbiyalagan. Hozir esa bir-birini tanimay, laynlarda ayovsiz urishib yurishadi.",
        "hashtags": ["#mlbb_lore", "#dyrroth", "#silvanna", "#murodalievgg"]
    },
    {
        "topic_type": "LORE",
        "hero_name": "Gusion",
        "title": "PAXLEY KLANIDAGI BEBOSh GUSION",
        "content": "Gusion aristokrat Paxley xonadonining eng erka va iqtidorli bolasi bo'lgan. Ota-onasi 'faqat sehr o'rgan' desa, bu xanjar bilan tezkorlikni tanlagan. Qoidalarga bo'ysunmagani uchun uydan haydalgan, lekin hozir Land of Dawnda eng mashhur asassin!",
        "hashtags": ["#mlbb_lore", "#gusion", "#aamon", "#murodalievgg"]
    },
    {
        "topic_type": "LORE",
        "hero_name": "Alucard",
        "title": "ALUCARDNING SIRLI ISMI",
        "content": "'ALUCARD' so'zini teskarisiga o'qib ko'rganmisiz? 'DRACULA' so'zi kelib chiqadi! U ota-onasining qasosi uchun vampirlar va jinlarni birma-bir yanchib yuruvchi jinlar ovchisi hisoblanadi.",
        "hashtags": ["#mlbb_lore", "#alucard", "#murodalievgg", "#tarix"]
    },

    # 4. PRO TIPS (Geymercha Foydali Maslahatlar)
    {
        "topic_type": "TIP",
        "hero_name": "Tigreal",
        "title": "KUSTLARNI TEKSHIRISH ODATI",
        "content": "Hech qachon shubhali kustlarga yuzingiz bilan kirmang, bratva! Agar Flameshotingiz yoki uzoqdan uradigan skillingiz bo'lsa, oldin butaga oting. Dushman mini-kartadan yo'qolib qoldimi — demak u yo Lordda, yoki aynan siz yurgan yo'ldagi kustda poylab yotibdi!",
        "hashtags": ["#mlbb_maslahat", "#pro_tip", "#murodalievgg", "#guide"]
    },
    {
        "topic_type": "TIP",
        "hero_name": "Baxia",
        "title": "ANTI-XILSIZ G'ALOBA YO'Q",
        "content": "Dushmanda Estes, Floryn, Yu Zhong yoki Ruby kabi 'vampirlar' bo'lsa: 'jonini to'ldiryapti' deb yig'lamasdan birinchi bo'lib Anti-xil (Dominance Ice, Sea Halberd yoki Glowing Wand) yig'ing! 50% jon tiklashini kesasiz, aks holda butun katka ularni o'ldirolmay boshingiz qotadi.",
        "hashtags": ["#mlbb_maslahat", "#antiheal", "#murodalievgg", "#items"]
    }
]


class FunContentGenerator:
    """
    Generates captivating MLBB facts, jokes/memes, lore, and pro tips
    using Google Gemini with an authentic Uzbek gamer slang tone, plus curated fallback pool.
    """

    def __init__(self):
        self.api_key = settings.active_ai_key
        self.base_url = settings.AI_BASE_URL
        self.model = settings.AI_MODEL
        self.client: Optional[AsyncOpenAI] = None

        if self.api_key and self.api_key.strip():
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=18.0,
                max_retries=1
            )

    async def generate_fun_post(self) -> Dict[str, Any]:
        """
        Produce a fun item (Fact, Joke, Lore, Tip) with an official 1200x675 visual graphic.
        """
        raw_data = None
        if self.client:
            try:
                raw_data = await self._generate_with_gemini()
            except Exception as e:
                logger.warning(f"Gemini fun content generation failed, using curated pool: {e}")

        if not raw_data:
            raw_data = random.choice(CURATED_FUN_POOL)

        topic_type = raw_data.get("topic_type", "FACT").upper()
        title = raw_data.get("title", "MLBB QIZIQARLI FAKT").upper()
        content = raw_data.get("content", "")
        hero_name = raw_data.get("hero_name")
        hashtags = raw_data.get("hashtags", ["#mlbb", "#murodalievgg"])

        formatted_caption = self._format_telegram_caption(
            topic_type=topic_type,
            title=title,
            content=content,
            hashtags=hashtags,
            hero_name=hero_name
        )

        image_bytes = render_fun_card(
            topic_type=topic_type,
            title=title,
            content=content,
            hero_name=hero_name
        )

        return {
            "topic_type": topic_type,
            "title": title,
            "content": content,
            "hero_name": hero_name,
            "formatted_caption": formatted_caption,
            "image_bytes": image_bytes
        }

    async def _generate_with_gemini(self) -> Optional[Dict[str, Any]]:
        """Call Gemini to create unique, engaging MLBB fun facts or humor using gamer slang."""
        topic_choice = random.choice(["FACT", "JOKE", "LORE", "TIP"])
        heroes_sample = [
            "Franco", "Fanny", "Layla", "Chou", "Johnson", "Angela",
            "Aldous", "Balmond", "Gusion", "Dyrroth", "Tigreal", "Ling",
            "Hayabusa", "Nana", "Zilong", "Estes", "Miya", "Saber", "Gusion"
        ]
        chosen_hero = random.choice(heroes_sample)

        prompt = (
            f"Sen Mobile Legends: Bang Bang (MLBB) bo'yicha O'zbekistondagi eng mashhur va o'yinchilar tilini mukammal biladigan geymer muharririsan.\n"
            f"Vazifa: MLBB bo'yicha o'zbek o'yinchilari va geymerlariga atalgan o'ta qiziqarli, kulgili va samimiy post yarat.\n\n"
            f"Tanlangan mavzu turi: {topic_choice}\n"
            f"- FACT: Mobile Legends sirlari, o'yin mexanikasi, qahramon haqidagi ajoyib geymercha fakt\n"
            f"- JOKE: O'zbek MLBB o'yinchilari uchun kulgili, real va hayotiy hazil/mem (solo rank, feeding, afk, troll piklar, asab buzilishlar, feyllar)\n"
            f"- LORE: Land of Dawn tarixi, qahramonlar o'rtasidagi drama yoki munosabat (sodda, qiziqarli tilda)\n"
            f"- TIP: Pro o'yinchilardan 1 ta aniq va foydali taktik geymercha layfxak/maslahat\n\n"
            f"Tavsiya etiladigan qahramon (ixtiyoriy): {chosen_hero}\n\n"
            f"MUHIM USLUB TALABLARI (QAT'IY):\n"
            f"1. Rasmiy, kitobiy yoki jiddiy tildan ASLO FOYDALANMA!\n"
            f"2. Haqiqiy o'zbek MLBB geymerlari katkalarda ishlatadigan jonli so'zlashuv tilidan foydalan: masalan, katka, farm, kust, fid qilish, fider, solo rank, ulti, retri, one-shot, shota qilish, baf, lesnik, adk, timmeyt, sliv, troll pik, epik kabi atamalarni tabiiy ishlat.\n"
            f"3. Matn samimiy, kulgili, jonli va emojilar bilan yozilsin (2-3 qisqa jumla, 100-220 belgi).\n"
            f"4. Qaytariladigan format faqat toza JSON bo'lsin:\n"
            f"{{\n"
            f'  "topic_type": "{topic_choice}",\n'
            f'  "hero_name": "{chosen_hero}",\n'
            f'  "title": "Qisqa, jozibali sarlavha (KATTA HARFLARDA)",\n'
            f'  "content": "Geymercha jonli so\'zlashuv tilidagi matn...",\n'
            f'  "hashtags": ["#mlbb", "#murodalievgg", "#{chosen_hero.lower()}"]\n'
            f"}}"
        )

        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Sen faqat JSON qaytaruvchi, haqiqiy o'zbek geymer tilida yozuvchi MLBB ustasisan."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.85,
            response_format={"type": "json_object"}
        )

        raw_content = resp.choices[0].message.content or ""
        data = json.loads(raw_content)
        if "title" in data and "content" in data:
            return data
        return None

    def _format_telegram_caption(
        self,
        topic_type: str,
        title: str,
        content: str,
        hashtags: list[str],
        hero_name: Optional[str]
    ) -> str:
        """Format caption with rich Telegram HTML styling and emojies."""
        headers = {
            "FACT": "💡 <b>MLBB QIZIQARLI FAKT & BILASIZMI?</b>",
            "JOKE": "🎭 <b>MLBB HAYOTIY HAZIL & MEM</b>",
            "MEME": "🎭 <b>MLBB HAYOTIY HAZIL & MEM</b>",
            "LORE": "⚔️ <b>LAND OF DAWN AFSONALARI & TARIXI</b>",
            "TIP": "🧠 <b>PRO GEYMER MASLAHATI & LAYFXAK</b>"
        }
        header_text = headers.get(topic_type.upper(), "💡 <b>MLBB QIZIQARLI GEYMER POSTI</b>")

        callouts = {
            "FACT": "💬 <i>Siz bu haqida bilarmidingiz? Fikringizni izohlarda yozing!</i>",
            "JOKE": "😂 <i>Sizda ham shunaqa katka bo'lganmi? Do'stlaringizga yuboring!</i>",
            "MEME": "😂 <i>Sizda ham shunaqa katka bo'lganmi? Do'stlaringizga yuboring!</i>",
            "LORE": "📖 <i>Land of Dawn olamining qaysi qahramoni tarixi sizga eng qiziq?</i>",
            "TIP": "🎯 <i>Keyingi katkada buni albatta sinab ko'ring!</i>"
        }
        callout = callouts.get(topic_type.upper(), "💬 <i>Fikringizni izohlarda qoldiring!</i>")

        tags_str = " ".join(hashtags) if hashtags else "#mlbb #murodalievgg"

        caption = (
            f"{header_text}\n\n"
            f"📌 <b>{title.upper()}</b>\n\n"
            f"{content.strip()}\n\n"
            f"{callout}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏆 <b>MLBB UZ</b> — @murodalievgg\n"
            f"{tags_str}"
        )
        return caption
