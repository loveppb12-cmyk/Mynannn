import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Bot Configuration
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    API_ID = int(os.getenv('API_ID', 0))
    API_HASH = os.getenv('API_HASH')
    
    # MongoDB Configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    DB_NAME = os.getenv('DB_NAME', 'userbot_db')
    
    # Bot Settings
    MESSAGES_PER_CYCLE = int(os.getenv('MESSAGES_PER_CYCLE', 10))
    CYCLE_SECONDS = int(os.getenv('CYCLE_SECONDS', 40))
    MIN_DELAY = int(os.getenv('MIN_DELAY', 1))
    MAX_DELAY = int(os.getenv('MAX_DELAY', 3))
    
    # Messages to send randomly
    MESSAGES = [
        "hello", "hi", "kaise ho", "ap kya kr rhe ho", 
        "huuu", "hoooo", "hiiiiii", "what's up?",
        "hello everyone", "how are you all?", "gm", "hello guys"
    ]
    
    # Validate required variables
    @classmethod
    def validate(cls):
        required_vars = ['BOT_TOKEN', 'API_ID', 'API_HASH']
        missing = [var for var in required_vars if not getattr(cls, var)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        if cls.API_ID == 0:
            raise ValueError("API_ID must be a valid integer")
