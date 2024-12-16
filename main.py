from config import DISCORD_TOKEN
from bot.client import PonderBot
from bot.commands import setup_commands

def main():
        client = PonderBot()
        setup_commands(client)
        client.run(DISCORD_TOKEN)
if __name__ == "__main__":
    main()