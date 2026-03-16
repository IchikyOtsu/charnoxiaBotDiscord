import discord
from discord import app_commands
from discord.ext import commands
import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
db: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_character(self, user_id, guild_id):
        res = db.table('characters').select("*").eq('user_id', user_id).eq('guild_id', guild_id).execute()
        return res.data[0] if res.data else None

    @app_commands.command(name="inventaire", description="Affiche ton inventaire ou celui d'un autre joueur")
    async def inventaire(self, interaction: discord.Interaction, membre: discord.Member = None):
        target = membre or interaction.user
        p = await self.get_character(target.id, interaction.guild_id)
        if not p:
            return await interaction.response.send_message(f"❌ {'Ce membre' if membre else 'Tu'} n'a pas encore de personnage sur ce serveur.", ephemeral=True)
            
        inv = db.table('inventory').select("quantity, items(name, description)").eq('user_id', target.id).eq('guild_id', interaction.guild_id).execute()
        
        embed = discord.Embed(title=f"🎒 Inventaire de {p['first_name']} {p['last_name']}", color=discord.Color.brand_red())
        if not inv.data:
            embed.description = "_L'inventaire est complètement vide._"
        else:
            for row in inv.data:
                # La jointure Supabase imbrique les colonnes liées
                item_name = row['items']['name']
                item_desc = row['items']['description']
                qty = row['quantity']
                
                embed.add_field(name=f"[{qty}x] {item_name}", value=f"_{item_desc}_", inline=False)
                
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="item-add", description="[Admin] Crée un nouveau type d'objet en jeu")
    @app_commands.default_permissions(manage_guild=True)
    async def item_add(self, interaction: discord.Interaction, nom: str, description: str):
        try:
            # Insertion avec UUID généré par Python (évite l'erreur de null constraint si Supabase schema n'est pas à jour)
            generated_uuid = str(uuid.uuid4())
            res = db.table('items').insert({"id": generated_uuid, "name": nom, "description": description}).execute()
            if res.data:
                generated_id = res.data[0]['id']
                short_id = generated_id[:8]
                await interaction.response.send_message(f"✅ Objet **{nom}** créé ! Son ID complet est `...{short_id}...`.")
            else:
                await interaction.response.send_message("❌ Échec inexpliqué de la création de l'objet.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur: {e}", ephemeral=True)

    @app_commands.command(name="item-del", description="[Admin] Supprime définitivement un objet du jeu (Fournir l'ID ou début de l'ID)")
    @app_commands.default_permissions(manage_guild=True)
    async def item_del(self, interaction: discord.Interaction, search_id: str):
        # On essaie de trouver l'item qui commence par cet ID (pour permettre les vrais UUID ou les short UUID)
        items = db.table('items').select("id, name").ilike("id", f"{search_id}%").execute()
        
        if not items.data:
            return await interaction.response.send_message(f"❌ Objet introuvable avec l'ID **{search_id}**.", ephemeral=True)
        elif len(items.data) > 1:
            return await interaction.response.send_message(f"❌ Plus d'un objet correspond à cet ID court. Sois plus précis.", ephemeral=True)
            
        target_item = items.data[0]
        try:
            db.table('items').delete().eq("id", target_item['id']).execute()
            await interaction.response.send_message(f"🗑️ L'objet **{target_item['name']}** a été supprimé de la base et a disparu de tous les inventaires concernés.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur: {e}", ephemeral=True)

    @app_commands.command(name="item-list", description="Affiche la liste de tous les objets disponibles dans le jeu")
    async def item_list(self, interaction: discord.Interaction):
        items = db.table('items').select("*").execute()
        if not items.data:
            return await interaction.response.send_message("❌ Aucun objet n'est enregistré dans la base pour le moment.", ephemeral=True)
            
        embed = discord.Embed(title="📦 Encyclopédie des Objets", color=discord.Color.light_grey())
        for i in items.data:
            short_id = i['id'][:8]
            embed.add_field(name=f"{i['name']} (ID: {short_id})", value=i['description'], inline=False)
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="give-item", description="[Admin] Donne une quantité d'un objet (Fournir ID)")
    @app_commands.default_permissions(manage_guild=True)
    async def give_item(self, interaction: discord.Interaction, membre: discord.Member, search_id: str, quantite: int = 1):
        if quantite <= 0:
            return await interaction.response.send_message("❌ La quantité doit être supérieure à zéro.", ephemeral=True)
            
        item_check = db.table('items').select("id, name").ilike("id", f"{search_id}%").execute()
        if not item_check.data:
            return await interaction.response.send_message(f"❌ L'objet (ID: '{search_id}') n'existe pas. Vérifie avec `/item-list`.", ephemeral=True)
        elif len(item_check.data) > 1:
            return await interaction.response.send_message(f"❌ ID trop court, plusieurs objets correspondent.", ephemeral=True)
            
        real_item_id = item_check.data[0]['id']
        real_name = item_check.data[0]['name']
            
        p = await self.get_character(membre.id, interaction.guild_id)
        if not p:
            return await interaction.response.send_message(f"❌ {membre.display_name} n'a pas de personnage sur ce serveur.", ephemeral=True)
            
        # Check if user already has the item
        inv = db.table('inventory').select("*").eq('user_id', membre.id).eq('guild_id', interaction.guild_id).eq('item_id', real_item_id).execute()
        try:
            if inv.data:
                # Mise à jour du stack (quantité existante + nouvelle)
                db.table('inventory').update({"quantity": inv.data[0]['quantity'] + quantite}).eq('user_id', membre.id).eq('guild_id', interaction.guild_id).eq('item_id', real_item_id).execute()
            else:
                # Ajout de l'item dans sa poche s'il l'avait pas
                db.table('inventory').insert({
                    "user_id": membre.id, "guild_id": interaction.guild_id,
                    "item_id": real_item_id, "quantity": quantite
                }).execute()
            await interaction.response.send_message(f"🎁 Tu as glissé **{quantite}x {real_name}** dans le sac de {membre.mention}.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur lors de l'ajout : {e}", ephemeral=True)

    @app_commands.command(name="remove-item", description="[Admin] Retire une quantité d'un objet (Fournir ID)")
    @app_commands.default_permissions(manage_guild=True)
    async def remove_item(self, interaction: discord.Interaction, membre: discord.Member, search_id: str, quantite: int = 1):
        if quantite <= 0:
            return await interaction.response.send_message("❌ La quantité doit être supérieure à zéro.", ephemeral=True)
            
        item_check = db.table('items').select("id").ilike("id", f"{search_id}%").execute()
        if not item_check.data:
            return await interaction.response.send_message(f"❌ Objet (ID: '{search_id}') inconnu.", ephemeral=True)
        elif len(item_check.data) > 1:
            return await interaction.response.send_message(f"❌ ID trop court, plusieurs objets correspondent.", ephemeral=True)
            
        real_item_id = item_check.data[0]['id']

        inv = db.table('inventory').select("*").eq('user_id', membre.id).eq('guild_id', interaction.guild_id).eq('item_id', real_item_id).execute()
        
        if not inv.data:
            return await interaction.response.send_message(f"❌ Ce joueur ne possède pas du tout cet objet dans son inventaire.", ephemeral=True)
            
        current_qty = inv.data[0]['quantity']
        try:
            if current_qty <= quantite:
                # S'il lui en reste moins ou juste assez, on supprime la ligne de son inventaire (zéro=disparu)
                db.table('inventory').delete().eq('user_id', membre.id).eq('guild_id', interaction.guild_id).eq('item_id', real_item_id).execute()
                await interaction.response.send_message(f"🗑️ Tu as retiré complètement l'objet de l'inventaire de {membre.mention}.")
            else:
                # Sinon on réduit simplement la quantité
                db.table('inventory').update({"quantity": current_qty - quantite}).eq('user_id', membre.id).eq('guild_id', interaction.guild_id).eq('item_id', real_item_id).execute()
                await interaction.response.send_message(f"🗑️ Tu lui as retiré **{quantite}**. Il lui en reste encore {current_qty - quantite}.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Inventory(bot))
