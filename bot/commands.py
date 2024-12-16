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
    
    @client.tree.command(name="check", description="Check general information about token. Token address required for input.")
    async def check(interaction: discord.Interaction, token_address: str):
        # First validate the input
        if not DexScreenerService.is_valid_pair_id(token_address):
            await interaction.response.send_message("Input is not a valid address")
            return
        
        # Defer reply since we're making an API call
        await interaction.response.defer()
        
        try:
            pair_info = await DexScreenerService.fetch_pair_info(token_address)
            rugcheck_info = await DexScreenerService.fetch_rugcheck(token_address)
            print(rugcheck_info)
            if pair_info:
                # Format the response
                response = (
                    f"URL: {pair_info.get('url', 'N/A')}\n"
                    f"DEX ID: {pair_info.get('dexId', 'N/A')}\n"
                    f"Market Cap: ${pair_info.get('marketCap', 0):,.2f}\n"
                    f"Quote Token: {pair_info.get('quoteToken', {}).get('name', 'N/A')}\n"
                    f"Rugcheck score: {rugcheck_info.get('score', 0)}"
                )
                await interaction.followup.send(response)
            else:
                await interaction.followup.send("No pair information found for this ID")
        except Exception as e:
            await interaction.followup.send(f"An error occurred while fetching the pair information: {str(e)}")

    
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