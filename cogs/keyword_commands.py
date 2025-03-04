import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from config import DEFAULT_KEYWORDS
from utils.storage import server_keywords, save_config
from utils.embed_builder import create_confirmation_embed

logger = logging.getLogger(__name__)

class KeywordCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setkeywords")
    async def set_keywords(self, ctx, *keywords):
        """Définit les mots-clés pour le filtrage des articles"""
        if not keywords:
            await ctx.send("Veuillez spécifier au moins un mot-clé. Exemple: `!setkeywords mot1 \"phrase avec espaces\" mot3`")
            return

        guild_id = str(ctx.guild.id)
        server_keywords[guild_id] = list(keywords)
        save_config()  # Sauvegarder la configuration

        # Créer un embed pour la confirmation
        embed = create_confirmation_embed(
            title="🔍 Mots-clés configurés",
            description="Les articles RSS seront filtrés selon ces mots-clés.",
            color=discord.Color.green(),
            author=ctx.author
        )

        # Ajouter les mots-clés
        keywords_str = "\n".join([f"• {keyword}" for keyword in keywords])
        embed.add_field(name="📝 Liste des mots-clés", value=keywords_str, inline=False)

        # Ajouter des informations
        embed.add_field(name="ℹ️ Information", value="Seuls les articles contenant au moins un de ces mots-clés seront publiés.", inline=False)

        # Ajouter un pied de page
        embed.set_footer(text=f"Configuré par {ctx.author.display_name} • Utilisez !clearkeywords pour désactiver le filtrage", 
                         icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        await ctx.send(embed=embed)
        logger.info(f"Mots-clés configurés pour le serveur {guild_id}: {keywords}")

    @commands.command(name="addkeywords")
    async def add_keywords(self, ctx, *keywords):
        """Ajoute des mots-clés à la liste existante"""
        if not keywords:
            await ctx.send("Veuillez spécifier au moins un mot-clé à ajouter.")
            return

        guild_id = str(ctx.guild.id)
        if guild_id not in server_keywords:
            server_keywords[guild_id] = []

        # Ajouter les nouveaux mots-clés
        added_keywords = []
        for keyword in keywords:
            if keyword not in server_keywords[guild_id]:
                server_keywords[guild_id].append(keyword)
                added_keywords.append(keyword)

        if not added_keywords:
            await ctx.send("Tous les mots-clés spécifiés sont déjà dans la liste.")
            return

        save_config()  # Sauvegarder la configuration

        # Créer un embed pour la confirmation
        embed = create_confirmation_embed(
            title="➕ Mots-clés ajoutés",
            description="Les mots-clés suivants ont été ajoutés à la liste de filtrage:",
            color=discord.Color.green(),
            author=ctx.author
        )

        # Ajouter les nouveaux mots-clés
        keywords_str = "\n".join([f"• {keyword}" for keyword in added_keywords])
        embed.add_field(name="📝 Nouveaux mots-clés", value=keywords_str, inline=False)

        # Ajouter la liste complète
        all_keywords_str = ", ".join(server_keywords[guild_id][:10])
        if len(server_keywords[guild_id]) > 10:
            all_keywords_str += f" et {len(server_keywords[guild_id]) - 10} autres..."

        embed.add_field(name="🔍 Liste complète", value=f"Il y a maintenant {len(server_keywords[guild_id])} mots-clés configurés.", inline=False)

        # Ajouter un pied de page
        embed.set_footer(text=f"Modifié par {ctx.author.display_name} • Utilisez !listkeywords pour voir tous les mots-clés", 
                         icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        await ctx.send(embed=embed)
        logger.info(f"Mots-clés ajoutés pour le serveur {guild_id}: {added_keywords}")

    @commands.command(name="removekeywords")
    async def remove_keywords(self, ctx, *keywords):
        """Supprime des mots-clés de la liste"""
        if not keywords:
            await ctx.send("Veuillez spécifier au moins un mot-clé à supprimer.")
            return

        guild_id = str(ctx.guild.id)
        if guild_id not in server_keywords or not server_keywords[guild_id]:
            await ctx.send("Aucun mot-clé n'est configuré pour ce serveur.")
            return

        # Supprimer les mots-clés
        removed = []
        for keyword in keywords:
            if keyword in server_keywords[guild_id]:
                server_keywords[guild_id].remove(keyword)
                removed.append(keyword)

        if not removed:
            await ctx.send("Aucun des mots-clés spécifiés n'a été trouvé dans la liste.")
            return

        save_config()  # Sauvegarder la configuration

        # Créer un embed pour la confirmation
        embed = create_confirmation_embed(
            title="➖ Mots-clés supprimés",
            description="Les mots-clés suivants ont été supprimés de la liste de filtrage:",
            color=discord.Color.orange(),
            author=ctx.author
        )

        # Ajouter les mots-clés supprimés
        keywords_str = "\n".join([f"• {keyword}" for keyword in removed])
        embed.add_field(name="📝 Mots-clés supprimés", value=keywords_str, inline=False)

        # Ajouter la liste restante
        if server_keywords[guild_id]:
            all_keywords_str = ", ".join(server_keywords[guild_id][:10])
            if len(server_keywords[guild_id]) > 10:
                all_keywords_str += f" et {len(server_keywords[guild_id]) - 10} autres..."
            
            embed.add_field(name="🔍 Liste restante", value=f"Il reste {len(server_keywords[guild_id])} mots-clés configurés.", inline=False)
        else:
            embed.add_field(name="🔍 Liste vide", value="Tous les mots-clés ont été supprimés. Le filtrage est désactivé.", inline=False)

        await ctx.send(embed=embed)
        logger.info(f"Mots-clés supprimés pour le serveur {guild_id}: {removed}")

    @commands.command(name="clearkeywords")
    async def clear_keywords(self, ctx):
        """Supprime tous les mots-clés (désactive le filtrage)"""
        guild_id = str(ctx.guild.id)
        if guild_id not in server_keywords or not server_keywords[guild_id]:
            await ctx.send("Aucun mot-clé n'est configuré pour ce serveur.")
            return

        keyword_count = len(server_keywords[guild_id])
        server_keywords[guild_id] = []
        save_config()  # Sauvegarder la configuration

        # Créer un embed pour la confirmation
        embed = create_confirmation_embed(
            title="🧹 Mots-clés effacés",
            description=f"Tous les mots-clés ({keyword_count}) ont été supprimés.",
            color=discord.Color.red(),
            author=ctx.author
        )

        embed.add_field(name="ℹ️ Information", value="Le filtrage est maintenant désactivé. Tous les articles RSS seront publiés.", inline=False)

        await ctx.send(embed=embed)
        logger.info(f"Tous les mots-clés ont été supprimés pour le serveur {guild_id}")

    @commands.command(name="listkeywords")
    async def list_keywords(self, ctx):
        """Affiche la liste des mots-clés configurés"""
        guild_id = str(ctx.guild.id)
        if guild_id not in server_keywords or not server_keywords[guild_id]:
            # Embed pour aucun mot-clé configuré
            embed = create_confirmation_embed(
                title="🔍 Liste des mots-clés",
                description="⚠️ Aucun mot-clé n'est configuré pour ce serveur.",
                color=discord.Color.orange(),
                author=ctx.author
            )
            embed.add_field(name="ℹ️ Information", value="Le filtrage est désactivé. Tous les articles RSS sont publiés.", inline=False)
            embed.add_field(name="💡 Conseil", value="Utilisez `!setkeywords mot1 mot2 ...` pour configurer des mots-clés.", inline=False)
            
            await ctx.send(embed=embed)
            return

        # Créer un embed pour la liste des mots-clés
        embed = discord.Embed(
            title="🔍 Liste des mots-clés",
            description=f"{len(server_keywords[guild_id])} mots-clés configurés pour le filtrage:",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        # Diviser les mots-clés en plusieurs champs si nécessaire
        keywords = server_keywords[guild_id]
        chunk_size = 15  # Nombre de mots-clés par champ

        for i in range(0, len(keywords), chunk_size):
            chunk = keywords[i:i+chunk_size]
            keywords_str = "\n".join([f"• {keyword}" for keyword in chunk])
            embed.add_field(name=f"📝 Mots-clés {i+1}-{i+len(chunk)}", value=keywords_str, inline=False)

        # Ajouter des informations
        embed.add_field(name="ℹ️ Information", value="Seuls les articles contenant au moins un de ces mots-clés seront publiés.", inline=False)

        # Ajouter un pied de page
        embed.set_footer(text=f"Demandé par {ctx.author.display_name} • Utilisez !help pour plus d'options", 
                         icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        await ctx.send(embed=embed)
        logger.info(f"Liste des mots-clés affichée pour le serveur {guild_id}")

    @commands.command(name="resetkeywords")
    async def reset_keywords(self, ctx):
        """Réinitialise les mots-clés avec la liste par défaut"""
        guild_id = str(ctx.guild.id)
        server_keywords[guild_id] = DEFAULT_KEYWORDS.copy()
        save_config()  # Sauvegarder la configuration

        # Créer un embed pour la confirmation
        embed = create_confirmation_embed(
            title="🔄 Mots-clés réinitialisés",
            description=f"Les mots-clés ont été réinitialisés avec la liste par défaut ({len(DEFAULT_KEYWORDS)} mots-clés).",
            color=discord.Color.purple(),
            author=ctx.author
        )

        # Ajouter quelques exemples de mots-clés
        examples = ", ".join(DEFAULT_KEYWORDS[:10])
        if len(DEFAULT_KEYWORDS) > 10:
            examples += f" et {len(DEFAULT_KEYWORDS) - 10} autres..."

        embed.add_field(name="📝 Exemples", value=examples, inline=False)
        embed.add_field(name="ℹ️ Information", value="Utilisez `!listkeywords` pour voir la liste complète.", inline=False)

        await ctx.send(embed=embed)
        logger.info(f"Mots-clés réinitialisés pour le serveur {guild_id}")

async def setup(bot):
    await bot.add_cog(KeywordCommands(bot))