from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat
)
from aiogram import Bot
from app.config.settings import get_settings
from app.utils.logger import logger


def get_admin_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Doimiy admin pastki menyusi (Persistent Reply Keyboard).
    Admin uchun barcha asosiy buyruqlar ekranning pastki qismida 1 bosishda turadi.
    """
    kb = [
        [
            KeyboardButton(text="📊 Holat"),
            KeyboardButton(text="⚔️ Bugungi o‘yinlar")
        ],
        [
            KeyboardButton(text="🇲🇾 MPL MY"),
            KeyboardButton(text="🇮🇩 MPL ID"),
            KeyboardButton(text="🇵🇭 MPL PH")
        ],
        [
            KeyboardButton(text="👑 Meta Tier"),
            KeyboardButton(text="🆕 Yangi Patch")
        ],
        [
            KeyboardButton(text="⚡️ Yangilik tekshirish"),
            KeyboardButton(text="🎮 MLBB Fakt / Fun")
        ],
        [
            KeyboardButton(text="⚙️ Admin Panel"),
            KeyboardButton(text="📢 Kanallar")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Kerakli amalni tanlang..."
    )


def get_admin_inline_panel(is_paused: bool = False) -> InlineKeyboardMarkup:
    """
    Interaktiv boshqaruv paneli (Inline Dashboard).
    Har bir amalni bitta tugma orqali zudlik bilan ishga tushirish imkoniyati.
    """
    pause_text = "▶️ Yangiliklarni davom ettirish" if is_paused else "⏸ Yangiliklarni to‘xtatish"
    pause_data = "admin_action:resume" if is_paused else "admin_action:pause"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Tizim Holati", callback_data="admin_action:status"),
                InlineKeyboardButton(text="⚔️ Barcha O‘yinlar", callback_data="admin_action:today_all")
            ],
            [
                InlineKeyboardButton(text="🇲🇾 MPL MY", callback_data="admin_action:mpl_my"),
                InlineKeyboardButton(text="🇮🇩 MPL ID", callback_data="admin_action:mpl_id"),
                InlineKeyboardButton(text="🇵🇭 MPL PH", callback_data="admin_action:mpl_ph")
            ],
            [
                InlineKeyboardButton(text="👑 Meta Tier (Preview)", callback_data="admin_action:meta_preview"),
                InlineKeyboardButton(text="🚀 Tezkor Meta", callback_data="admin_action:meta_fast")
            ],
            [
                InlineKeyboardButton(text="🆕 Yangi Patch (Preview)", callback_data="admin_action:patch_preview"),
                InlineKeyboardButton(text="🚀 Tezkor Patch", callback_data="admin_action:patch_fast")
            ],
            [
                InlineKeyboardButton(text="⚡️ Yangilik Tekshiruvi", callback_data="admin_action:check_news"),
                InlineKeyboardButton(text="🎮 Fun / Fakt Post", callback_data="admin_action:fun")
            ],
            [
                InlineKeyboardButton(text=pause_text, callback_data=pause_data)
            ],
            [
                InlineKeyboardButton(text="📢 Kanallar", callback_data="admin_action:channels"),
                InlineKeyboardButton(text="👥 Adminlar", callback_data="admin_action:admins")
            ],
            [
                InlineKeyboardButton(text="🔄 Panelni Yangilash", callback_data="admin_action:refresh_panel")
            ]
        ]
    )


async def setup_bot_commands(bot: Bot):
    """
    Telegramning rasmiy [/] (Menu) tugmasiga buyruqlarni ro‘yxatdan o‘tkazadi.
    Adminga barcha buyruqlar tavsifi bilan birgalikda avtomatik chiqadi.
    """
    settings = get_settings()

    # 1. Standart foydalanuvchilar menyusi
    user_commands = [
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="status", description="📊 Tizim holati va statistika"),
        BotCommand(command="today", description="⚔️ Bugungi barcha o‘yinlar"),
        BotCommand(command="latest", description="📰 So‘nggi yangiliklar"),
        BotCommand(command="help", description="ℹ️ Yordam")
    ]
    try:
        await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    except Exception as e:
        logger.warning(f"Could not set default bot commands: {e}")

    # 2. Administratorlar menyusi
    admin_commands = [
        BotCommand(command="admin", description="⚙️ Interaktiv boshqaruv paneli"),
        BotCommand(command="status", description="📊 Tizim holati va statistika"),
        BotCommand(command="today", description="⚔️ Bugungi barcha o‘yinlar dasturi"),
        BotCommand(command="today_my", description="🇲🇾 MPL MY bugungi o‘yinlar"),
        BotCommand(command="today_id", description="🇮🇩 MPL ID bugungi o‘yinlar"),
        BotCommand(command="today_ph", description="🇵🇭 MPL PH bugungi o‘yinlar"),
        BotCommand(command="mpl_my", description="🇲🇾 MPL Malaysia jadvali"),
        BotCommand(command="mpl_id", description="🇮🇩 MPL Indonesia jadvali"),
        BotCommand(command="mpl_ph", description="🇵🇭 MPL Philippines jadvali"),
        BotCommand(command="meta", description="👑 Meta Tier list (Strong/Traps/Gems)"),
        BotCommand(command="fastmeta", description="🚀 Meta Tierni darhol kanalga chiqarish"),
        BotCommand(command="newpatch", description="🆕 Yangi patch infografikasi"),
        BotCommand(command="fastpatch", description="🚀 Patchni darhol kanalga chiqarish"),
        BotCommand(command="check_news", description="⚡️ Yangiliklarni tezkor tekshirish"),
        BotCommand(command="fun", description="🎮 MLBB fakt yoki hazil posti"),
        BotCommand(command="channels", description="📢 Ulangan kanallar"),
        BotCommand(command="pause", description="⏸ Yangilik yig‘ishni to‘xtatish"),
        BotCommand(command="resume", description="▶️ Yangilik yig‘ishni davom ettirish"),
        BotCommand(command="admins", description="👥 Administratorlar ro‘yxati"),
        BotCommand(command="help", description="ℹ️ Barcha buyruqlar va qo‘llanma")
    ]

    for admin_id in settings.admin_ids:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.debug(f"Could not set commands for admin {admin_id}: {e}")
