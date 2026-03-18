import asyncio
import logging
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

from config import Config
from bot.database import Database
from bot.handlers import register_handlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to run the bot"""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Initialize database
        logger.info("Connecting to MongoDB...")
        db = Database(Config.MONGO_URI, Config.DB_NAME)
        logger.info("MongoDB connected successfully")
        
        # Initialize bot
        logger.info("Starting Telegram bot...")
        bot = TelegramClient('bot', Config.API_ID, Config.API_HASH)
        await bot.start(bot_token=Config.BOT_TOKEN)
        
        # Register handlers
        register_handlers(bot, db)
        
        logger.info("Bot is running! Press Ctrl+C to stop.")
        await bot.run_until_disconnected()
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        if 'db' in locals():
            db.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
