import discord
from discord import app_commands
from typing import Optional
from config import DISCORD_TOKEN

class PingBot(discord.Client):
    def __init__(self):
        # Initialize with necessary intents
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        # Create a command tree for slash commands
        self.tree = app_commands.CommandTree(self)
    
    async def setup_hook(self):
        # Sync commands with Discord
        await self.tree.sync()

# Create bot instance
bot = PingBot()

# Define the ping command
@bot.tree.command(name="ping", description="Responds with Pong!")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

# Run the bot
if __name__ == "__main__":
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token from Discord Developer Portal
    bot.run(DISCORD_TOKEN)
	