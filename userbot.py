import asyncio
import random
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import Config

logger = logging.getLogger(__name__)

class UserBot:
    def __init__(self, user_id, phone, session_string):
        self.user_id = user_id
        self.phone = phone
        self.session_string = session_string
        self.client = None
        self.is_running = False
        self.task = None
        self.messages = Config.MESSAGES
        self.messages_per_cycle = Config.MESSAGES_PER_CYCLE
        self.cycle_seconds = Config.CYCLE_SECONDS
        self.min_delay = Config.MIN_DELAY
        self.max_delay = Config.MAX_DELAY
        
    async def start(self):
        """Start the userbot"""
        try:
            self.client = TelegramClient(
                StringSession(self.session_string), 
                Config.API_ID, 
                Config.API_HASH
            )
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.error(f"User {self.user_id} is not authorized")
                return False
                
            self.is_running = True
            logger.info(f"Userbot started for user {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting userbot for {self.user_id}: {e}")
            return False
    
    async def stop(self):
        """Stop the userbot"""
        self.is_running = False
        if self.task:
            self.task.cancel()
        if self.client:
            await self.client.disconnect()
        logger.info(f"Userbot stopped for user {self.user_id}")
    
    async def send_messages_to_groups(self):
        """Send messages to all groups where userbot is joined"""
        while self.is_running:
            try:
                # Get all dialogs (chats)
                dialogs = await self.client.get_dialogs()
                
                # Filter groups and channels
                groups = [d for d in dialogs if d.is_group or d.is_channel]
                
                if groups:
                    # Randomly select groups
                    selected_groups = random.sample(
                        groups, 
                        min(self.messages_per_cycle, len(groups))
                    )
                    
                    for dialog in selected_groups:
                        if not self.is_running:
                            break
                            
                        try:
                            # Send random message
                            message = random.choice(self.messages)
                            await self.client.send_message(dialog.id, message)
                            logger.info(
                                f"Sent message to {dialog.name} for user {self.user_id}"
                            )
                            
                            # Random delay between messages
                            delay = random.uniform(self.min_delay, self.max_delay)
                            await asyncio.sleep(delay)
                            
                        except Exception as e:
                            logger.error(
                                f"Error sending message to group {dialog.name}: {e}"
                            )
                            continue
                
                # Wait for cycle before next round
                await asyncio.sleep(self.cycle_seconds)
                
            except Exception as e:
                logger.error(f"Error in message loop for user {self.user_id}: {e}")
                await asyncio.sleep(self.cycle_seconds)
    
    async def run(self):
        """Run the userbot main loop"""
        self.task = asyncio.create_task(self.send_messages_to_groups())
