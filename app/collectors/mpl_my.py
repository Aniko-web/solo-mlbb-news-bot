from typing import List, Optional
from app.collectors.base import SourceCollector
from app.utils.logger import logger
from app.utils.validators import RawCollectedItem, SourceReliability
from app.config.settings import get_settings
from app.services.liquipedia_parser import LiquipediaParserService

settings = get_settings()


class MPLMYCollector(SourceCollector):
    """
    Collector for MPL Malaysia (Liquipedia Season 16/17) schedules, countdowns, and results.
    Directly parses Liquipedia MediaWiki API and outputs Normalized items.
    """

    def __init__(self, base_url: Optional[str] = None):
        url = base_url or "https://liquipedia.net/mobilelegends/MPL/Malaysia/Season_16"
        super().__init__(
            name="MPL Malaysia",
            source_type="ESPORTS",
            base_url=url,
            reliability_score=SourceReliability.TRUSTED_ESPORTS
        )

    async def fetch(self) -> List[RawCollectedItem]:
        items: List[RawCollectedItem] = []
        try:
            matches_data = await LiquipediaParserService.fetch_and_parse_mpl_my(season=16)
            if not matches_data:
                matches_data = await LiquipediaParserService.fetch_and_parse_mpl_my(season=15)

            for m in matches_data:
                items.append(LiquipediaParserService.match_to_raw_collected_item(m))
            logger.info(f"[{self.name}] Successfully parsed {len(items)} matches from Liquipedia")
        except Exception as e:
            logger.error(f"[{self.name}] Error during Liquipedia MPL MY fetch: {e}", exc_info=True)

        return items

