import discord
from bot.client import PonderBot
from services.dexscreener import DexScreenerService

def setup_commands(client: PonderBot):
    @client.tree.command(name="ping", description="Responds with Pong!")
    async def ping(interaction: discord.Interaction):
        print("pinged")
        await interaction.response.send_message("Pong!")
    
    @client.tree.command(name="hello", description="Says hello to the user")
    async def hello(interaction: discord.Interaction):
        user_name = interaction.user.name
        await interaction.response.send_message(f"Hi {user_name}!")
    
    @client.tree.command(name="getfirst", description="Get the URL of the first token profile from DexScreener")
    async def getfirst(interaction: discord.Interaction):
        await interaction.response.defer()
        print("dex")
        try:
            url = await DexScreenerService.fetch_first_token_url()
            if url:
                await interaction.followup.send(f"First token profile URL: {url}")
            else:
                await interaction.followup.send("No token profile found or unable to fetch data.")
        except Exception as e:
            await interaction.followup.send(f"An error occurred while fetching the data: {str(e)}")