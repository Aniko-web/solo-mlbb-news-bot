import asyncio
import signal
import sys
from app.config.settings import get_settings
from app.utils.logger import logger
from app.database.database import init_db
from app.telegram.bot import create_bot_and_dispatcher
from app.scheduler.jobs import NewsJobManager

settings = get_settings()


async def main():
    logger.info("==========================================")
    logger.info("   MLBB TELEGRAM NEWS AI AGENT STARTING   ")
    logger.info("==========================================")
    logger.info(f"Mode: {'AUTO PUBLISH' if settings.AUTO_PUBLISH else 'ADMIN APPROVAL (Recommended)'}")
    logger.info(f"Database: {settings.DATABASE_URL}")

    # 1. Initialize Database
    await init_db()

    # 2. Setup Bot & Dispatcher
    bot, dp = create_bot_and_dispatcher()

    # 3. Setup Scheduler & Job Pipeline
    job_manager = NewsJobManager(bot=bot)
    job_manager.start()

    # 4. Graceful shutdown handler
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received. Stopping services...")
        job_manager.stop()
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Signal handling on some platforms
            pass

    try:
        if bot:
            logger.info("Starting Telegram Bot Polling...")
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        else:
            logger.info("Running in headless scheduler mode (Waiting for shutdown)...")
            await stop_event.wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Interrupted. Exiting cleanly...")
    finally:
        job_manager.stop()
        if bot:
            await bot.session.close()
        logger.info("MLBB Telegram News AI Agent stopped safely.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
