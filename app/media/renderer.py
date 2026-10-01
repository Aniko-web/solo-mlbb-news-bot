from typing import Dict, Any
from app.utils.logger import logger
from app.media.templates.mpl_id import render_mpl_id_result, render_mpl_id_upcoming
from app.media.templates.mpl_ph import render_mpl_ph_result, render_mpl_ph_upcoming
from app.media.templates.patch_recap import render_patch_recap
from app.media.templates.matchday_card import render_matchday_card


def render_matchday_schedule(matchday_data: Dict[str, Any]) -> bytes:
    """
    Renders multi-match daily schedule card in 1200x675 PNG.
    """
    league = str(matchday_data.get("league") or "MPL ID").upper()
    logger.info(f"Rendering Matchday Schedule graphic for {league} ({len(matchday_data.get('matches', []))} matches)")
    return render_matchday_card(matchday_data)


def render_match_result(match_data: Dict[str, Any]) -> bytes:
    """
    Route match result rendering to the dedicated league template.
    Returns 1200x675 PNG bytes.
    """
    league = str(match_data.get("league") or "MPL ID").upper().strip()

    if "ID" in league or "INDONESIA" in league:
        logger.info(f"Rendering MPL ID result graphic for {match_data.get('team_a')} vs {match_data.get('team_b')}")
        return render_mpl_id_result(match_data)
    elif "PH" in league or "PHILIPPINES" in league:
        logger.info(f"Rendering MPL PH result graphic for {match_data.get('team_a')} vs {match_data.get('team_b')}")
        return render_mpl_ph_result(match_data)
    else:
        # Default to MPL ID theme for generic leagues
        logger.info(f"Defaulting league '{league}' to MPL ID result template")
        return render_mpl_id_result(match_data)


def render_match_upcoming(match_data: Dict[str, Any]) -> bytes:
    """
    Route upcoming match rendering to the dedicated league template.
    Returns 1200x675 PNG bytes.
    """
    league = str(match_data.get("league") or "MPL ID").upper().strip()

    if "ID" in league or "INDONESIA" in league:
        logger.info(f"Rendering MPL ID upcoming graphic for {match_data.get('team_a')} vs {match_data.get('team_b')}")
        return render_mpl_id_upcoming(match_data)
    elif "PH" in league or "PHILIPPINES" in league:
        logger.info(f"Rendering MPL PH upcoming graphic for {match_data.get('team_a')} vs {match_data.get('team_b')}")
        return render_mpl_ph_upcoming(match_data)
    else:
        logger.info(f"Defaulting league '{league}' to MPL ID upcoming template")
        return render_mpl_id_upcoming(match_data)


def render_match_graphic(match_data: Dict[str, Any]) -> bytes:
    """
    Automatic master router: detects whether the match is finished/live result
    or an upcoming/postponed match, and selects the exact league template.
    """
    status = str(match_data.get("status") or "").upper().strip()
    score_a = match_data.get("score_a")
    score_b = match_data.get("score_b")

    is_upcoming = (
        status in ("UPCOMING", "POSTPONED", "CANCELLED", "SCHEDULED")
        or (score_a is None and score_b is None and "LIVE" not in status)
    )

    if is_upcoming:
        return render_match_upcoming(match_data)
    else:
        return render_match_result(match_data)
