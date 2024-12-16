import discord
from discord import app_commands
# from services.dexscreener import DexScreenerService

class PonderBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        # self.dex_service = DexScreenerService()
    
    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print('------')