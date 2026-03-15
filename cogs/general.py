from discord import app_commands
from discord.ext import commands
import discord

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Affiche la liste de toutes les commandes disponibles")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📜 Guide des Commandes de Charnoxia",
            description="Voici la liste complète des commandes pour interagir avec le monde et son économie.",
            color=discord.Color.blurple()
        )
        
        # Section Personnage
        character_cmds = (
            "**`/creer`** - Crée ton personnage (Infos, Dôme, Photo).\n"
            "**`/profil`** - Affiche la carte d'identité texte de ton personnage.\n"
            "**`/id`** - Affiche l'image officielle de ta carte d'identité."
        )
        embed.add_field(name="🧬 Personnage", value=character_cmds, inline=False)
        
        # Section Économie
        economy_cmds = (
            "**`/balance`** - Affiche tes poches et tes comptes bancaires.\n"
            "**`/bank-list`** - Affiche les banques disponibles dans le monde.\n"
            "**`/bank-access`** - Ouvre un guichet ATM pour créer un compte, déposer ou retirer de l'argent."
        )
        embed.add_field(name="💰 Économie & Banques", value=economy_cmds, inline=False)
        
        # Section Administration
        admin_cmds = (
            "**`/give-id`** - [Modo] Donne une image de carte d'ID à un membre.\n"
            "**`/admin-money-add`** - [Admin] Donne des Nox 💠 directement dans la poche d'un membre.\n"
            "**`/bank-add`** - [Admin] Crée une nouvelle banque officielle.\n"
            "**`/bank-del`** - [Admin] Supprime une banque (et tous ses comptes)."
        )
        embed.add_field(name="⚙️ Administration", value=admin_cmds, inline=False)
        
        embed.set_footer(text="Bot développé pour le monde de Charnoxia")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(General(bot))