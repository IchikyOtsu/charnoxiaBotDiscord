from discord import app_commands
from discord.ext import commands
import discord
from __main__ import supabase  # bad practice but quick hack for now, or just re-init

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
db: Client = create_client(url, key)

class Character(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="creer", description="Crée ton personnage (Explorateur ou autre, Contaminé ou non)")
    @app_commands.describe(date_naissance="Format requis : AAAA-MM-JJ (ex: 1995-10-25)")
    @app_commands.choices(role=[
        app_commands.Choice(name="Explorateur", value="explorateur"),
        app_commands.Choice(name="Autre", value="autre")
    ])
    @app_commands.choices(contamine=[
        app_commands.Choice(name="Oui (Forcera ton rôle à Explorateur)", value="oui"),
        app_commands.Choice(name="Non", value="non")
    ])
    @app_commands.choices(dome=[
        app_commands.Choice(name="Aurelis", value="aurelis"),
        app_commands.Choice(name="Verdancia", value="verdancia"),
        app_commands.Choice(name="Lumivor", value="lumivor"),
        app_commands.Choice(name="Crysalis", value="crysalis"),
        app_commands.Choice(name="Solarion", value="solarion"),
        app_commands.Choice(name="Nivara", value="nivara"),
        app_commands.Choice(name="Célestium", value="célestium"),
        app_commands.Choice(name="Virelia", value="virelia"),
        app_commands.Choice(name="Obsidara", value="obsidara"),
        app_commands.Choice(name="Eryndor", value="eryndor"),
        app_commands.Choice(name="Thaliora", value="thaliora"),
        app_commands.Choice(name="Argovian", value="argovian"),
        app_commands.Choice(name="Zephyrian", value="zephyrian"),
        app_commands.Choice(name="Orivane", value="orivane")
    ])
    async def create_character(self, interaction: discord.Interaction, prenom: str, nom: str, date_naissance: str, role: app_commands.Choice[str], contamine: app_commands.Choice[str], dome: app_commands.Choice[str], photo_profil: discord.Attachment):
        # Envoyer une réponse différée car l'upload d'image peut prendre quelques secondes
        await interaction.response.defer(ephemeral=False)

        # Validation de la date format YYYY-MM-DD
        import re
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_naissance):
            await interaction.followup.send("❌ La date de naissance doit être au format AAAA-MM-JJ (ex: 1990-05-15).", ephemeral=True)
            return

        is_contamine = contamine.value == "oui"
        final_role = "explorateur" if is_contamine else role.value
        
        # Check if already exists in this guild
        check = db.table('characters').select("*").eq('user_id', interaction.user.id).eq('guild_id', interaction.guild_id).execute()
        if check.data:
            await interaction.followup.send("❌ Tu as déjà un personnage sur ce serveur !", ephemeral=True)
            return
            
        # Upload Avatar to Supabase "avatars" bucket
        avatar_url = None
        if photo_profil.content_type and photo_profil.content_type.startswith("image/"):
            import time
            file_bytes = await photo_profil.read()
            # secure filename - ajout de l'extension dynamique
            ext = photo_profil.filename.split('.')[-1] if '.' in photo_profil.filename else 'png'
            path = f"{interaction.guild_id}_{interaction.user.id}_{int(time.time())}.{ext}"
            try:
                # Appeler Supabase de façon synchrone car le SDK courrant l'est 
                db.storage.from_("avatars").upload(
                    file=file_bytes, 
                    path=path, 
                    file_options={"content-type": photo_profil.content_type}
                )
                # Obtenir le lien public
                avatar_url = db.storage.from_("avatars").get_public_url(path)
                print(f"Image uploadée avec succès : {avatar_url}")
            except Exception as e:
                print(f"Erreur d'upload avatar : {e}")
                
        # Insert
        data = {
            "user_id": interaction.user.id,
            "guild_id": interaction.guild_id,
            "first_name": prenom,
            "last_name": nom,
            "birth_date": date_naissance,
            "role": final_role,
            "dome": dome.value,
            "is_contaminated": is_contamine,
            "balance": 0,
            "bank": 0,
            "avatar_url": avatar_url
        }
        
        db.table('characters').insert(data).execute()
        
        etat = "Contaminé" if is_contamine else "Sain"
        await interaction.followup.send(f"✅ Ton personnage **{prenom} {nom}** a été créé dans le dôme de **{dome.value.capitalize()}** ! Date de naissance: {date_naissance} | Rôle : {final_role.capitalize()} | État : {etat}.")

    @app_commands.command(name="profil", description="Affiche la carte d'identité de ton personnage sur ce serveur")
    async def profile(self, interaction: discord.Interaction, membre: discord.Member = None):
        target = membre or interaction.user
        res = db.table('characters').select("*").eq('user_id', target.id).eq('guild_id', interaction.guild_id).execute()
        
        if not res.data:
            await interaction.response.send_message(f"❌ {'Ce membre' if membre else 'Tu'} n'a pas encore de personnage sur ce serveur.", ephemeral=True)
            return
            
        p = res.data[0]
        etat = "⚠️ Contaminé" if p['is_contaminated'] else "✅ Sain"
        
        embed = discord.Embed(title=f"Carte d'identité de {p['first_name']} {p['last_name']}", color=discord.Color.blue())
        if p.get('avatar_url'):
            embed.set_thumbnail(url=p['avatar_url'])
        else:
            embed.set_thumbnail(url=target.display_avatar.url)
            
        embed.add_field(name="Date de Naissance", value=p.get('birth_date', 'Inconnue'), inline=False)
        embed.add_field(name="Dôme", value=p.get('dome', 'Inconnu').capitalize(), inline=True)
        embed.add_field(name="Rôle", value=p['role'].capitalize(), inline=True)
        embed.add_field(name="État", value=etat, inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="give-id", description="[Admin] Attribue une carte d'identité (image) à un joueur")
    @app_commands.default_permissions(manage_roles=True) # Réservé aux modérateurs/admins
    async def give_id(self, interaction: discord.Interaction, membre: discord.Member, image: discord.Attachment):
        if not image.content_type or not image.content_type.startswith("image/"):
            return await interaction.response.send_message("❌ Le fichier doit être une image.", ephemeral=True)
            
        await interaction.response.defer(ephemeral=False)
        
        # Vérif si le personnage existe
        res = db.table('characters').select("*").eq('user_id', membre.id).eq('guild_id', interaction.guild_id).execute()
        if not res.data:
            return await interaction.followup.send(f"❌ {membre.display_name} n'a pas de personnage sur ce serveur.", ephemeral=True)
            
        import time
        file_bytes = await image.read()
        path = f"{interaction.guild_id}_{membre.id}_{int(time.time())}.png"
        
        try:
            db.storage.from_("ids").upload(
                file=file_bytes, 
                path=path, 
                file_options={"content-type": image.content_type}
            )
            id_url = db.storage.from_("ids").get_public_url(path)
            
            # Update de la BDD
            db.table('characters').update({"id_card_url": id_url}).eq('user_id', membre.id).eq('guild_id', interaction.guild_id).execute()
            await interaction.followup.send(f"✅ La carte d'identité de {membre.mention} a bien été enregistrée !")
        except Exception as e:
            print(f"Erreur d'upload ID : {e}")
            await interaction.followup.send("❌ Une erreur est survenue lors de l'upload de l'image.")

    @app_commands.command(name="id", description="Affiche la photo de la carte d'identité")
    async def view_id(self, interaction: discord.Interaction, membre: discord.Member = None):
        target = membre or interaction.user
        res = db.table('characters').select("id_card_url, first_name, last_name").eq('user_id', target.id).eq('guild_id', interaction.guild_id).execute()
        
        if not res.data:
            return await interaction.response.send_message(f"❌ {'Ce membre' if membre else 'Tu'} n'a pas encore de personnage sur ce serveur.", ephemeral=True)
            
        p = res.data[0]
        if not p.get('id_card_url'):
            return await interaction.response.send_message(f"❌ Aucune carte d'identité image n'est enregistrée pour {'ce membre' if membre else 'toi'}.", ephemeral=True)
            
        embed = discord.Embed(title=f"Carte d'identité : {p['first_name']} {p['last_name']}", color=discord.Color.gold())
        embed.set_image(url=p['id_card_url'])
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Character(bot))
