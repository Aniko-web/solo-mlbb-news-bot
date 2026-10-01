from typing import List, Optional
from app.collectors.base import SourceCollector
from app.utils.logger import logger
from app.utils.validators import RawCollectedItem, SourceReliability
from app.config.settings import get_settings
from app.services.liquipedia_parser import LiquipediaParserService
from app.services.mpl_parser import MPLParserService

settings = get_settings()


class MPLIDCollector(SourceCollector):
    """
    Collector for MPL Indonesia (Liquipedia Season 18) schedules, countdowns, and results.
    Directly parses Liquipedia MediaWiki API and outputs Normalized JSON.
    """

    def __init__(self, base_url: Optional[str] = None):
        url = base_url or "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_18"
        super().__init__(
            name="MPL Indonesia",
            source_type="ESPORTS",
            base_url=url,
            reliability_score=SourceReliability.TRUSTED_ESPORTS
        )

    async def fetch(self) -> List[RawCollectedItem]:
        items: List[RawCollectedItem] = []
        try:
            matches_data = await LiquipediaParserService.fetch_and_parse_mpl_id(season=18)
            if not matches_data:
                logger.warning(f"[{self.name}] Liquipedia empty, falling back to official id-mpl.com...")
                fallback_matches = await MPLParserService.fetch_and_parse_mpl_id()
                for m in fallback_matches:
                    items.append(MPLParserService.match_to_raw_collected_item(m))
            else:
                for m in matches_data:
                    items.append(LiquipediaParserService.match_to_raw_collected_item(m))
                logger.info(f"[{self.name}] Successfully parsed {len(items)} matches from Liquipedia Season 18")
        except Exception as e:
            logger.error(f"[{self.name}] Error during Liquipedia MPL ID fetch: {e}", exc_info=True)
            try:
                fallback_matches = await MPLParserService.fetch_and_parse_mpl_id()
                for m in fallback_matches:
                    items.append(MPLParserService.match_to_raw_collected_item(m))
            except Exception:
                pass

        return items
