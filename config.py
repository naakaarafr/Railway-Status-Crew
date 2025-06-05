import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for Railway Status Crew"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY")
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.model_name = "gemini-2.0-flash"
        self.temperature = 0.1
        self.max_tokens = 1000
        
    def get_llm(self):
        """Get configured Gemini LLM instance"""
        if not self.gemini_api_key:
            print("⚠️  Warning: GEMINI_API_KEY not found in environment variables")
            print("   Using default configuration - some features may be limited")
            # Create a basic LLM instance that will work with mock data
            return ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key="dummy_key_for_testing",
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
        
        try:
            llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.gemini_api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return llm
        except Exception as e:
            print(f"❌ Error initializing Gemini LLM: {str(e)}")
            print("   Falling back to basic configuration")
            return ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key="dummy_key_for_testing",
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
    
    def display_status(self):
        """Display configuration status"""
        print("⚙️  Configuration Status:")
        print(f"   Model: {self.model_name}")
        print(f"   Gemini API Key: {'✅ Configured' if self.gemini_api_key else '❌ Missing'}")
        print(f"   Serper API Key: {'✅ Configured' if self.serper_api_key else '❌ Missing (will use mock data)'}")
        print(f"   Temperature: {self.temperature}")
        print()

# Create global config instance
config = Config()

# Convenience function for getting LLM
def get_llm():
    """Get configured LLM instance"""
    return config.get_llm()
