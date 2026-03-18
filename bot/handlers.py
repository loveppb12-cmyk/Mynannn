from telethon import events, Button
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession
import logging
from config import Config
from bot.userbot import UserBot
from bot.database import Database

logger = logging.getLogger(__name__)

# Global dictionaries to store temporary data
user_sessions = {}
userbot_tasks = {}
db = None

def register_handlers(bot, database):
    """Register all event handlers"""
    global db
    db = database
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start_command(event):
        """Handle /start command"""
        user_id = event.sender_id
        
        # Check if user already has a userbot
        user_data = db.get_user(user_id)
        
        if user_data and 'session_string' in user_data:
            # User already has a userbot
            buttons = [
                [Button.inline("▶️ Start Userbot", data="start_userbot")],
                [Button.inline("⏹️ Stop Userbot", data="stop_userbot")],
                [Button.inline("📊 Check Status", data="status")],
                [Button.inline("❌ Remove Userbot", data="remove")]
            ]
            await event.respond(
                "Welcome back! You already have a userbot configured. "
                "What would you like to do?",
                buttons=buttons
            )
        else:
            # New user - start registration process
            await event.respond(
                "🤖 **Welcome to UserBot Creator Bot!**\n\n"
                "To create your userbot, please provide your phone number "
                "with country code.\n"
                "Example: `+1234567890`"
            )
            # Set user state
            user_sessions[user_id] = {'state': 'waiting_phone'}

    @bot.on(events.CallbackQuery)
    async def callback_handler(event):
        """Handle callback queries from inline buttons"""
        user_id = event.sender_id
        data = event.data.decode()
        
        user_data = db.get_user(user_id)
        
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
                db.update_user_status(user_id, True)
                asyncio.create_task(userbot.run())
                await event.answer("Userbot started successfully!")
                await event.edit(
                    "✅ **Userbot has been started!**\n\n"
                    f"It will send {Config.MESSAGES_PER_CYCLE} messages "
                    f"every {Config.CYCLE_SECONDS} seconds to your groups."
                )
            else:
                await event.answer("Failed to start userbot!")
                
        elif data == "stop_userbot":
            # Stop the userbot
            if user_id in userbot_tasks:
                await userbot_tasks[user_id].stop()
                del userbot_tasks[user_id]
                db.update_user_status(user_id, False)
                await event.answer("Userbot stopped!")
                await event.edit("⏹️ **Userbot has been stopped.**")
            else:
                await event.answer("Userbot is not running!")
                
        elif data == "status":
            # Check status
            if user_id in userbot_tasks and userbot_tasks[user_id].is_running:
                status = "🟢 **Running**"
            else:
                status = "🔴 **Stopped**"
            
            user_info = db.get_user(user_id)
            created_at = user_info.get('created_at', 'Unknown')
            
            await event.answer("Status checked")
            await event.edit(
                f"📊 **Userbot Status**\n\n"
                f"Status: {status}\n"
                f"Phone: `{user_info['phone']}`\n"
                f"Created: {created_at}\n"
                f"Messages per cycle: {Config.MESSAGES_PER_CYCLE}\n"
                f"Cycle time: {Config.CYCLE_SECONDS} seconds"
            )
            
        elif data == "remove":
            # Remove userbot
            buttons = [
                [Button.inline("✅ Yes, remove", data="confirm_remove")],
                [Button.inline("❌ No, keep", data="cancel")]
            ]
            await event.edit(
                "⚠️ **Are you sure?**\n\n"
                "This will remove your userbot and all associated data. "
                "This action cannot be undone.",
                buttons=buttons
            )
            
        elif data == "confirm_remove":
            # Confirm removal
            if user_id in userbot_tasks:
                await userbot_tasks[user_id].stop()
                del userbot_tasks[user_id]
            
            db.delete_user(user_id)
            await event.edit(
                "✅ **Userbot removed successfully!**\n\n"
                "Send /start to create a new one."
            )
            
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
                    user_sessions[user_id]['phone'] = event.text.strip()
                    user_sessions[user_id]['state'] = 'waiting_otp'
                    
                    # Send OTP request
                    try:
                        # Create temporary client for OTP
                        temp_client = TelegramClient(
                            StringSession(), 
                            Config.API_ID, 
                            Config.API_HASH
                        )
                        await temp_client.connect()
                        
                        # Send code request
                        await temp_client.send_code_request(event.text.strip())
                        
                        # Store temp client
                        user_sessions[user_id]['temp_client'] = temp_client
                        
                        await event.respond(
                            "📱 **Code sent!**\n\n"
                            "Please enter the OTP code you received:\n"
                            "`(if you don't receive it within 2 minutes, start over)`"
                        )
                    except Exception as e:
                        await event.respond(f"❌ Error sending OTP: {str(e)}")
                        if user_id in user_sessions:
                            del user_sessions[user_id]
                        
                elif state == 'waiting_otp':
                    # Verify OTP
                    phone = user_sessions[user_id]['phone']
                    temp_client = user_sessions[user_id]['temp_client']
                    otp = event.text.strip()
                    
                    try:
                        await temp_client.sign_in(phone, otp)
                        
                        # Get session string
                        session_string = temp_client.session.save()
                        
                        # Save to MongoDB
                        db.save_user(user_id, phone, session_string)
                        
                        # Clean up
                        await temp_client.disconnect()
                        if user_id in user_sessions:
                            del user_sessions[user_id]
                        
                        # Show success message with options
                        buttons = [
                            [Button.inline("▶️ Start Userbot Now", data="start_userbot")],
                            [Button.inline("📊 Check Status", data="status")]
                        ]
                        
                        await event.respond(
                            "✅ **Success!**\n\n"
                            "Your userbot has been created successfully.\n"
                            "What would you like to do now?",
                            buttons=buttons
                        )
                        
                    except SessionPasswordNeededError:
                        # Two-factor authentication enabled
                        user_sessions[user_id]['state'] = 'waiting_2fa'
                        await event.respond(
                            "🔐 **Two-Factor Authentication Enabled**\n\n"
                            "Please enter your password:"
                        )
                    except Exception as e:
                        await event.respond(f"❌ Error verifying OTP: {str(e)}")
                        await temp_client.disconnect()
                        if user_id in user_sessions:
                            del user_sessions[user_id]
                            
                elif state == 'waiting_2fa':
                    # Handle 2FA password
                    temp_client = user_sessions[user_id]['temp_client']
                    password = event.text.strip()
                    
                    try:
                        await temp_client.sign_in(password=password)
                        
                        # Get session string
                        session_string = temp_client.session.save()
                        
                        # Save to MongoDB
                        db.save_user(
                            user_id, 
                            user_sessions[user_id]['phone'], 
                            session_string
                        )
                        
                        # Clean up
                        await temp_client.disconnect()
                        if user_id in user_sessions:
                            del user_sessions[user_id]
                        
                        buttons = [
                            [Button.inline("▶️ Start Userbot Now", data="start_userbot")],
                            [Button.inline("📊 Check Status", data="status")]
                        ]
                        
                        await event.respond(
                            "✅ **Success!**\n\n"
                            "Your userbot has been created with 2FA.",
                            buttons=buttons
                        )
                        
                    except Exception as e:
                        await event.respond(f"❌ Error with password: {str(e)}")
                        await temp_client.disconnect()
                        if user_id in user_sessions:
                            del user_sessions[user_id]
