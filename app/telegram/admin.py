import os
from typing import Optional, List
from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
    BufferedInputFile
)
from app.config.settings import get_settings
from app.utils.logger import logger
from app.database.database import get_session
from app.database.repositories import PostRepository, AdminRepository
from app.utils.validators import PostStatus

settings = get_settings()
admin_router = Router(name="admin_router")


async def is_authorized_admin(user_id: int) -> bool:
    """Check if user_id is admin via settings (.env) or database."""
    if settings.is_admin(user_id):
        return True
    try:
        async with get_session() as session:
            return await AdminRepository.is_admin(session, user_id)
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False


async def get_effective_admin_ids() -> List[int]:
    """Return all unique admin IDs combining .env and database."""
    ids = set(settings.admin_ids)
    try:
        async with get_session() as session:
            db_ids = await AdminRepository.get_all_admin_ids(session)
            ids.update(db_ids)
    except Exception as e:
        logger.error(f"Error fetching admin IDs: {e}")
    return sorted(list(ids))


def get_approval_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Create inline keyboard with Publish, Reject, and Edit buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Publish", callback_data=f"publish:{post_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"reject:{post_id}"),
            ],
            [
                InlineKeyboardButton(text="✏️ Edit", callback_data=f"edit:{post_id}")
            ]
        ]
    )


class AdminNotifier:
    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot

    async def send_approval_request(
        self,
        post_id: int,
        category: str,
        formatted_post: str,
        image_bytes: Optional[bytes] = None,
        image_url: Optional[str] = None
    ) -> None:
        """
        Send generated post preview to all registered admins with inline approval buttons.
        """
        target_ids = await get_effective_admin_ids()
        if not self.bot or not target_ids:
            logger.info(f"[Approval Mode] Simulated approval request for post #{post_id} ({category})")
            return

        timeout_min = getattr(settings, "APPROVAL_TIMEOUT_MINUTES", 30)
        preview_text = (
            f"📰 <b>NEW POST APPROVAL REQUIRED</b>\n"
            f"🏷 Category: <b>{category}</b> | Post ID: #{post_id}\n\n"
            f"{formatted_post}\n\n"
            f"⏰ <i>Eslatma: Agar {timeout_min} daqiqa ichida tasdiqlanmasa, post avtomatik ravishda kanalga uzatiladi.</i>"
        )

        keyboard = get_approval_keyboard(post_id)

        # If image_bytes not passed, try loading from local file or downloading from image_url
        if not image_bytes and image_url:
            try:
                if os.path.exists(image_url):
                    with open(image_url, "rb") as f:
                        image_bytes = f.read()
                else:
                    from app.media.image_processor import ImageProcessor
                    image_bytes = await ImageProcessor.download_and_optimize(image_url)
            except Exception as dl_err:
                logger.debug(f"Failed preview image load: {dl_err}")

        for admin_id in target_ids:
            try:
                if image_bytes:
                    from app.utils.html_utils import safe_trim_html
                    caption = safe_trim_html(preview_text, max_len=1020)
                    photo_file = BufferedInputFile(image_bytes, filename=f"preview_{post_id}.png")
                    try:
                        await self.bot.send_photo(
                            chat_id=admin_id,
                            photo=photo_file,
                            caption=caption,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                    except Exception as photo_ex:
                        logger.warning(f"Admin send_photo failed ({photo_ex}), falling back to send_message")
                        await self.bot.send_message(
                            chat_id=admin_id,
                            text=preview_text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                else:
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=preview_text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
            except Exception as e:
                logger.error(f"Failed to send approval request to admin {admin_id}: {e}")

    async def send_auto_published_alert(
        self,
        post_id: int,
        category: str,
        title: str,
        msg_id: int
    ) -> None:
        """
        Notify all registered admins when a pending post is auto-forwarded to channel after timeout.
        """
        target_ids = await get_effective_admin_ids()
        if not self.bot or not target_ids:
            return

        timeout_min = getattr(settings, "APPROVAL_TIMEOUT_MINUTES", 30)
        alert_text = (
            f"⏰ <b>POST AVTOMATIK KANALGA UZATILDI</b>\n\n"
            f"Post #<b>{post_id}</b> [{category}] admin tomonidan {timeout_min} daqiqa davomida "
            f"tasdiqlanmaganligi sababli kanalga avtomatik chiqarildi!\n\n"
            f"📌 <b>Sarlavha:</b> {title}\n"
            f"📢 <b>Kanal xabar ID:</b> <code>{msg_id}</code>"
        )

        for admin_id in target_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=alert_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.debug(f"Failed to send auto-publish alert to admin {admin_id}: {e}")

    async def send_source_error_alert(self, source_name: str, error_time: str) -> None:
        """
        Notify all registered admins when a source fails without stopping the system.
        """
        target_ids = await get_effective_admin_ids()
        if not self.bot or not target_ids:
            logger.warning(f"Simulated Admin Alert: Source '{source_name}' error at {error_time}")
            return

        alert_text = (
            f"⚠️ <b>SOURCE ERROR</b>\n"
            f"<b>{source_name}</b> source is unavailable.\n"
            f"Time: {error_time}\n\n"
            f"<i>System continues running normally.</i>"
        )

        for admin_id in target_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=alert_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to send source error alert to admin {admin_id}: {e}")


@admin_router.message(Command("admins"))
async def cmd_list_admins(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Ruxsat berilmagan.")
        return

    env_ids = settings.admin_ids
    async with get_session() as session:
        db_admins = await AdminRepository.list_admins(session)

    all_ids = set(env_ids)
    for a in db_admins:
        all_ids.add(a.telegram_id)

    lines = [f"👑 <b>Administratorlar ro‘yxati ({len(all_ids)} ta):</b>\n"]
    if env_ids:
        lines.append("<b>.env orqali sozlangan:</b>")
        for eid in env_ids:
            lines.append(f"• <code>{eid}</code>")

    if db_admins:
        lines.append("\n<b>Bot orqali qo‘shilgan:</b>")
        for da in db_admins:
            name_str = f" (@{da.username})" if da.username else (f" ({da.full_name})" if da.full_name else "")
            lines.append(f"• <code>{da.telegram_id}</code>{name_str}")

    lines.append("\n<i>Yangi admin qo‘shish: /addadmin &lt;telegram_id&gt;</i>")
    lines.append("<i>Adminni o‘chirish: /deladmin &lt;telegram_id&gt;</i>")
    await message.reply("\n".join(lines), parse_mode="HTML")


@admin_router.message(Command("addadmin"))
async def cmd_add_admin(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Ruxsat berilmagan.")
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        await message.reply("Foydalanish: <code>/addadmin &lt;telegram_user_id&gt;</code>")
        return

    new_admin_id = int(parts[1])
    async with get_session() as session:
        success = await AdminRepository.add_admin(
            session=session,
            telegram_id=new_admin_id,
            added_by=user_id
        )

    if success:
        await message.reply(
            f"✅ <b>Yangi administrator qo‘shildi:</b> <code>{new_admin_id}</code>\n"
            f"Endi ushbu foydalanuvchi ham barcha xabarnomalarni oladi va boshqaruv huquqiga ega.",
            parse_mode="HTML"
        )
    else:
        await message.reply(f"ℹ️ <code>{new_admin_id}</code> allaqachon administrator sifatida mavjud.")


@admin_router.message(Command("deladmin"))
async def cmd_del_admin(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Ruxsat berilmagan.")
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        await message.reply("Foydalanish: <code>/deladmin &lt;telegram_user_id&gt;</code>")
        return

    del_id = int(parts[1])
    if del_id in settings.admin_ids:
        await message.reply(
            f"⚠️ <code>{del_id}</code> asosiy <code>.env</code> faylida sozlangan. Uni o‘chirish uchun .env faylidan olib tashlang."
        )
        return

    async with get_session() as session:
        success = await AdminRepository.remove_admin(session, del_id)

    if success:
        await message.reply(f"✅ Administrator <code>{del_id}</code> muvaffaqiyatli o‘chirildi.", parse_mode="HTML")
    else:
        await message.reply(f"ℹ️ Administrator <code>{del_id}</code> topilmadi.")


@admin_router.message(Command("newpatch", "patch"))
async def cmd_new_patch(message: Message, bot: Bot):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Ruxsat berilmagan.")
        return

    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        help_text = (
            "🛠 <b>YANGI PATCH POSTI YARATISH</b>\n\n"
            "Patch ma'lumotlarini tezda kiritib, infografika rasmi va o‘zbekcha matn bilan post yaratishingiz mumkin.\n\n"
            "📋 <b>1-usul: Qulay ko‘p qatorli format:</b>\n"
            "<code>/newpatch\n"
            "Versiya: 1.9.45\n"
            "Buff: Fanny, Franco, Baxia\n"
            "Nerf: Lancelot, Granger, Valentina\n"
            "Adjustment: Harith, Chou, Martis\n"
            "Revamp: Kalea\n"
            "Tavsif: Yangi original server qahramonlar balansi</code>\n\n"
            "⚡️ <b>2-usul: Tezkor bir qatorli format:</b>\n"
            "<code>/newpatch 1.9.45 | Fanny, Franco | Lancelot, Granger | Harith, Chou | Kalea</code>\n\n"
            "💡 <i>Post yaratilgach, sizga tasdiqlash tugmalari ([✅ Publish], [❌ Reject]) bilan preview yuboriladi. To‘g‘ridan-to‘g‘ri kanalga chiqarish uchun /fastpatch buyrug‘idan foydalaning.</i>"
        )
        await message.reply(help_text, parse_mode="HTML")
        return

    await message.reply("⏳ <i>Patch infografikasi chizilmoqda va post tayyorlanmoqda...</i>", parse_mode="HTML")

    from app.services.patch_service import parse_patch_text, create_patch_post
    parsed = parse_patch_text(text)

    try:
        res = await create_patch_post(
            version=parsed.get("version", "1.9.xx"),
            buffs=parsed.get("buffs", []),
            nerfs=parsed.get("nerfs", []),
            adjustments=parsed.get("adjustments", []),
            revamps=parsed.get("revamps", []),
            server=parsed.get("server", "ORIGINAL SERVER"),
            summary=parsed.get("summary", ""),
            publish_to_channel=False,
            notify_admins=True,
            bot=bot
        )
        await message.reply(
            f"✅ <b>Patch #{res['post_id']} muvaffaqiyatli yaratildi!</b>\n"
            f"Versiya: <b>{res['version']}</b> ({res['server']})\n"
            f"Yuqoridagi preview xabarida <b>[✅ Publish]</b> tugmasini bosib, postni kanalga chiqarishingiz mumkin.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error creating patch post via command: {e}")
        await message.reply(f"❌ Xatolik yuz berdi: {e}")


@admin_router.message(Command("fastpatch"))
async def cmd_fast_patch(message: Message, bot: Bot):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_authorized_admin(user_id):
        await message.reply("Ruxsat berilmagan.")
        return

    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.reply(
            "Foydalanish: <code>/fastpatch &lt;versiya&gt; | &lt;buffs&gt; | &lt;nerfs&gt; | &lt;adjustments&gt; | &lt;revamps&gt;</code>\n"
            "Ushbu buyruq postni darhol kanalga chop etadi.",
            parse_mode="HTML"
        )
        return

    await message.reply("🚀 <i>Patch infografikasi chizilmoqda va to‘g‘ridan-to‘g‘ri kanalga chiqarilmoqda...</i>", parse_mode="HTML")

    from app.services.patch_service import parse_patch_text, create_patch_post
    parsed = parse_patch_text(text)

    try:
        res = await create_patch_post(
            version=parsed.get("version", "1.9.xx"),
            buffs=parsed.get("buffs", []),
            nerfs=parsed.get("nerfs", []),
            adjustments=parsed.get("adjustments", []),
            revamps=parsed.get("revamps", []),
            server=parsed.get("server", "ORIGINAL SERVER"),
            summary=parsed.get("summary", ""),
            publish_to_channel=True,
            notify_admins=False,
            bot=bot
        )
        await message.reply(
            f"🎉 <b>Patch #{res['post_id']} darhol kanalga chop etildi!</b>\n"
            f"Versiya: <b>{res['version']}</b>\n"
            f"Xabar ID: <code>{res.get('message_id')}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error fast-publishing patch post: {e}")
        await message.reply(f"❌ Xatolik yuz berdi: {e}")



@admin_router.callback_query(F.data.startswith("publish:"))
async def handle_publish_callback(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if not await is_authorized_admin(user_id):
        await callback.answer("Ruxsat berilmagan (Admin emassiz).", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        post = await PostRepository.get_by_id(session, post_id)
        if not post:
            await callback.answer("Post topilmadi!", show_alert=True)
            return

        if post.status == PostStatus.PUBLISHED.value:
            await callback.answer("Ushbu post boshqa admin tomonidan allaqachon kanalga yuborilgan.", show_alert=True)
            return

        # Publish to channel
        from app.telegram.publisher import TelegramPublisher
        publisher = TelegramPublisher(bot=bot)
        msg_id = await publisher.publish_post(
            post_id=post.id,
            formatted_text=post.formatted_post or post.title,
            image_url=post.image_url
        )

        await callback.answer("✅ Post kanalga muvaffaqiyatli joylandi!")
        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            await callback.message.reply(f"✅ <b>Post #{post_id} kanalga joylandi</b> (Xabar ID: {msg_id})")


@admin_router.callback_query(F.data.startswith("reject:"))
async def handle_reject_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_authorized_admin(user_id):
        await callback.answer("Ruxsat berilmagan.", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        post = await PostRepository.get_by_id(session, post_id)
        if post and post.status == PostStatus.PUBLISHED.value:
            await callback.answer("Ushbu post allaqachon kanalga chiqib bo‘lgan, rad etib bo‘lmaydi.", show_alert=True)
            return

        if post and post.status == PostStatus.REJECTED.value:
            await callback.answer("Ushbu post allaqachon rad etilgan.", show_alert=True)
            return

        await PostRepository.update_status(session, post_id, PostStatus.REJECTED.value)

    await callback.answer("❌ Post rad etildi!")
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.reply(f"❌ <b>Post #{post_id} rad etildi.</b>")


@admin_router.callback_query(F.data.startswith("edit:"))
async def handle_edit_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_authorized_admin(user_id):
        await callback.answer("Ruxsat berilmagan.", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])
    await callback.answer(f"Tahrirlash: /send {post_id} <yangi_matn>", show_alert=True)
