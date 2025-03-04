import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from config import PREFIX

logger = logging.getLogger(__name__)

class UtilityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Affiche l'aide pour les commandes RSS"""
        embed = discord.Embed(
            title="📚 Guide du Bot RSS",
            description="Voici les commandes disponibles pour gérer vos flux RSS et le filtrage par mots-clés.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        # Commandes de base
        embed.add_field(name="📡 Gestion des flux RSS", value=f"""
`{PREFIX}addrss #canal URL` - Ajoute un flux RSS à surveiller
`{PREFIX}removerss URL` - Supprime un flux RSS
`{PREFIX}listrss` - Liste tous les flux RSS configurés
`{PREFIX}testrss URL` - Teste un flux RSS
`{PREFIX}checkrss` - Force une vérification immédiate des flux RSS
""", inline=False)

        # Commandes de filtrage
        embed.add_field(name="🔍 Filtrage par mots-clés", value=f"""
`{PREFIX}setkeywords mot1 "phrase avec espaces" mot3` - Définit les mots-clés (remplace les existants)
`{PREFIX}addkeywords mot1 mot2` - Ajoute des mots-clés à la liste existante
`{PREFIX}removekeywords mot1 mot2` - Supprime des mots-clés spécifiques
`{PREFIX}clearkeywords` - Supprime tous les mots-clés (désactive le filtrage)
`{PREFIX}listkeywords` - Affiche la liste des mots-clés configurés
`{PREFIX}resetkeywords` - Réinitialise avec la liste de mots-clés par défaut
""", inline=False)

        # Exemples
        embed.add_field(name="💡 Exemples", value=f"""
`{PREFIX}addrss #actualités https://www.lemonde.fr/rss/une.xml`
`{PREFIX}setkeywords IA "intelligence artificielle" santé médecine`
`{PREFIX}testrss https://www.lemonde.fr/rss/une.xml`
`{PREFIX}checkrss` - Vérifie immédiatement tous les flux
""", inline=False)

        # Informations sur le filtrage
        embed.add_field(name="ℹ️ À propos du filtrage", value="""
Lorsque des mots-clés sont configurés, seuls les articles contenant au moins un de ces mots-clés seront publiés.
Le filtrage s'applique au titre, à la description et au contenu des articles.
Si aucun mot-clé n'est configuré, tous les articles seront publiés.
""", inline=False)

        # Informations sur la fréquence de vérification
        embed.add_field(name="⏱️ Fréquence de vérification", value=f"""
Le bot vérifie les flux RSS **toutes les 5 minutes** par défaut.
Utilisez `{PREFIX}checkrss` pour forcer une vérification immédiate.
""", inline=False)

        # Ajouter un pied de page
        embed.set_footer(text=f"Demandé par {ctx.author.display_name} • Bot RSS v3.0", 
                         icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        await ctx.send(embed=embed)

    @app_commands.command(name="help", description="Affiche l'aide pour les commandes RSS")
    async def slash_help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        
        embed = discord.Embed(
            title="📚 Guide du Bot RSS",
            description="Voici les commandes disponibles pour gérer vos flux RSS et le filtrage par mots-clés.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Commandes de base
        embed.add_field(name="📡 Gestion des flux RSS", value=f"""
`{PREFIX}addrss #canal URL` - Ajoute un flux RSS à surveiller
`{PREFIX}removerss URL` - Supprime un flux RSS
`{PREFIX}listrss` - Liste tous les flux RSS configurés
`{PREFIX}testrss URL` - Teste un flux RSS
`{PREFIX}checkrss` - Force une vérification immédiate des flux RSS
""", inline=False)
        
        # Commandes de filtrage
        embed.add_field(name="🔍 Filtrage par mots-clés", value=f"""
`{PREFIX}setkeywords mot1 "phrase avec espaces" mot3` - Définit les mots-clés (remplace les existants)
`{PREFIX}addkeywords mot1 mot2` - Ajoute des mots-clés à la liste existante
`{PREFIX}removekeywords mot1 mot2` - Supprime des mots-clés spécifiques
`{PREFIX}clearkeywords` - Supprime tous les mots-clés (désactive le filtrage)
`{PREFIX}listkeywords` - Affiche la liste des mots-clés configurés
`{PREFIX}resetkeywords` - Réinitialise avec la liste de mots-clés par défaut
""", inline=False)
        
        # Informations sur le filtrage
        embed.add_field(name="ℹ️ À propos du filtrage", value="""
Lorsque des mots-clés sont configurés, seuls les articles contenant au moins un de ces mots-clés seront publiés.
Le filtrage s'applique au titre, à la description et au contenu des articles.
Si aucun mot-clé n'est configuré, tous les articles seront publiés.
""", inline=False)
        
        # Informations sur la fréquence de vérification
        embed.add_field(name="⏱️ Fréquence de vérification", value=f"""
Le bot vérifie les flux RSS **toutes les 5 minutes** par défaut.
Utilisez `{PREFIX}checkrss` pour forcer une vérification immédiate.
""", inline=False)
        
        # Ajouter un pied de page
        embed.set_footer(text=f"Demandé par {interaction.user.display_name} • Bot RSS v3.0", 
                         icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))