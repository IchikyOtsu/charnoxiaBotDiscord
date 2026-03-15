import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

class CleanupBot(commands.Bot):
    def __init__(self):
        # Intents ne sont pas stricts ici pour juste nettoyer
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        guild_id = os.getenv("GUILD_ID")
        
        # 1. Nettoyer les commandes globales
        print("Suppression des commandes globales...")
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        
        # 2. Nettoyer les commandes du serveur spécifique (si applicable)
        if guild_id and guild_id.isdigit():
            guild = discord.Object(id=int(guild_id))
            print(f"Suppression des commandes pour le serveur {guild_id}...")
            self.tree.clear_commands(guild=guild)
            await self.tree.sync(guild=guild)
            
        print("Toutes les commandes ont été effacées avec succès.")
        await self.close()

bot = CleanupBot()

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
