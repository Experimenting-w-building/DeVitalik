from zerepy.core import BaseAgent
from social_enhancement import SocialManager

async def main():
    agent = BaseAgent()
    social_manager = SocialManager(agent)
    social_manager.enhance_agent()
    
    # Now you can use it like:
    # await agent.social.handle_interaction(context)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 