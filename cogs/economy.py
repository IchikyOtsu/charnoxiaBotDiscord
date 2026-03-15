from discord import app_commands
from discord.ext import commands
import discord
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
db: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))


class TransactionModal(discord.ui.Modal):
    def __init__(self, action_type: str, bank_id: str, bank_name: str, pocket_balance: int, account_balance: int):
        title = "Dépôt d'argent" if action_type == "depot" else "Retrait d'argent"
        super().__init__(title=title)
        self.action_type = action_type
        self.bank_id = bank_id
        
        self.amount_input = discord.ui.TextInput(
            label="Montant en Nox 💠",
            style=discord.TextStyle.short,
            placeholder=f"Poche: {pocket_balance} | Banque: {account_balance}",
            required=True,
            min_length=1,
            max_length=9
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            montant = int(self.amount_input.value)
        except ValueError:
            return await interaction.response.send_message("❌ Le montant doit être un chiffre valide.", ephemeral=True)
            
        if montant <= 0:
            return await interaction.response.send_message("❌ Le montant doit être positif.", ephemeral=True)

        user_id = interaction.user.id
        guild_id = interaction.guild_id

        # Revérifier la bdd pour la sécurité (les montants peuvent avoir changé)
        p_res = db.table('characters').select("balance").eq('user_id', user_id).eq('guild_id', guild_id).execute()
        acc_res = db.table('bank_accounts').select("balance").eq('user_id', user_id).eq('guild_id', guild_id).eq('bank_id', self.bank_id).execute()

        if not p_res.data or not acc_res.data:
            return await interaction.response.send_message("❌ Erreur: Profil ou compte introuvable.", ephemeral=True)

        pocket = p_res.data[0]['balance']
        bank_bal = acc_res.data[0]['balance']

        if self.action_type == "depot":
            if pocket < montant:
                return await interaction.response.send_message(f"❌ Fonds insuffisants dans tes poches. Tu n'as que {pocket} Nox 💠.", ephemeral=True)
            new_pocket = pocket - montant
            new_bank = bank_bal + montant
            msg = f"✅ Tu as déposé **{montant} Nox 💠** dans ton compte **{self.bank_id}**."
        else:
            if bank_bal < montant:
                return await interaction.response.send_message(f"❌ Fonds insuffisants à la banque. Ton solde est de {bank_bal} Nox 💠.", ephemeral=True)
            new_pocket = pocket + montant
            new_bank = bank_bal - montant
            msg = f"✅ Tu as retiré **{montant} Nox 💠** de ton compte **{self.bank_id}**."

        # Mise à jour BDD (Characters + Bank Accounts)
        db.table('characters').update({"balance": new_pocket}).eq('user_id', user_id).eq('guild_id', guild_id).execute()
        db.table('bank_accounts').update({"balance": new_bank}).eq('user_id', user_id).eq('guild_id', guild_id).eq('bank_id', self.bank_id).execute()
        
        # Log Transaction
        db.table('bank_transactions').insert({
            'user_id': user_id,
            'guild_id': guild_id,
            'bank_id': self.bank_id,
            'transaction_type': self.action_type,
            'amount': montant
        }).execute()

        await interaction.response.send_message(msg, ephemeral=True)


class ATMView(discord.ui.View):
    def __init__(self, bank_id: str, bank_name: str, pocket_balance: int, account_balance: int):
        super().__init__(timeout=120)
        self.bank_id = bank_id
        self.bank_name = bank_name
        self.pocket_balance = pocket_balance
        self.account_balance = account_balance

    @discord.ui.button(label="Déposer", style=discord.ButtonStyle.green, emoji="📥")
    async def deposit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            TransactionModal("depot", self.bank_id, self.bank_name, self.pocket_balance, self.account_balance)
        )

    @discord.ui.button(label="Retirer", style=discord.ButtonStyle.red, emoji="📤")
    async def withdraw_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            TransactionModal("retrait", self.bank_id, self.bank_name, self.pocket_balance, self.account_balance)
        )


class CreateAccountView(discord.ui.View):
    def __init__(self, bank_id: str, bank_name: str):
        super().__init__(timeout=120)
        self.bank_id = bank_id
        self.bank_name = bank_name

    @discord.ui.button(label="Créer un compte", style=discord.ButtonStyle.blurple, emoji="📝")
    async def create_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Création du compte dans la DB
        try:
            db.table('bank_accounts').insert({
                "user_id": interaction.user.id,
                "guild_id": interaction.guild_id,
                "bank_id": self.bank_id,
                "balance": 0
            }).execute()
            await interaction.response.send_message(f"🎉 Félicitations ! Ton compte à la banque **{self.bank_name}** a été créé avec succès. Refais `/bank-access` pour l'utiliser !", ephemeral=True)
            self.stop()
        except Exception as e:
            await interaction.response.send_message("❌ Une erreur est survenue ou tu possèdes déjà un compte ici.", ephemeral=True)


class BankSelect(discord.ui.Select):
    def __init__(self, banks, pocket_balance: int):
        self.banks_data = {b['id']: b['name'] for b in banks}
        self.pocket_balance = pocket_balance
        
        options = [
            discord.SelectOption(label=b['name'], value=b['id'], description=b['description'][:100], emoji="🏦")
            for b in banks
        ]
        super().__init__(placeholder="🏧 Sélectionnez le guichet de votre banque...", options=options)

    async def callback(self, interaction: discord.Interaction):
        bank_id = self.values[0]
        bank_name = self.banks_data[bank_id]
        
        # Vérifier si l'utilisateur y a un compte
        res = db.table('bank_accounts').select("balance").eq('user_id', interaction.user.id).eq('guild_id', interaction.guild_id).eq('bank_id', bank_id).execute()
        
        if not res.data:
            # Pas de compte
            embed = discord.Embed(title=f"🏦 Guichet - {bank_name}", description="Tu n'as aucun compte ouvert dans cet établissement.", color=discord.Color.dark_gray())
            view = CreateAccountView(bank_id, bank_name)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            # Afficher l'ATM
            account_balance = res.data[0]['balance']
            embed = discord.Embed(title=f"🏦 Guichet Automatique - {bank_name}", color=discord.Color.brand_green())
            embed.add_field(name="Poches", value=f"**{self.pocket_balance}** Nox 💠", inline=True)
            embed.add_field(name="Solde Bancaire", value=f"**{account_balance}** Nox 💠", inline=True)
            embed.set_footer(text="Que souhaitez-vous faire ?")
            
            view = ATMView(bank_id, bank_name, self.pocket_balance, account_balance)
            await interaction.response.edit_message(embed=embed, view=view)


class BankAccessView(discord.ui.View):
    def __init__(self, banks, pocket_balance: int):
        super().__init__(timeout=120)
        self.add_item(BankSelect(banks, pocket_balance))


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_character(self, user_id, guild_id):
        res = db.table('characters').select("*").eq('user_id', user_id).eq('guild_id', guild_id).execute()
        return res.data[0] if res.data else None

    @app_commands.command(name="balance", description="Affiche l'argent que tu as sur toi et dans tes différentes banques.")
    async def balance(self, interaction: discord.Interaction):
        p = await self.get_character(interaction.user.id, interaction.guild_id)
        if not p:
            return await interaction.response.send_message("❌ Tu n'as pas de personnage sur ce serveur.", ephemeral=True)
            
        # Récupérer les comptes en banque
        accounts = db.table('bank_accounts').select("bank_id, balance").eq('user_id', interaction.user.id).eq('guild_id', interaction.guild_id).execute()
        
        embed = discord.Embed(title="💰 Bilan Financier", color=discord.Color.green())
        embed.add_field(name="Poches", value=f"**{p['balance']}** Nox 💠", inline=False)
        
        if accounts.data:
            banks_text = ""
            for acc in accounts.data:
                banks_text += f"🏦 **Banque [{acc['bank_id']}] :** {acc['balance']} Nox 💠\n"
            embed.add_field(name="Comptes en Banque", value=banks_text, inline=False)
        else:
            embed.add_field(name="Comptes en Banque", value="_Tu n'as aucun compte bancaire d'ouvert._", inline=False)
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bank-list", description="Affiche la liste des différentes banques du monde de Charnoxia")
    async def bank_list(self, interaction: discord.Interaction):
        banks = db.table('banks').select("*").execute()
        
        if not banks.data:
            return await interaction.response.send_message("❌ Aucune banque n'est disponible pour le moment.", ephemeral=True)
            
        embed = discord.Embed(title="🏛️ Les Banques de Charnoxia", description="Voici la liste des institutions financières officielles :", color=discord.Color.gold())
        
        for b in banks.data:
            embed.add_field(name=f"[{b['id']}] - {b['name']}", value=f"_{b['description']}_", inline=False)
            
        embed.set_footer(text="Utilise /bank-access pour utiliser leurs services")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bank-access", description="Ouvre l'interface du guichet de ta banque (ATM)")
    async def bank_access(self, interaction: discord.Interaction):
        p = await self.get_character(interaction.user.id, interaction.guild_id)
        if not p:
            return await interaction.response.send_message("❌ Tu dois d'abord créer un personnage (`/creer`) pour utiliser une banque.", ephemeral=True)
            
        banks_res = db.table('banks').select("*").execute()
        if not banks_res.data:
            return await interaction.response.send_message("❌ Le système bancaire est actuellement fermé (Aucune banque).", ephemeral=True)

        embed = discord.Embed(title="🏦 Accès Bancaire", description="Bienvenue aux services bancaires.\nVeuillez insérer votre carte et sélectionner un établissement ci-dessous.", color=discord.Color.dark_theme())
        view = BankAccessView(banks_res.data, p['balance'])
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="bank-add", description="[Admin] Ajoute une nouvelle banque au système")
    @app_commands.default_permissions(manage_guild=True)
    async def bank_add(self, interaction: discord.Interaction, acronyme: str, nom: str, description: str):
        # Vérification si l'acronyme existe déjà
        check = db.table('banks').select("id").eq("id", acronyme.upper()).execute()
        if check.data:
            return await interaction.response.send_message(f"❌ La banque avec l'acronyme **{acronyme.upper()}** existe déjà.", ephemeral=True)
            
        try:
            db.table('banks').insert({
                "id": acronyme.upper(),
                "name": nom,
                "description": description
            }).execute()
            await interaction.response.send_message(f"✅ La banque **{nom}** ({acronyme.upper()}) a été ajoutée avec succès.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur lors de l'ajout de la banque : {e}", ephemeral=True)

    @app_commands.command(name="bank-del", description="[Admin] Supprime une banque du système")
    @app_commands.default_permissions(manage_guild=True)
    async def bank_del(self, interaction: discord.Interaction, acronyme: str):
        # Vérification 
        check = db.table('banks').select("name").eq("id", acronyme.upper()).execute()
        if not check.data:
            return await interaction.response.send_message(f"❌ Aucune banque trouvée avec l'acronyme **{acronyme.upper()}**.", ephemeral=True)
            
        bank_name = check.data[0]['name']
        try:
            db.table('banks').delete().eq("id", acronyme.upper()).execute()
            await interaction.response.send_message(f"🗑️ La banque **{bank_name}** ({acronyme.upper()}) a été supprimée. (Tous les comptes associés ont été effacés).")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur lors de la suppression : {e}", ephemeral=True)

    @app_commands.command(name="admin-money-add", description="[Admin] Ajoute de l'argent dans les poches d'un joueur")
    @app_commands.default_permissions(manage_guild=True)
    async def admin_money_add(self, interaction: discord.Interaction, membre: discord.Member, montant: int):
        if montant <= 0:
            return await interaction.response.send_message("❌ Le montant doit être positif.", ephemeral=True)
            
        p = await self.get_character(membre.id, interaction.guild_id)
        if not p:
            return await interaction.response.send_message(f"❌ {membre.display_name} n'a pas de personnage sur ce serveur.", ephemeral=True)
            
        nouveau_solde = p['balance'] + montant
        try:
            db.table('characters').update({"balance": nouveau_solde}).eq("user_id", membre.id).eq("guild_id", interaction.guild_id).execute()
            
            # Log de l'admin (Optionnel mais recommandé)
            db.table('bank_transactions').insert({
                'user_id': membre.id,
                'guild_id': interaction.guild_id,
                'transaction_type': 'admin_add',
                'amount': montant
            }).execute()
            
            await interaction.response.send_message(f"✅ Tu as ajouté **{montant} Nox 💠** dans les poches de {membre.mention}.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur lors de la transaction : {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Economy(bot))
