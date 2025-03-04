import discord
from discord.ext import commands
from discord import app_commands
import feedparser
import asyncio
import logging
from datetime import datetime

# Correction des imports - utilisation d'imports relatifs à la racine du projet
import sys
import os
# Ajouter le répertoire parent du répertoire courant au chemin de recherche
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.storage import rss_configs, server_keywords, save_config, log_channels
from utils.rss_parser import get_color_for_url, contains_keywords, parse_date
from utils.embed_builder import create_article_embed, create_confirmation_embed
from utils.logger import send_log

logger = logging.getLogger(__name__)

class RSSCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="addrss")
    async def add_rss(self, ctx, channel: discord.TextChannel, rss_url: str):
        """Ajoute un flux RSS à surveiller"""
        try:
            feed = feedparser.parse(rss_url)
            if feed.bozo and not feed.entries:
                await ctx.send("URL RSS invalide ou inaccessible !")
                return
            
            guild_id = str(ctx.guild.id)
            if guild_id not in rss_configs:
                rss_configs[guild_id] = {"channel": channel.id, "feeds": {}}
            elif rss_configs[guild_id]["channel"] != channel.id:
                rss_configs[guild_id]["channel"] = channel.id
            
            # Stocker l'ID du dernier article
            last_entry_id = None
            if feed.entries:
                last_entry_id = getattr(feed.entries[0], 'id', None) or getattr(feed.entries[0], 'link', None)
            
            rss_configs[guild_id]["feeds"][rss_url] = last_entry_id
            save_config()  # Sauvegarder la configuration
            
            # Obtenir le titre du flux
            feed_title = feed.feed.title if hasattr(feed.feed, 'title') else "Flux RSS"
            
            # Créer un embed moderne pour la confirmation
            embed = discord.Embed(
                title="✅ Flux RSS ajouté avec succès",
                description=f"Le flux **{feed_title}** sera surveillé pour les nouveaux articles.",
                color=get_color_for_url(rss_url),
                timestamp=datetime.now()
            )
            
            # Ajouter une image si disponible
            if hasattr(feed.feed, 'image') and hasattr(feed.feed.image, 'href'):
                embed.set_thumbnail(url=feed.feed.image.href)
            
            embed.add_field(name="📡 URL du flux", value=f"```{rss_url}```", inline=False)
            embed.add_field(name="📢 Canal de publication", value=channel.mention, inline=True)
            
            # Ajouter des informations sur le filtrage
            guild_id_str = str(ctx.guild.id)
            if guild_id_str in server_keywords and server_keywords[guild_id_str]:
                keyword_count = len(server_keywords[guild_id_str])
                embed.add_field(name="🔍 Filtrage actif", value=f"{keyword_count} mots-clés configurés", inline=True)
            else:
                embed.add_field(name="🔍 Filtrage", value="Aucun (tous les articles seront publiés)", inline=True)
            
            # Ajouter un pied de page avec des instructions
            embed.set_footer(text=f"Ajouté par {ctx.author.display_name} • Utilisez !help pour plus d'options", 
                             icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            
            await ctx.send(embed=embed)
            logger.info(f"Flux RSS ajouté: {rss_url} pour le serveur {guild_id}")
            
            # Ajouter un log
            await send_log(
                self.bot, 
                ctx.guild.id, 
                f"Flux RSS ajouté: `{rss_url}`\nCanal: {channel.mention}", 
                color=discord.Color.green(),
                title="✅ Flux RSS ajouté"
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du flux RSS: {e}")
            await ctx.send(f"Erreur: {str(e)}")
    
    @commands.command(name="removerss")
    async def remove_rss(self, ctx, rss_url: str):
        """Supprime un flux RSS"""
        guild_id = str(ctx.guild.id)
        if guild_id not in rss_configs or rss_url not in rss_configs[guild_id]["feeds"]:
            await ctx.send("Ce flux RSS n'est pas configuré !")
            return

        del rss_configs[guild_id]["feeds"][rss_url]
        save_config()  # Sauvegarder la configuration

        # Créer un embed moderne pour la confirmation
        embed = create_confirmation_embed(
            title="🗑️ Flux RSS supprimé",
            description="Le flux RSS a été supprimé de la liste de surveillance.",
            color=discord.Color.red(),
            author=ctx.author
        )

        embed.add_field(name="📡 URL du flux", value=f"```{rss_url}```", inline=False)

        await ctx.send(embed=embed)
        logger.info(f"Flux RSS supprimé: {rss_url} du serveur {guild_id}")
        
        # Ajouter un log
        await send_log(
            self.bot, 
            ctx.guild.id, 
            f"Flux RSS supprimé: `{rss_url}`", 
            color=discord.Color.red(),
            title="🗑️ Flux RSS supprimé"
        )

    @commands.command(name="listrss")
    async def list_rss(self, ctx):
        """Liste les flux RSS configurés"""
        guild_id = str(ctx.guild.id)
        if guild_id not in rss_configs or not rss_configs[guild_id]["feeds"]:
            # Embed pour aucun flux configuré
            embed = create_confirmation_embed(
                title="📋 Flux RSS configurés",
                description="⚠️ Aucun flux RSS n'est configuré pour ce serveur.",
                color=discord.Color.orange(),
                author=ctx.author
            )
            embed.add_field(name="💡 Conseil", value="Utilisez `!addrss #canal URL` pour ajouter un flux RSS.", inline=False)
            
            await ctx.send(embed=embed)
            return

        channel = self.bot.get_channel(rss_configs[guild_id]["channel"])
        channel_mention = channel.mention if channel else "canal inconnu"

        # Créer un embed moderne pour la liste
        embed = discord.Embed(
            title="📋 Flux RSS configurés",
            description=f"Liste des flux RSS surveillés pour {channel_mention}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        # Ajouter les flux RSS
        for i, url in enumerate(rss_configs[guild_id]["feeds"].keys(), 1):
            embed.add_field(name=f"📡 Flux {i}", value=f"```{url}```", inline=False)

        # Ajouter des informations sur le filtrage
        if guild_id in server_keywords and server_keywords[guild_id]:
            keywords_str = ", ".join(server_keywords[guild_id][:5])
            if len(server_keywords[guild_id]) > 5:
                keywords_str += f" et {len(server_keywords[guild_id]) - 5} autres..."
            
            embed.add_field(name="🔍 Filtrage actif", value=f"Mots-clés: {keywords_str}", inline=False)
        else:
            embed.add_field(name="🔍 Filtrage", value="Aucun (tous les articles sont publiés)", inline=False)

        # Ajouter un pied de page
        embed.set_footer(text=f"Demandé par {ctx.author.display_name} • Utilisez !help pour plus d'options", 
                         icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        await ctx.send(embed=embed)

    @commands.command(name="testrss")
    async def test_rss(self, ctx, rss_url: str):
        """Teste un flux RSS configuré"""
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                await ctx.send("Aucune entrée trouvée dans le flux RSS.")
                return

            entry = feed.entries[0]
            
            # Vérifier si l'article contient des mots-clés (si configurés)
            guild_id = str(ctx.guild.id)
            keywords = server_keywords.get(guild_id, [])
            
            if keywords and not contains_keywords(entry, keywords):
                # Créer un embed pour indiquer que l'article ne contient pas de mots-clés
                embed = create_confirmation_embed(
                    title="⚠️ Test de filtrage",
                    description=f"L'article ne contient aucun des mots-clés configurés et ne serait pas publié.",
                    color=discord.Color.orange(),
                    author=ctx.author
                )
                
                embed.add_field(name="📝 Titre de l'article", value=entry.title, inline=False)
                embed.add_field(name="🔍 Mots-clés configurés", value=", ".join(keywords[:10]) + 
                               ("..." if len(keywords) > 10 else ""), inline=False)
                
                embed.set_footer(text="Utilisez !setkeywords pour modifier les mots-clés ou !clearkeywords pour les supprimer")
                
                await ctx.send(embed=embed)
                return
            
            # Créer un embed pour l'article
            embed = create_article_embed(entry, feed, rss_url)
            embed.set_footer(text=f"Test de flux RSS • Demandé par {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            
            # Ajouter un log
            await send_log(
                self.bot, 
                ctx.guild.id, 
                f"Test du flux RSS: `{rss_url}`\nArticle: {entry.title}", 
                color=discord.Color.blue(),
                title="🔍 Test de flux RSS"
            )
        except Exception as e:
            logger.error(f"Erreur lors du test RSS: {e}")
            await ctx.send(f"Erreur lors du test: {str(e)}")

    @commands.command(name="checkrss")
    @commands.has_permissions(manage_messages=True)  # Limite aux modérateurs
    async def force_check_rss(self, ctx):
        """Force une vérification immédiate des flux RSS"""
        await ctx.send("⏳ Vérification forcée des flux RSS en cours...")
        
        # Créer une tâche asynchrone pour la vérification
        asyncio.create_task(self.check_rss_once(ctx))
        
        logger.info(f"Vérification forcée des flux RSS demandée par {ctx.author}")
        
        # Ajouter un log
        await send_log(
            self.bot, 
            ctx.guild.id, 
            f"Vérification forcée des flux RSS demandée par {ctx.author.mention}", 
            color=discord.Color.blue(),
            title="🔄 Vérification forcée"
        )

    async def check_rss_once(self, ctx):
        """Vérifie les flux RSS une seule fois et envoie un rapport"""
        try:
            logger.info("Vérification forcée des flux RSS...")
            new_articles_count = 0
            checked_feeds = 0
            
            for guild_id, config in list(rss_configs.items()):
                channel = self.bot.get_channel(config["channel"])
                if not channel:
                    logger.warning(f"Channel introuvable pour guild {guild_id}")
                    continue

                # Obtenir les mots-clés pour ce serveur
                keywords = server_keywords.get(guild_id, [])
                
                for rss_url, last_id in list(config["feeds"].items()):
                    try:
                        logger.info(f"Vérification du flux: {rss_url}")
                        feed = feedparser.parse(rss_url)
                        checked_feeds += 1
                        
                        if not feed.entries:
                            logger.warning(f"Aucune entrée dans le flux: {rss_url}")
                            continue

                        # Initialiser last_id si c'est la première vérification
                        if last_id is None:
                            entry_id = getattr(feed.entries[0], 'id', None) or getattr(feed.entries[0], 'link', None)
                            rss_configs[guild_id]["feeds"][rss_url] = entry_id
                            save_config()  # Sauvegarder la configuration
                            logger.info(f"Premier ID enregistré pour {rss_url}: {entry_id}")
                            continue

                        # Trouver les nouvelles entrées
                        new_entries = []
                        for entry in feed.entries:
                            entry_id = getattr(entry, 'id', None) or getattr(entry, 'link', None)
                            if entry_id == last_id:
                                break
                            new_entries.append(entry)
                        
                        # Envoyer les nouvelles entrées
                        for entry in reversed(new_entries):  # Envoyer dans l'ordre chronologique
                            try:
                                # Vérifier si l'article contient des mots-clés (si configurés)
                                if keywords and not contains_keywords(entry, keywords):
                                    logger.info(f"Article filtré (ne contient pas de mots-clés): {entry.title}")
                                    continue
                                
                                # Créer un embed pour l'article
                                embed = create_article_embed(entry, feed, rss_url)
                                
                                await channel.send(embed=embed)
                                new_articles_count += 1
                                logger.info(f"Nouvel article envoyé: {entry.title}")
                            except Exception as e:
                                logger.error(f"Erreur lors de l'envoi d'un article: {e}")

                        # Mettre à jour le dernier ID
                        if feed.entries:
                            entry_id = getattr(feed.entries[0], 'id', None) or getattr(feed.entries[0], 'link', None)
                            rss_configs[guild_id]["feeds"][rss_url] = entry_id
                            save_config()  # Sauvegarder la configuration
                            logger.info(f"ID mis à jour pour {rss_url}: {entry_id}")
                    
                    except Exception as e:
                        logger.error(f"Erreur pour le flux {rss_url}: {e}")
                    
                    # Pause entre chaque flux pour éviter de surcharger
                    await asyncio.sleep(1)  # Pause plus courte pour la vérification forcée

            # Envoyer un rapport de la vérification
            embed = create_confirmation_embed(
                title="✅ Vérification RSS terminée",
                description=f"Vérification forcée des flux RSS terminée.",
                color=discord.Color.green(),
                author=ctx.author
            )
            
            embed.add_field(name="📊 Résultats", value=f"""
• Flux vérifiés: **{checked_feeds}**
• Nouveaux articles publiés: **{new_articles_count}**
            """, inline=False)
            
            await ctx.send(embed=embed)
            logger.info(f"Vérification forcée terminée. {new_articles_count} nouveaux articles publiés.")
            
            # Ajouter un log
            await send_log(
                self.bot, 
                ctx.guild.id, 
                f"Vérification forcée terminée.\n• Flux vérifiés: **{checked_feeds}**\n• Nouveaux articles publiés: **{new_articles_count}**", 
                color=discord.Color.green(),
                title="✅ Vérification terminée"
            )

        except Exception as e:
            logger.error(f"Erreur dans la vérification forcée: {e}")
            await ctx.send(f"❌ Erreur lors de la vérification forcée: {str(e)}")
            
            # Ajouter un log d'erreur
            await send_log(
                self.bot, 
                ctx.guild.id, 
                f"Erreur lors de la vérification forcée: {str(e)}", 
                color=discord.Color.red(),
                title="❌ Erreur de vérification"
            )

    # Commandes slash
    @app_commands.command(name="addrss", description="Ajoute un flux RSS à surveiller")
    @app_commands.describe(
        channel="Le canal où les articles seront publiés",
        rss_url="L'URL du flux RSS à surveiller"
    )
    async def slash_add_rss(self, interaction: discord.Interaction, channel: discord.TextChannel, rss_url: str):
        try:
            await interaction.response.defer(ephemeral=False)
            
            feed = feedparser.parse(rss_url)
            if feed.bozo and not feed.entries:
                await interaction.followup.send("URL RSS invalide ou inaccessible !")
                return
            
            guild_id = str(interaction.guild_id)
            if guild_id not in rss_configs:
                rss_configs[guild_id] = {"channel": channel.id, "feeds": {}}
            elif rss_configs[guild_id]["channel"] != channel.id:
                rss_configs[guild_id]["channel"] = channel.id
            
            # Stocker l'ID du dernier article
            last_entry_id = None
            if feed.entries:
                last_entry_id = getattr(feed.entries[0], 'id', None) or getattr(feed.entries[0], 'link', None)
            
            rss_configs[guild_id]["feeds"][rss_url] = last_entry_id
            save_config()  # Sauvegarder la configuration
            
            # Obtenir le titre du flux
            feed_title = feed.feed.title if hasattr(feed.feed, 'title') else "Flux RSS"
            
            # Créer un embed moderne pour la confirmation
            embed = discord.Embed(
                title="✅ Flux RSS ajouté avec succès",
                description=f"Le flux **{feed_title}** sera surveillé pour les nouveaux articles.",
                color=get_color_for_url(rss_url),
                timestamp=datetime.now()
            )
            
            # Ajouter une image si disponible
            if hasattr(feed.feed, 'image') and hasattr(feed.feed.image, 'href'):
                embed.set_thumbnail(url=feed.feed.image.href)
            
            embed.add_field(name="📡 URL du flux", value=f"```{rss_url}```", inline=False)
            embed.add_field(name="📢 Canal de publication", value=channel.mention, inline=True)
            
            # Ajouter des informations sur le filtrage
            guild_id_str = str(interaction.guild_id)
            if guild_id_str in server_keywords and server_keywords[guild_id_str]:
                keyword_count = len(server_keywords[guild_id_str])
                embed.add_field(name="🔍 Filtrage actif", value=f"{keyword_count} mots-clés configurés", inline=True)
            else:
                embed.add_field(name="🔍 Filtrage", value="Aucun (tous les articles seront publiés)", inline=True)
            
            # Ajouter un pied de page avec des instructions
            embed.set_footer(text=f"Ajouté par {interaction.user.display_name} • Utilisez /help pour plus d'options", 
                             icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Flux RSS ajouté: {rss_url} pour le serveur {guild_id}")
            
            # Ajouter un log
            await send_log(
                self.bot, 
                interaction.guild_id, 
                f"Flux RSS ajouté: `{rss_url}`\nCanal: {channel.mention}", 
                color=discord.Color.green(),
                title="✅ Flux RSS ajouté"
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du flux RSS: {e}")
            await interaction.followup.send(f"Erreur: {str(e)}")

    @app_commands.command(name="removerss", description="Supprime un flux RSS")
    @app_commands.describe(rss_url="L'URL du flux RSS à supprimer")
    async def slash_remove_rss(self, interaction: discord.Interaction, rss_url: str):
        await interaction.response.defer(ephemeral=False)
        
        guild_id = str(interaction.guild_id)
        if guild_id not in rss_configs or rss_url not in rss_configs[guild_id]["feeds"]:
            await interaction.followup.send("Ce flux RSS n'est pas configuré !")
            return

        del rss_configs[guild_id]["feeds"][rss_url]
        save_config()  # Sauvegarder la configuration

        # Créer un embed moderne pour la confirmation
        embed = create_confirmation_embed(
            title="🗑️ Flux RSS supprimé",
            description="Le flux RSS a été supprimé de la liste de surveillance.",
            color=discord.Color.red(),
            author=interaction.user
        )

        embed.add_field(name="📡 URL du flux", value=f"```{rss_url}```", inline=False)

        await interaction.followup.send(embed=embed)
        logger.info(f"Flux RSS supprimé: {rss_url} du serveur {guild_id}")
        
        # Ajouter un log
        await send_log(
            self.bot, 
            interaction.guild_id, 
            f"Flux RSS supprimé: `{rss_url}`", 
            color=discord.Color.red(),
            title="🗑️ Flux RSS supprimé"
        )

    @app_commands.command(name="listrss", description="Liste les flux RSS configurés")
    async def slash_list_rss(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        
        guild_id = str(interaction.guild_id)
        if guild_id not in rss_configs or not rss_configs[guild_id]["feeds"]:
            # Embed pour aucun flux configuré
            embed = create_confirmation_embed(
                title="📋 Flux RSS configurés",
                description="⚠️ Aucun flux RSS n'est configuré pour ce serveur.",
                color=discord.Color.orange(),
                author=interaction.user
            )
            embed.add_field(name="💡 Conseil", value="Utilisez `/addrss` pour ajouter un flux RSS.", inline=False)
            
            await interaction.followup.send(embed=embed)
            return

        channel = self.bot.get_channel(rss_configs[guild_id]["channel"])
        channel_mention = channel.mention if channel else "canal inconnu"

        # Créer un embed moderne pour la liste
        embed = discord.Embed(
            title="📋 Flux RSS configurés",
            description=f"Liste des flux RSS surveillés pour {channel_mention}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        # Ajouter les flux RSS
        for i, url in enumerate(rss_configs[guild_id]["feeds"].keys(), 1):
            embed.add_field(name=f"📡 Flux {i}", value=f"```{url}```", inline=False)

        # Ajouter des informations sur le filtrage
        if guild_id in server_keywords and server_keywords[guild_id]:
            keywords_str = ", ".join(server_keywords[guild_id][:5])
            if len(server_keywords[guild_id]) > 5:
                keywords_str += f" et {len(server_keywords[guild_id]) - 5} autres..."
            
            embed.add_field(name="🔍 Filtrage actif", value=f"Mots-clés: {keywords_str}", inline=False)
        else:
            embed.add_field(name="🔍 Filtrage", value="Aucun (tous les articles sont publiés)", inline=False)

        # Ajouter un pied de page
        embed.set_footer(text=f"Demandé par {interaction.user.display_name} • Utilisez /help pour plus d'options", 
                         icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="testrss", description="Teste un flux RSS configuré")
    @app_commands.describe(rss_url="L'URL du flux RSS à tester")
    async def slash_test_rss(self, interaction: discord.Interaction, rss_url: str):
        await interaction.response.defer(ephemeral=False)
        
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                await interaction.followup.send("Aucune entrée trouvée dans le flux RSS.")
                return

            entry = feed.entries[0]
            
            # Vérifier si l'article contient des mots-clés (si configurés)
            guild_id = str(interaction.guild_id)
            keywords = server_keywords.get(guild_id, [])
            
            if keywords and not contains_keywords(entry, keywords):
                # Créer un embed pour indiquer que l'article ne contient pas de mots-clés
                embed = create_confirmation_embed(
                    title="⚠️ Test de filtrage",
                    description=f"L'article ne contient aucun des mots-clés configurés et ne serait pas publié.",
                    color=discord.Color.orange(),
                    author=interaction.user
                )
                
                embed.add_field(name="📝 Titre de l'article", value=entry.title, inline=False)
                embed.add_field(name="🔍 Mots-clés configurés", value=", ".join(keywords[:10]) + 
                               ("..." if len(keywords) > 10 else ""), inline=False)
                
                embed.set_footer(text="Utilisez /setkeywords pour modifier les mots-clés")
                
                await interaction.followup.send(embed=embed)
                return
            
            # Créer un embed pour l'article
            embed = create_article_embed(entry, feed, rss_url)
            embed.set_footer(text=f"Test de flux RSS • Demandé par {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed)
            
            # Ajouter un log
            await send_log(
                self.bot, 
                interaction.guild_id, 
                f"Test du flux RSS: `{rss_url}`\nArticle: {entry.title}", 
                color=discord.Color.blue(),
                title="🔍 Test de flux RSS"
            )
        except Exception as e:
            logger.error(f"Erreur lors du test RSS: {e}")
            await interaction.followup.send(f"Erreur lors du test: {str(e)}")

    @app_commands.command(name="checkrss", description="Force une vérification immédiate des flux RSS")
    async def slash_force_check_rss(self, interaction: discord.Interaction):
        # Vérifier les permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Vous n'avez pas les permissions nécessaires pour utiliser cette commande.", ephemeral=True)
            return
        
        await interaction.response.send_message("⏳ Vérification forcée des flux RSS en cours...")
        
        # Créer un contexte simulé pour la fonction check_rss_once
        class SimulatedContext:
            def __init__(self, interaction):
                self.author = interaction.user
                self.guild = interaction.guild
                self.send = interaction.followup.send
        
        # Créer une tâche asynchrone pour la vérification
        asyncio.create_task(self.check_rss_once(SimulatedContext(interaction)))
        
        logger.info(f"Vérification forcée des flux RSS demandée par {interaction.user}")
        
        # Ajouter un log
        await send_log(
            self.bot, 
            interaction.guild_id, 
            f"Vérification forcée des flux RSS demandée par {interaction.user.mention}", 
            color=discord.Color.blue(),
            title="🔄 Vérification forcée"
        )

# Fonction pour vérifier les flux RSS (utilisée par la tâche périodique)
async def check_rss_feeds(bot):
    """Vérifie périodiquement les flux RSS pour de nouveaux articles"""
    try:
        logger.info("Vérification des flux RSS...")
        new_articles_count = 0
        
        for guild_id, config in list(rss_configs.items()):
            # Envoyer un log au début de la vérification
            await send_log(
                bot, 
                guild_id, 
                f"Vérification des flux RSS en cours...", 
                color=discord.Color.blue(),
                title="🔄 Vérification des flux"
            )
            
            channel = bot.get_channel(config["channel"])
            if not channel:
                logger.warning(f"Channel introuvable pour guild {guild_id}")
                continue

            # Obtenir les mots-clés pour ce serveur
            keywords = server_keywords.get(guild_id, [])
            guild_new_articles = 0
            
            for rss_url, last_id in list(config["feeds"].items()):
                try:
                    logger.info(f"Vérification du flux: {rss_url}")
                    feed = feedparser.parse(rss_url)
                    
                    if not feed.entries:
                        logger.warning(f"Aucune entrée dans le flux: {rss_url}")
                        continue

                    # Initialiser last_id si c'est la première vérification
                    if last_id is None:
                        entry_id = getattr(feed.entries[0], 'id', None) or getattr(feed.entries[0], 'link', None)
                        rss_configs[guild_id]["feeds"][rss_url] = entry_id
                        save_config()  # Sauvegarder la configuration
                        logger.info(f"Premier ID enregistré pour {rss_url}: {entry_id}")
                        continue

                    # Trouver les nouvelles entrées
                    new_entries = []
                    for entry in feed.entries:
                        entry_id = getattr(entry, 'id', None) or getattr(entry, 'link', None)
                        if entry_id == last_id:
                            break
                        new_entries.append(entry)
                    
                    # Envoyer les nouvelles entrées
                    for entry in reversed(new_entries):  # Envoyer dans l'ordre chronologique
                        try:
                            # Vérifier si l'article contient des mots-clés (si configurés)
                            if keywords and not contains_keywords(entry, keywords):
                                logger.info(f"Article filtré (ne contient pas de mots-clés): {entry.title}")
                                continue
                            
                            # Créer un embed pour l'article
                            embed = create_article_embed(entry, feed, rss_url)
                            
                            await channel.send(embed=embed)
                            new_articles_count += 1
                            guild_new_articles += 1
                            logger.info(f"Nouvel article envoyé: {entry.title}")
                        except Exception as e:
                            logger.error(f"Erreur lors de l'envoi d'un article: {e}")

                    # Mettre à jour le dernier ID
                    if feed.entries:
                        entry_id = getattr(feed.entries[0], 'id', None) or getattr(feed.entries[0], 'link', None)
                        rss_configs[guild_id]["feeds"][rss_url] = entry_id
                        save_config()  # Sauvegarder la configuration
                        logger.info(f"ID mis à jour pour {rss_url}: {entry_id}")
                
                except Exception as e:
                    logger.error(f"Erreur pour le flux {rss_url}: {e}")
                    
                    # Envoyer un log d'erreur
                    await send_log(
                        bot, 
                        guild_id, 
                        f"Erreur lors de la vérification du flux `{rss_url}`: {str(e)}", 
                        color=discord.Color.red(),
                        title="❌ Erreur de vérification"
                    )
                
                # Pause entre chaque flux pour éviter de surcharger
                await asyncio.sleep(2)
            
            # Envoyer un log à la fin de la vérification
            await send_log(
                bot, 
                guild_id, 
                f"Vérification terminée. {guild_new_articles} nouveaux articles publiés.", 
                color=discord.Color.green(),
                title="✅ Vérification terminée"
            )

        logger.info(f"Cycle de vérification terminé. {new_articles_count} nouveaux articles publiés.")

    except Exception as e:
        logger.error(f"Erreur dans check_rss: {e}")

async def setup(bot):
    await bot.add_cog(RSSCommands(bot))