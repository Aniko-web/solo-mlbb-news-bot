import re
import hashlib
from typing import Dict, Any, List, Optional
from aiogram import Bot

from app.config.settings import get_settings
from app.utils.logger import logger
from app.utils.validators import utc_now, CategoryEnum, PostStatus
from app.database.database import get_session
from app.database.repositories import PostRepository
from app.media.image_processor import ImageProcessor
from app.ai.formatter import PostFormatter
from app.telegram.publisher import TelegramPublisher
from app.telegram.admin import AdminNotifier

settings = get_settings()


def parse_patch_text(text: str) -> Dict[str, Any]:
    """
    Parse patch details from natural text or command arguments.
    Supports both pipe-separated syntax:
      '1.9.42 | Fanny, Franco | Lancelot, Granger | Harith, Chou | Kalea'
    and labeled multiline syntax:
      Versiya: 1.9.42
      Server: ORIGINAL SERVER
      Buff: Fanny, Franco, Baxia
      Nerf: Lancelot, Granger
      Adjustment: Harith, Chou
      Revamp: Kalea
      Tavsif: Yangi qahramonlar balansi
    """
    clean_text = text.strip()
    result = {
        "version": "1.9.xx",
        "server": "ORIGINAL SERVER",
        "buffs": [],
        "nerfs": [],
        "adjustments": [],
        "revamps": [],
        "summary": ""
    }

    # Remove leading command if present (e.g. /newpatch or /patch)
    if clean_text.startswith(("/newpatch", "/patch", "/fastpatch")):
        lines = clean_text.splitlines()
        first_line = lines[0]
        cmd_parts = first_line.split(maxsplit=1)
        if len(cmd_parts) > 1:
            clean_text = cmd_parts[1] + ("\n" + "\n".join(lines[1:]) if len(lines) > 1 else "")
        else:
            clean_text = "\n".join(lines[1:]).strip()

    if not clean_text:
        return result

    # Check for Pipe separated syntax (e.g. version | buffs | nerfs | adjustments | revamps)
    if "|" in clean_text and "\n" not in clean_text:
        parts = [p.strip() for p in clean_text.split("|")]
        if len(parts) >= 1 and parts[0]:
            result["version"] = parts[0]
        if len(parts) >= 2 and parts[1]:
            result["buffs"] = [h.strip() for h in parts[1].split(",") if h.strip()]
        if len(parts) >= 3 and parts[2]:
            result["nerfs"] = [h.strip() for h in parts[2].split(",") if h.strip()]
        if len(parts) >= 4 and parts[3]:
            result["adjustments"] = [h.strip() for h in parts[3].split(",") if h.strip()]
        if len(parts) >= 5 and parts[4]:
            result["revamps"] = [h.strip() for h in parts[4].split(",") if h.strip()]
        return result

    # Multiline / Key-Value parsing
    lines = [ln.strip() for ln in clean_text.splitlines() if ln.strip()]
    for line in lines:
        lower = line.lower()
        if any(lower.startswith(k) for k in ["versiya:", "version:", "v:"]):
            val = line.split(":", 1)[1].strip()
            if val:
                result["version"] = val
        elif any(lower.startswith(k) for k in ["server:", "svr:"]):
            val = line.split(":", 1)[1].strip().upper()
            if "ADV" in val:
                result["server"] = "ADVANCED SERVER"
            else:
                result["server"] = "ORIGINAL SERVER"
        elif any(lower.startswith(k) for k in ["buff:", "buffs:", "kuchaytirildi:", "kuchaytirilgan:"]):
            val = line.split(":", 1)[1].strip()
            result["buffs"] = [h.strip() for h in val.split(",") if h.strip()]
        elif any(lower.startswith(k) for k in ["nerf:", "nerfs:", "zaiflashtirildi:", "zaif:"]):
            val = line.split(":", 1)[1].strip()
            result["nerfs"] = [h.strip() for h in val.split(",") if h.strip()]
        elif any(lower.startswith(k) for k in ["adjustment:", "adjustments:", "moslashtirildi:", "ozgarish:"]):
            val = line.split(":", 1)[1].strip()
            result["adjustments"] = [h.strip() for h in val.split(",") if h.strip()]
        elif any(lower.startswith(k) for k in ["revamp:", "revamps:", "yangilandi:"]):
            val = line.split(":", 1)[1].strip()
            result["revamps"] = [h.strip() for h in val.split(",") if h.strip()]
        elif any(lower.startswith(k) for k in ["tavsif:", "summary:", "info:", "izoh:"]):
            val = line.split(":", 1)[1].strip()
            result["summary"] = val
        elif not result.get("version") or result["version"] == "1.9.xx":
            # Attempt to extract version if standing on its own
            ver_match = re.search(r"(\d+\.\d+\.\d+[a-z]?)", line)
            if ver_match:
                result["version"] = ver_match.group(1)

    return result


async def create_patch_post(
    version: str,
    buffs: Optional[List[str]] = None,
    nerfs: Optional[List[str]] = None,
    adjustments: Optional[List[str]] = None,
    revamps: Optional[List[str]] = None,
    server: str = "ORIGINAL SERVER",
    summary: Optional[str] = None,
    source_url: Optional[str] = None,
    publish_to_channel: bool = False,
    notify_admins: bool = True,
    bot: Optional[Bot] = None
) -> Dict[str, Any]:
    """
    Quick ready-to-use function to generate a complete MLBB Patch Notes post:
    1. Generates the high-resolution patch infographic with all hero circular avatars.
    2. Formats a 100% natural Uzbek caption.
    3. Saves post to database.
    4. Automatically dispatches either directly to channel or sends approval card to admins.
    """
    buffs = buffs or []
    nerfs = nerfs or []
    adjustments = adjustments or []
    revamps = revamps or []
    source_url = source_url or "https://mobilelegends.com/"

    if not summary or len(summary) < 10:
        summary = (
            f"Mobile Legends: Bang Bang da rasmiy {version} versiyasi e'lon qilindi! "
            f"Ushbu yangilanishda qator qahramonlar muvozanatlashtirildi va o‘yinga yaxshilanishlar kiritildi."
        )

    # 1. Render Patch Recap Graphic using official MLBB branding & hero avatar cache
    recap_data = {
        "server": server,
        "version": version,
        "buffs": buffs,
        "nerfs": nerfs,
        "adjustments": adjustments,
        "revamps": revamps
    }

    logger.info(f"Rendering patch recap graphic for version {version} ({server})...")
    image_bytes = ImageProcessor.render_patch_recap(recap_data)

    # 2. Build 100% Uzbek Telegram Caption
    formatted_post = PostFormatter.format_patch(
        version=version,
        buffs=buffs,
        nerfs=nerfs,
        adjustments=adjustments,
        source_url=source_url,
        summary=summary,
        revamps=revamps
    )

    # 3. Save to Database
    title = f"MLBB Patch Notes {version} ({server})"
    raw_content = (
        f"Version: {version}\nServer: {server}\n"
        f"Buffs: {', '.join(buffs)}\n"
        f"Nerfs: {', '.join(nerfs)}\n"
        f"Adjustments: {', '.join(adjustments)}\n"
        f"Revamps: {', '.join(revamps)}\n"
        f"Summary: {summary}"
    )

    content_hash = hashlib.sha256(f"patch_{version}_{server}_{utc_now().strftime('%Y%m%d')}".encode("utf-8")).hexdigest()

    async with get_session() as session:
        db_post = await PostRepository.create_post(
            session=session,
            source_url=source_url,
            title=title,
            category=CategoryEnum.PATCH.value,
            content_hash=content_hash,
            status=PostStatus.PUBLISHED.value if publish_to_channel else PostStatus.PENDING.value,
            raw_content=raw_content,
            formatted_post=formatted_post,
            image_url=None,
            reliability_score=100,
            confidence_score=0.99
        )
        post_id = db_post.id

    msg_id = None
    # 4. Dispatch
    if publish_to_channel:
        publisher = TelegramPublisher(bot=bot)
        msg_id = await publisher.publish_post(
            post_id=post_id,
            formatted_text=formatted_post,
            image_bytes=image_bytes
        )
        logger.info(f"Patch post #{post_id} published directly to channel. Msg ID: {msg_id}")
    elif notify_admins:
        notifier = AdminNotifier(bot=bot)
        await notifier.send_approval_request(
            post_id=post_id,
            category="PATCH",
            formatted_post=formatted_post,
            image_bytes=image_bytes
        )
        logger.info(f"Patch post #{post_id} sent to admins for approval.")

    return {
        "success": True,
        "post_id": post_id,
        "version": version,
        "server": server,
        "formatted_post": formatted_post,
        "image_bytes": image_bytes,
        "published": publish_to_channel,
        "message_id": msg_id
    }
