import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, User, Chat, CallbackQuery
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.telegram.bot import cmd_start, cmd_status, cmd_pause, cmd_resume, STATE
from app.telegram.admin import (
    get_approval_keyboard,
    handle_publish_callback,
    is_authorized_admin,
    get_effective_admin_ids,
    AdminNotifier
)
from app.config.settings import get_settings
from app.database.models import Base
from app.database.repositories import AdminRepository

settings = get_settings()


@pytest.mark.asyncio
async def test_cmd_start():
    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = 12345
    msg.reply = AsyncMock()

    await cmd_start(msg)
    msg.reply.assert_called_once()
    called_text = msg.reply.call_args[0][0]
    assert "MLBB News AI Agent" in called_text


@pytest.mark.asyncio
async def test_cmd_pause_and_resume():
    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = 999999
    msg.reply = AsyncMock()

    # If not admin, shouldn't pause
    settings.ADMIN_TELEGRAM_ID = "888888"
    settings.ADMIN_TELEGRAM_IDS = ""
    await cmd_pause(msg)
    assert STATE["is_paused"] is False

    # Mock admin ID
    settings.ADMIN_TELEGRAM_ID = "999999"
    await cmd_pause(msg)
    assert STATE["is_paused"] is True

    await cmd_resume(msg)
    assert STATE["is_paused"] is False


def test_approval_keyboard():
    kb = get_approval_keyboard(post_id=42)
    assert kb.inline_keyboard[0][0].callback_data == "publish:42"
    assert kb.inline_keyboard[0][1].callback_data == "reject:42"
    assert kb.inline_keyboard[1][0].callback_data == "edit:42"


def test_multi_admin_settings_parsing():
    """Verify comma, semicolon, space separation and ADMIN_TELEGRAM_IDS support."""
    settings.ADMIN_TELEGRAM_ID = "1001, 1002; 1003"
    settings.ADMIN_TELEGRAM_IDS = "1004 1005, 1001"

    ids = settings.admin_ids
    assert 1001 in ids
    assert 1002 in ids
    assert 1003 in ids
    assert 1004 in ids
    assert 1005 in ids
    assert len(ids) == 5  # Deduplicated

    assert settings.is_admin(1001) is True
    assert settings.is_admin(1005) is True
    assert settings.is_admin(9999) is False


@pytest.mark.asyncio
async def test_database_admin_management(monkeypatch):
    """Verify adding/removing admins dynamically in database."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    from app.database import database
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", session_maker)

    settings.ADMIN_TELEGRAM_ID = "777777"
    settings.ADMIN_TELEGRAM_IDS = ""

    async with session_maker() as session:
        # Add new dynamic admin
        added = await AdminRepository.add_admin(session, telegram_id=555555, username="testadmin")
        assert added is True
        await session.commit()

        # Check is_admin
        is_adm = await AdminRepository.is_admin(session, 555555)
        assert is_adm is True

        # Check effective admin list
        effective = await get_effective_admin_ids()
        assert 777777 in effective
        assert 555555 in effective

        # Remove dynamic admin
        removed = await AdminRepository.remove_admin(session, 555555)
        assert removed is True
        await session.commit()

        is_adm_now = await AdminRepository.is_admin(session, 555555)
        assert is_adm_now is False

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_admin_notifier_broadcasts_to_all_admins(monkeypatch):
    """Verify approval notifications are dispatched to all registered admins."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    from app.database import database
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", session_maker)

    settings.ADMIN_TELEGRAM_ID = "1111, 2222"
    settings.ADMIN_TELEGRAM_IDS = ""

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()

    notifier = AdminNotifier(bot=mock_bot)
    await notifier.send_approval_request(
        post_id=99,
        category="PATCH",
        formatted_post="Test Post Content"
    )

    # Must be sent to both 1111 and 2222!
    assert mock_bot.send_message.call_count == 2
    called_chats = [call.kwargs.get("chat_id") for call in mock_bot.send_message.call_args_list]
    assert 1111 in called_chats
    assert 2222 in called_chats

    await test_engine.dispose()
