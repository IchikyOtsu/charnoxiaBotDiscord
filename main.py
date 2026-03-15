import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Setup Supabase
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(URL, KEY)

# Setup Bot
class CharnoxiaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        # Load cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
        
        # Sync slash commands
        guild_id = os.getenv("GUILD_ID")
        if guild_id and guild_id.isdigit():
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Commandes synchronisées pour le serveur {guild_id}")
        else:
            await self.tree.sync()
            print("Commandes synchronisées globalement (peut prendre jusqu'à 1 heure)")


bot = CharnoxiaBot()

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user}')

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
