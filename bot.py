import os
import asyncio
import random
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import SendMessageRequest
from telethon.errors import SessionPasswordNeededError
from pymongo import MongoClient
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = "8791767856:AAFDcfcO3Jx3WrOO1rchQTryK0R4HabbJZo"  # Replace with your bot token from @BotFather
API_ID = 20284828  # Replace with your API ID from my.telegram.org
API_HASH = "a980ba25306901d5c9b899414d6a9ab7"  # Replace with your API hash from my.telegram.org
MONGO_URI = "mongodb+srv://yacan69355:Cw92BrnfAfWQcLvU@cluster0.jh6h6wg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # Replace with your MongoDB URI

# Connect to MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["userbot_db"]
users_collection = db["users"]

# Messages to send randomly
MESSAGES = [
    "hello", 
    "hi", 
    "kaise ho", 
    "ap kya kr rhe ho", 
    "huuu", 
    "hoooo", 
    "hiiiiii",
    "what's up?",
    "hello everyone",
    "how are you all?",
    "gm",
    "hello guys"
]

# Main bot client
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Store user sessions
user_sessions = {}

# Store active userbot tasks
userbot_tasks = {}

class UserBot:
    def __init__(self, user_id, phone, session_string):
        self.user_id = user_id
        self.phone = phone
        self.session_string = session_string
        self.client = None
        self.is_running = False
        self.task = None
        
    async def start(self):
        """Start the userbot"""
        try:
            self.client = TelegramClient(
                StringSession(self.session_string), 
                API_ID, 
                API_HASH
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
                    # Randomly select 10 groups or less if fewer available
                    selected_groups = random.sample(groups, min(10, len(groups)))
                    
                    for dialog in selected_groups:
                        if not self.is_running:
                            break
                            
                        try:
                            # Send random message
                            message = random.choice(MESSAGES)
                            await self.client.send_message(dialog.id, message)
                            logger.info(f"Sent message to {dialog.name} for user {self.user_id}")
                            
                            # Random delay between messages (1-3 seconds)
                            await asyncio.sleep(random.uniform(1, 3))
                            
                        except Exception as e:
                            logger.error(f"Error sending message to group {dialog.name}: {e}")
                            continue
                
                # Wait for 40 seconds before next cycle
                await asyncio.sleep(40)
                
            except Exception as e:
                logger.error(f"Error in message loop for user {self.user_id}: {e}")
                await asyncio.sleep(40)
    
    async def run(self):
        """Run the userbot main loop"""
        self.task = asyncio.create_task(self.send_messages_to_groups())

# Command handlers
@bot.on(events.NewMessage(pattern='/start'))
async def start_command(event):
    """Handle /start command"""
    user_id = event.sender_id
    
    # Check if user already has a userbot
    user_data = users_collection.find_one({"user_id": user_id})
    
    if user_data and 'session_string' in user_data:
        # User already has a userbot
        buttons = [
            [Button.inline("▶️ Start Userbot", data="start_userbot")],
            [Button.inline("⏹️ Stop Userbot", data="stop_userbot")],
            [Button.inline("📊 Check Status", data="status")],
            [Button.inline("❌ Remove Userbot", data="remove")]
        ]
        await event.respond(
            "Welcome back! You already have a userbot configured. What would you like to do?",
            buttons=buttons
        )
    else:
        # New user - start registration process
        await event.respond(
            "Welcome to UserBot Creator Bot!\n\n"
            "To create your userbot, please provide your phone number (with country code).\n"
            "Example: +1234567890"
        )
        # Set user state
        user_sessions[user_id] = {'state': 'waiting_phone'}

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    """Handle callback queries from inline buttons"""
    user_id = event.sender_id
    data = event.data.decode()
    
    user_data = users_collection.find_one({"user_id": user_id})
    
    if not user_data:
        await event.answer("No userbot found! Please start over with /start")
        return
    
    if data == "start_userbot":
        # Start the userbot
        if user_id in userbot_tasks and userbot_tasks[user_id].is_running:
            await event.answer("Userbot is already running!")
            return
            
        userbot = UserBot(
            user_id,
            user_data['phone'],
            user_data['session_string']
        )
        
        if await userbot.start():
            userbot_tasks[user_id] = userbot
            asyncio.create_task(userbot.run())
            await event.answer("Userbot started successfully!")
            await event.edit("✅ Userbot has been started. It will now send messages every 40 seconds.")
        else:
            await event.answer("Failed to start userbot!")
            
    elif data == "stop_userbot":
        # Stop the userbot
        if user_id in userbot_tasks:
            await userbot_tasks[user_id].stop()
            del userbot_tasks[user_id]
            await event.answer("Userbot stopped!")
            await event.edit("⏹️ Userbot has been stopped.")
        else:
            await event.answer("Userbot is not running!")
            
    elif data == "status":
        # Check status
        if user_id in userbot_tasks and userbot_tasks[user_id].is_running:
            status = "🟢 Running"
        else:
            status = "🔴 Stopped"
        
        user_info = users_collection.find_one({"user_id": user_id})
        created_at = user_info.get('created_at', 'Unknown')
        
        await event.answer("Status checked")
        await event.edit(
            f"📊 **Userbot Status**\n\n"
            f"Status: {status}\n"
            f"Phone: {user_info['phone']}\n"
            f"Created: {created_at}\n"
            f"Messages will be sent to all groups you're in."
        )
        
    elif data == "remove":
        # Remove userbot
        buttons = [
            [Button.inline("✅ Yes, remove", data="confirm_remove")],
            [Button.inline("❌ No, keep", data="cancel")]
        ]
        await event.edit(
            "Are you sure you want to remove your userbot? This action cannot be undone.",
            buttons=buttons
        )
        
    elif data == "confirm_remove":
        # Confirm removal
        if user_id in userbot_tasks:
            await userbot_tasks[user_id].stop()
            del userbot_tasks[user_id]
        
        users_collection.delete_one({"user_id": user_id})
        await event.edit("✅ Your userbot has been removed successfully. Send /start to create a new one.")
        
    elif data == "cancel":
        await event.delete()
        await start_command(event)

@bot.on(events.NewMessage)
async def message_handler(event):
    """Handle text messages (for registration process)"""
    if event.is_private and not event.text.startswith('/'):
        user_id = event.sender_id
        
        # Check if user is in registration process
        if user_id in user_sessions:
            state = user_sessions[user_id].get('state')
            
            if state == 'waiting_phone':
                # Store phone number and ask for OTP
                user_sessions[user_id]['phone'] = event.text
                user_sessions[user_id]['state'] = 'waiting_otp'
                
                # Send OTP request
                try:
                    # Create temporary client for OTP
                    temp_client = TelegramClient(StringSession(), API_ID, API_HASH)
                    await temp_client.connect()
                    
                    # Send code request
                    await temp_client.send_code_request(event.text)
                    
                    # Store temp client
                    user_sessions[user_id]['temp_client'] = temp_client
                    
                    await event.respond(
                        "📱 Code sent to your phone!\n\n"
                        "Please enter the OTP code you received:"
                    )
                except Exception as e:
                    await event.respond(f"Error sending OTP: {str(e)}")
                    del user_sessions[user_id]
                    
            elif state == 'waiting_otp':
                # Verify OTP
                phone = user_sessions[user_id]['phone']
                temp_client = user_sessions[user_id]['temp_client']
                otp = event.text
                
                try:
                    await temp_client.sign_in(phone, otp)
                    
                    # Get session string
                    session_string = temp_client.session.save()
                    
                    # Save to MongoDB
                    users_collection.insert_one({
                        "user_id": user_id,
                        "phone": phone,
                        "session_string": session_string,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # Clean up
                    await temp_client.disconnect()
                    del user_sessions[user_id]
                    
                    # Show success message with options
                    buttons = [
                        [Button.inline("▶️ Start Userbot Now", data="start_userbot")],
                        [Button.inline("📊 Check Status", data="status")]
                    ]
                    
                    await event.respond(
                        "✅ **Success!** Your userbot has been created.\n\n"
                        "What would you like to do now?",
                        buttons=buttons
                    )
                    
                except SessionPasswordNeededError:
                    # Two-factor authentication enabled
                    user_sessions[user_id]['state'] = 'waiting_2fa'
                    await event.respond(
                        "🔐 Two-factor authentication is enabled.\n"
                        "Please enter your password:"
                    )
                except Exception as e:
                    await event.respond(f"Error verifying OTP: {str(e)}")
                    await temp_client.disconnect()
                    del user_sessions[user_id]
                    
            elif state == 'waiting_2fa':
                # Handle 2FA password
                temp_client = user_sessions[user_id]['temp_client']
                password = event.text
                
                try:
                    await temp_client.sign_in(password=password)
                    
                    # Get session string
                    session_string = temp_client.session.save()
                    
                    # Save to MongoDB
                    users_collection.insert_one({
                        "user_id": user_id,
                        "phone": user_sessions[user_id]['phone'],
                        "session_string": session_string,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # Clean up
                    await temp_client.disconnect()
                    del user_sessions[user_id]
                    
                    buttons = [
                        [Button.inline("▶️ Start Userbot Now", data="start_userbot")],
                        [Button.inline("📊 Check Status", data="status")]
                    ]
                    
                    await event.respond(
                        "✅ **Success!** Your userbot has been created with 2FA.",
                        buttons=buttons
                    )
                    
                except Exception as e:
                    await event.respond(f"Error with password: {str(e)}")
                    await temp_client.disconnect()
                    del user_sessions[user_id]

async def main():
    """Main function to run the bot"""
    logger.info("Bot is starting...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    # Required import for StringSession
    from telethon.sessions import StringSession
    
    # Run the bot
    asyncio.run(main())
