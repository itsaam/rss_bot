import discord
from discord.ext import commands, tasks
from discord import app_commands
import feedparser
from datetime import datetime
import asyncio
import logging
import random
import hashlib
import time
import re
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
import json
import os

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration du bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Désactiver la commande help par défaut
bot.remove_command('help')

# Stockage des configurations RSS
rss_configs = {}
DATE_FORMAT = "%d %b %Y %H:%M:%S"

# Fichier pour sauvegarder les configurations
CONFIG_FILE = "rss_config.json"

# Liste des mots-clés pour le filtrage (par défaut)
DEFAULT_KEYWORDS = [
# Anglais
"AI healthcare", "medical AI", "cancer detection", "radiology AI", "MRI AI",
"CT scan AI", "deep learning medical", "AI diagnosis", "AI genomics", "AI surgery",
"robotic surgery AI", "biomedical AI", "AI drug discovery", "AI imaging",
"AI in medicine", "AI medical research", "AI patient care", "machine learning healthcare",
"neural networks medical", "AI-assisted diagnosis", "AI healthtech", "AI medical analysis",
"AI-powered radiology", "AI pathology", "medical deep learning",
# Français
"intelligence artificielle médicale", "santé IA", "diagnostic IA", "IA médicale",
"apprentissage profond médical", "détection du cancer IA", "radiologie IA", "IRM IA",
"scan médical IA", "diagnostic assisté par IA", "réseaux neuronaux santé",
"analyse médicale IA", "robotique chirurgicale IA", "pathologie IA", "imagerie médicale IA",
"technologie médicale IA", "traitement médical IA", "modèles IA santé",
"chirurgie assistée par IA", "IA"
]

# Dictionnaire pour stocker les mots-clés par serveur
server_keywords = {}

# Fonction pour générer une couleur basée sur l'URL du flux
def get_color_for_url(url):
    hash_object = hashlib.md5(url.encode())
    hash_hex = hash_object.hexdigest()

    # Convertir les 6 premiers caractères du hash en une couleur RGB
    r = int(hash_hex[0:2], 16)
    g = int(hash_hex[2:4], 16)
    b = int(hash_hex[4:6], 16)

    # Assurer que la couleur n'est pas trop sombre
    if r + g + b < 300:
        r = min(r + 100, 255)
        g = min(g + 100, 255)
        b = min(b + 100, 255)

    # Convertir en valeur décimale pour Discord
    return (r << 16) + (g << 8) + b

# Fonction pour parser la date d'un article RSS
def parse_date(entry):
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime(*entry.published_parsed[:6])
    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6])
    elif hasattr(entry, 'published') and entry.published:
        try:
            return parsedate_to_datetime(entry.published)
        except:
            pass
    elif hasattr(entry, 'updated') and entry.updated:
        try:
            return parsedate_to_datetime(entry.updated)
        except:
            pass

    return datetime.now()

# Fonction pour nettoyer le HTML
def clean_html(html_text):
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, 'html.parser')
    return soup.get_text(separator=' ', strip=True)

# Fonction pour vérifier si un article contient des mots-clés
def contains_keywords(entry, keywords):
    if not keywords:  # Si aucun mot-clé n'est spécifié, tout est accepté
        return True

    # Obtenir le texte à vérifier
    text_to_check = ""

    # Ajouter le titre
    if hasattr(entry, 'title'):
        text_to_check += entry.title + " "

    # Ajouter la description/résumé
    if hasattr(entry, 'summary'):
        text_to_check += clean_html(entry.summary) + " "
    elif hasattr(entry, 'description'):
        text_to_check += clean_html(entry.description) + " "

    # Ajouter le contenu
    if hasattr(entry, 'content'):
        for content in entry.content:
            if 'value' in content:
                text_to_check += clean_html(content.value) + " "

    # Convertir en minuscules pour une recherche insensible à la casse
    text_to_check = text_to_check.lower()

    # Vérifier chaque mot-clé
    for keyword in keywords:
        if keyword.lower() in text_to_check:
            return True

    return False

# Fonction pour sauvegarder les configurations
def save_config():
    config_data = {
        "rss_configs": rss_configs,
        "server_keywords": server_keywords
    }

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

# Fonction pour charger les configurations
def load_config():
    global rss_configs, server_keywords

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                rss_configs = config_data.get("rss_configs", {})
                server_keywords = config_data.get("server_keywords", {})
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")

@bot.event
async def on_ready():
    logger.info(f'Bot connecté en tant que {bot.user}')
    
    # Synchroniser les commandes slash avec Discord
    try:
        synced = await bot.tree.sync()
        logger.info(f"Commandes slash synchronisées: {len(synced)} commandes")
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation des commandes slash: {e}")
    
    # Charger les configurations
    load_config()
    
    # Démarrer la tâche de vérification RSS
    check_rss.start()

@tasks.loop(minutes=10)  # Change l'activité toutes les 10 minutes
async def change_activity():
    """Change l'activité du bot périodiquement"""
    activities = [
        discord.Activity(type=discord.ActivityType.watching, name="les flux RSS"),
        discord.Activity(type=discord.ActivityType.listening, name="les nouvelles"),
        discord.Game(name="!help pour l'aide"),
        discord.Activity(type=discord.ActivityType.watching, name=f"{len(rss_configs)} serveurs"),
        discord.Game(name="Surveiller l'actualité"),
        discord.Activity(type=discord.ActivityType.listening, name="!checkrss")
    ]
    
    activity = random.choice(activities)
    await bot.change_presence(activity=activity)
    logger.info(f"Activité changée: {activity.name}")

# Modifier la fonction on_ready pour démarrer la tâche de changement d'activité
@bot.event
async def on_ready():
    logger.info(f'Bot connecté en tant que {bot.user}')
    
    # Synchroniser les commandes slash avec Discord
    try:
        synced = await bot.tree.sync()
        logger.info(f"Commandes slash synchronisées: {len(synced)} commandes")
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation des commandes slash: {e}")
    
    # Charger les configurations
    load_config()
    
    # Démarrer la tâche de vérification RSS
    check_rss.start()
    
    # Démarrer la tâche de changement d'activité
    change_activity.start()
    
    # Définir l'activité initiale
    await bot.change_presence(activity=discord.Game(name="!help pour l'aide"))
    
# ===== COMMANDES PRÉFIXÉES (!) =====

@bot.command(name="addrss")
async def add_rss(ctx, channel: discord.TextChannel, rss_url: str):
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
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout du flux RSS: {e}")
        await ctx.send(f"Erreur: {str(e)}")

@bot.command(name="removerss")
async def remove_rss(ctx, rss_url: str):
    """Supprime un flux RSS"""
    guild_id = str(ctx.guild.id)
    if guild_id not in rss_configs or rss_url not in rss_configs[guild_id]["feeds"]:
        await ctx.send("Ce flux RSS n'est pas configuré !")
        return

    del rss_configs[guild_id]["feeds"][rss_url]
    save_config()  # Sauvegarder la configuration

    # Créer un embed moderne pour la confirmation
    embed = discord.Embed(
        title="🗑️ Flux RSS supprimé",
        description="Le flux RSS a été supprimé de la liste de surveillance.",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )

    embed.add_field(name="📡 URL du flux", value=f"```{rss_url}```", inline=False)

    # Ajouter un pied de page
    embed.set_footer(text=f"Supprimé par {ctx.author.display_name}", 
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

    await ctx.send(embed=embed)
    logger.info(f"Flux RSS supprimé: {rss_url} du serveur {guild_id}")

@bot.command(name="listrss")
async def list_rss(ctx):
    """Liste les flux RSS configurés"""
    guild_id = str(ctx.guild.id)
    if guild_id not in rss_configs or not rss_configs[guild_id]["feeds"]:
        # Embed pour aucun flux configuré
        embed = discord.Embed(
            title="📋 Flux RSS configurés",
            description="⚠️ Aucun flux RSS n'est configuré pour ce serveur.",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="💡 Conseil", value="Utilisez `!addrss #canal URL` pour ajouter un flux RSS.", inline=False)
        embed.set_footer(text=f"Demandé par {ctx.author.display_name}", 
                         icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
        return

    channel = bot.get_channel(rss_configs[guild_id]["channel"])
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

@bot.command(name="testrss")
async def test_rss(ctx, rss_url: str):
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
            embed = discord.Embed(
                title="⚠️ Test de filtrage",
                description=f"L'article ne contient aucun des mots-clés configurés et ne serait pas publié.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="📝 Titre de l'article", value=entry.title, inline=False)
            embed.add_field(name="🔍 Mots-clés configurés", value=", ".join(keywords[:10]) + 
                           ("..." if len(keywords) > 10 else ""), inline=False)
            
            embed.set_footer(text="Utilisez !setkeywords pour modifier les mots-clés ou !clearkeywords pour les supprimer")
            
            await ctx.send(embed=embed)
            return
        
        # Obtenir la date de publication
        pub_date = parse_date(entry)
        
        # Obtenir le titre du flux
        feed_title = feed.feed.title if hasattr(feed.feed, 'title') else "Flux RSS"
        
        # Obtenir la description/résumé
        description = ""
        if hasattr(entry, 'summary'):
            description = clean_html(entry.summary)
        elif hasattr(entry, 'description'):
            description = clean_html(entry.description)
        
        # Limiter la longueur de la description
        if len(description) > 300:
            description = description[:300] + "..."
        
        # Créer un embed moderne pour l'article
        embed = discord.Embed(
            title=entry.title,
            url=entry.link,
            description=description,
            color=get_color_for_url(rss_url),
            timestamp=pub_date
        )
        
        # Ajouter l'image du flux si disponible
        if hasattr(feed.feed, 'image') and hasattr(feed.feed.image, 'href'):
            embed.set_author(name=feed_title, url=feed.feed.link if hasattr(feed.feed, 'link') else None,
                            icon_url=feed.feed.image.href)
        else:
            embed.set_author(name=feed_title, url=feed.feed.link if hasattr(feed.feed, 'link') else None)
        
        # Ajouter l'image de l'article si disponible
        image_url = None
        
        # Vérifier les médias
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if 'url' in media and media['url'].endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    image_url = media['url']
                    break
        
        # Vérifier les enclosures
        if not image_url and hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if 'type' in enclosure and enclosure['type'].startswith('image/'):
                    image_url = enclosure['href']
                    break
        
        # Vérifier les liens
        if not image_url and hasattr(entry, 'links'):
            for link in entry.links:
                if 'type' in link and link['type'].startswith('image/'):
                    image_url = link['href']
                    break
        
        if image_url:
            embed.set_image(url=image_url)
        
        # Ajouter l'auteur si disponible
        if hasattr(entry, 'author'):
            embed.add_field(name="✍️ Auteur", value=entry.author, inline=True)
        
        # Ajouter les catégories si disponibles
        if hasattr(entry, 'tags'):
            categories = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
            if categories:
                embed.add_field(name="🏷️ Catégories", value=", ".join(categories[:5]) + 
                               ("..." if len(categories) > 5 else ""), inline=True)
        
        # Ajouter un pied de page
        formatted_date = pub_date.strftime(DATE_FORMAT)
        embed.set_footer(text=f"Publié le {formatted_date} • Test de flux RSS")
        
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Erreur lors du test RSS: {e}")
        await ctx.send(f"Erreur lors du test: {str(e)}")

@bot.command(name="setkeywords")
async def set_keywords(ctx, *keywords):
    """Définit les mots-clés pour le filtrage des articles"""
    if not keywords:
        await ctx.send("Veuillez spécifier au moins un mot-clé. Exemple: `!setkeywords mot1 \"phrase avec espaces\" mot3`")
        return

    guild_id = str(ctx.guild.id)
    server_keywords[guild_id] = list(keywords)
    save_config()  # Sauvegarder la configuration

    # Créer un embed pour la confirmation
    embed = discord.Embed(
        title="🔍 Mots-clés configurés",
        description="Les articles RSS seront filtrés selon ces mots-clés.",
        color=discord.Color.green(),
        timestamp=datetime.now()
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

@bot.command(name="addkeywords")
async def add_keywords(ctx, *keywords):
    """Ajoute des mots-clés à la liste existante"""
    if not keywords:
        await ctx.send("Veuillez spécifier au moins un mot-clé à ajouter.")
        return

    guild_id = str(ctx.guild.id)
    if guild_id not in server_keywords:
        server_keywords[guild_id] = []

    # Ajouter les nouveaux mots-clés
    for keyword in keywords:
        if keyword not in server_keywords[guild_id]:
            server_keywords[guild_id].append(keyword)

    save_config()  # Sauvegarder la configuration

    # Créer un embed pour la confirmation
    embed = discord.Embed(
        title="➕ Mots-clés ajoutés",
        description="Les mots-clés suivants ont été ajoutés à la liste de filtrage:",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )

    # Ajouter les nouveaux mots-clés
    keywords_str = "\n".join([f"• {keyword}" for keyword in keywords])
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
    logger.info(f"Mots-clés ajoutés pour le serveur {guild_id}: {keywords}")

@bot.command(name="removekeywords")
async def remove_keywords(ctx, *keywords):
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
    embed = discord.Embed(
        title="➖ Mots-clés supprimés",
        description="Les mots-clés suivants ont été supprimés de la liste de filtrage:",
        color=discord.Color.orange(),
        timestamp=datetime.now()
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

    # Ajouter un pied de page
    embed.set_footer(text=f"Modifié par {ctx.author.display_name}", 
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

    await ctx.send(embed=embed)
    logger.info(f"Mots-clés supprimés pour le serveur {guild_id}: {removed}")

@bot.command(name="clearkeywords")
async def clear_keywords(ctx):
    """Supprime tous les mots-clés (désactive le filtrage)"""
    guild_id = str(ctx.guild.id)
    if guild_id not in server_keywords or not server_keywords[guild_id]:
        await ctx.send("Aucun mot-clé n'est configuré pour ce serveur.")
        return

    keyword_count = len(server_keywords[guild_id])
    server_keywords[guild_id] = []
    save_config()  # Sauvegarder la configuration

    # Créer un embed pour la confirmation
    embed = discord.Embed(
        title="🧹 Mots-clés effacés",
        description=f"Tous les mots-clés ({keyword_count}) ont été supprimés.",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )

    embed.add_field(name="ℹ️ Information", value="Le filtrage est maintenant désactivé. Tous les articles RSS seront publiés.", inline=False)

    # Ajouter un pied de page
    embed.set_footer(text=f"Modifié par {ctx.author.display_name} • Utilisez !setkeywords pour réactiver le filtrage", 
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

    await ctx.send(embed=embed)
    logger.info(f"Tous les mots-clés ont été supprimés pour le serveur {guild_id}")

@bot.command(name="listkeywords")
async def list_keywords(ctx):
    """Affiche la liste des mots-clés configurés"""
    guild_id = str(ctx.guild.id)
    if guild_id not in server_keywords or not server_keywords[guild_id]:
        # Embed pour aucun mot-clé configuré
        embed = discord.Embed(
            title="🔍 Liste des mots-clés",
            description="⚠️ Aucun mot-clé n'est configuré pour ce serveur.",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="ℹ️ Information", value="Le filtrage est désactivé. Tous les articles RSS sont publiés.", inline=False)
        embed.add_field(name="💡 Conseil", value="Utilisez `!setkeywords mot1 mot2 ...` pour configurer des mots-clés.", inline=False)
        
        embed.set_footer(text=f"Demandé par {ctx.author.display_name}", 
                         icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
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

@bot.command(name="resetkeywords")
async def reset_keywords(ctx):
    """Réinitialise les mots-clés avec la liste par défaut"""
    guild_id = str(ctx.guild.id)
    server_keywords[guild_id] = DEFAULT_KEYWORDS.copy()
    save_config()  # Sauvegarder la configuration

    # Créer un embed pour la confirmation
    embed = discord.Embed(
        title="🔄 Mots-clés réinitialisés",
        description=f"Les mots-clés ont été réinitialisés avec la liste par défaut ({len(DEFAULT_KEYWORDS)} mots-clés).",
        color=discord.Color.purple(),
        timestamp=datetime.now()
    )

    # Ajouter quelques exemples de mots-clés
    examples = ", ".join(DEFAULT_KEYWORDS[:10])
    if len(DEFAULT_KEYWORDS) > 10:
        examples += f" et {len(DEFAULT_KEYWORDS) - 10} autres..."

    embed.add_field(name="📝 Exemples", value=examples, inline=False)
    embed.add_field(name="ℹ️ Information", value="Utilisez `!listkeywords` pour voir la liste complète.", inline=False)

    # Ajouter un pied de page
    embed.set_footer(text=f"Réinitialisé par {ctx.author.display_name}", 
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

    await ctx.send(embed=embed)
    logger.info(f"Mots-clés réinitialisés pour le serveur {guild_id}")

@bot.command(name="help")
async def help_command(ctx):
    """Affiche l'aide pour les commandes RSS"""
    embed = discord.Embed(
        title="📚 Guide du Bot RSS",
        description="Voici les commandes disponibles pour gérer vos flux RSS et le filtrage par mots-clés.",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )

    # Commandes de base
    embed.add_field(name="📡 Gestion des flux RSS", value="""
`!addrss #canal URL` - Ajoute un flux RSS à surveiller
`!removerss URL` - Supprime un flux RSS
`!listrss` - Liste tous les flux RSS configurés
`!testrss URL` - Teste un flux RSS
`!checkrss` - Force une vérification immédiate des flux RSS
""", inline=False)

    # Commandes de filtrage
    embed.add_field(name="🔍 Filtrage par mots-clés", value="""
`!setkeywords mot1 "phrase avec espaces" mot3` - Définit les mots-clés (remplace les existants)
`!addkeywords mot1 mot2` - Ajoute des mots-clés à la liste existante
`!removekeywords mot1 mot2` - Supprime des mots-clés spécifiques
`!clearkeywords` - Supprime tous les mots-clés (désactive le filtrage)
`!listkeywords` - Affiche la liste des mots-clés configurés
`!resetkeywords` - Réinitialise avec la liste de mots-clés par défaut
""", inline=False)

    # Exemples
    embed.add_field(name="💡 Exemples", value="""
`!addrss #actualités https://www.lemonde.fr/rss/une.xml`
`!setkeywords IA "intelligence artificielle" santé médecine`
`!testrss https://www.lemonde.fr/rss/une.xml`
`!checkrss` - Vérifie immédiatement tous les flux
""", inline=False)

    # Informations sur le filtrage
    embed.add_field(name="ℹ️ À propos du filtrage", value="""
Lorsque des mots-clés sont configurés, seuls les articles contenant au moins un de ces mots-clés seront publiés.
Le filtrage s'applique au titre, à la description et au contenu des articles.
Si aucun mot-clé n'est configuré, tous les articles seront publiés.
""", inline=False)

    # Informations sur la fréquence de vérification
    embed.add_field(name="⏱️ Fréquence de vérification", value="""
Le bot vérifie les flux RSS **toutes les 5 minutes** par défaut.
Utilisez `!checkrss` pour forcer une vérification immédiate.
""", inline=False)

    # Ajouter un pied de page
    embed.set_footer(text=f"Demandé par {ctx.author.display_name} • Bot RSS v2.0", 
                     icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

    await ctx.send(embed=embed)

# Commande pour forcer la vérification des flux RSS
@bot.command(name="checkrss")
@commands.has_permissions(manage_messages=True)  # Limite aux modérateurs
async def force_check_rss(ctx):
    """Force une vérification immédiate des flux RSS"""
    await ctx.send("⏳ Vérification forcée des flux RSS en cours...")
    
    # Créer une tâche asynchrone pour la vérification
    asyncio.create_task(check_rss_once(ctx))
    
    logger.info(f"Vérification forcée des flux RSS demandée par {ctx.author}")

# Fonction pour vérifier les flux RSS une seule fois
async def check_rss_once(ctx):
    """Vérifie les flux RSS une seule fois et envoie un rapport"""
    try:
        logger.info("Vérification forcée des flux RSS...")
        new_articles_count = 0
        checked_feeds = 0
        
        for guild_id, config in list(rss_configs.items()):
            channel = bot.get_channel(config["channel"])
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
                    
                    # Obtenir le titre du flux
                    feed_title = feed.feed.title if hasattr(feed.feed, 'title') else "Flux RSS"
                    
                    # Obtenir une couleur pour ce flux
                    color = get_color_for_url(rss_url)
                    
                    # Obtenir l'icône du flux
                    feed_icon = None
                    if hasattr(feed.feed, 'image') and hasattr(feed.feed.image, 'href'):
                        feed_icon = feed.feed.image.href
                    
                    # Envoyer les nouvelles entrées
                    for entry in reversed(new_entries):  # Envoyer dans l'ordre chronologique
                        try:
                            # Vérifier si l'article contient des mots-clés (si configurés)
                            if keywords and not contains_keywords(entry, keywords):
                                logger.info(f"Article filtré (ne contient pas de mots-clés): {entry.title}")
                                continue
                            
                            # Obtenir la date de publication
                            pub_date = parse_date(entry)
                            
                            # Obtenir la description/résumé
                            description = ""
                            if hasattr(entry, 'summary'):
                                description = clean_html(entry.summary)
                            elif hasattr(entry, 'description'):
                                description = clean_html(entry.description)
                            
                            # Limiter la longueur de la description
                            if len(description) > 300:
                                description = description[:300] + "..."
                            
                            # Créer un embed moderne pour l'article
                            embed = discord.Embed(
                                title=entry.title,
                                url=entry.link,
                                description=description,
                                color=color,
                                timestamp=pub_date
                            )
                            
                            # Ajouter l'auteur avec l'icône du flux
                            if feed_icon:
                                embed.set_author(name=feed_title, 
                                                url=feed.feed.link if hasattr(feed.feed, 'link') else None,
                                                icon_url=feed_icon)
                            else:
                                embed.set_author(name=feed_title, 
                                                url=feed.feed.link if hasattr(feed.feed, 'link') else None)
                            
                            # Ajouter l'image de l'article si disponible
                            image_url = None
                            
                            # Vérifier les médias
                            if hasattr(entry, 'media_content') and entry.media_content:
                                for media in entry.media_content:
                                    if 'url' in media and media['url'].endswith(('.jpg', '.jpeg', '.png', '.gif')):
                                        image_url = media['url']
                                        break
                            
                            # Vérifier les enclosures
                            if not image_url and hasattr(entry, 'enclosures') and entry.enclosures:
                                for enclosure in entry.enclosures:
                                    if 'type' in enclosure and enclosure['type'].startswith('image/'):
                                        image_url = enclosure['href']
                                        break
                            
                            # Vérifier les liens
                            if not image_url and hasattr(entry, 'links'):
                                for link in entry.links:
                                    if 'type' in link and link['type'].startswith('image/'):
                                        image_url = link['href']
                                        break
                            
                            if image_url:
                                embed.set_image(url=image_url)
                            
                            # Ajouter l'auteur si disponible
                            if hasattr(entry, 'author'):
                                embed.add_field(name="✍️ Auteur", value=entry.author, inline=True)
                            
                            # Ajouter les catégories si disponibles
                            if hasattr(entry, 'tags'):
                                categories = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
                                if categories:
                                    embed.add_field(name="🏷️ Catégories", value=", ".join(categories[:5]) + 
                                                  ("..." if len(categories) > 5 else ""), inline=True)
                            
                            # Ajouter un pied de page
                            formatted_date = pub_date.strftime(DATE_FORMAT)
                            embed.set_footer(text=f"Publié le {formatted_date}")
                            
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
        embed = discord.Embed(
            title="✅ Vérification RSS terminée",
            description=f"Vérification forcée des flux RSS terminée.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="📊 Résultats", value=f"""
• Flux vérifiés: **{checked_feeds}**
• Nouveaux articles publiés: **{new_articles_count}**
        """, inline=False)
        
        embed.set_footer(text=f"Demandé par {ctx.author.display_name}", 
                         icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
        logger.info(f"Vérification forcée terminée. {new_articles_count} nouveaux articles publiés.")

    except Exception as e:
        logger.error(f"Erreur dans la vérification forcée: {e}")
        await ctx.send(f"❌ Erreur lors de la vérification forcée: {str(e)}")

# ===== COMMANDES SLASH (/) =====
# Ces commandes sont définies mais ne seront utilisées que si elles fonctionnent

# Commande slash pour ajouter un flux RSS
@bot.tree.command(name="addrss", description="Ajoute un flux RSS à surveiller")
@app_commands.describe(
    channel="Le canal où les articles seront publiés",
    rss_url="L'URL du flux RSS à surveiller"
)
async def slash_add_rss(interaction: discord.Interaction, channel: discord.TextChannel, rss_url: str):
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
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout du flux RSS: {e}")
        await interaction.followup.send(f"Erreur: {str(e)}")

# Commande slash pour l'aide
@bot.tree.command(name="help", description="Affiche l'aide pour les commandes RSS")
async def slash_help(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    
    embed = discord.Embed(
        title="📚 Guide du Bot RSS",
        description="Voici les commandes disponibles pour gérer vos flux RSS et le filtrage par mots-clés.",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # Commandes de base
    embed.add_field(name="📡 Gestion des flux RSS", value="""
`!addrss #canal URL` - Ajoute un flux RSS à surveiller
`!removerss URL` - Supprime un flux RSS
`!listrss` - Liste tous les flux RSS configurés
`!testrss URL` - Teste un flux RSS
`!checkrss` - Force une vérification immédiate des flux RSS
""", inline=False)
    
    # Commandes de filtrage
    embed.add_field(name="🔍 Filtrage par mots-clés", value="""
`!setkeywords mot1 "phrase avec espaces" mot3` - Définit les mots-clés (remplace les existants)
`!addkeywords mot1 mot2` - Ajoute des mots-clés à la liste existante
`!removekeywords mot1 mot2` - Supprime des mots-clés spécifiques
`!clearkeywords` - Supprime tous les mots-clés (désactive le filtrage)
`!listkeywords` - Affiche la liste des mots-clés configurés
`!resetkeywords` - Réinitialise avec la liste de mots-clés par défaut
""", inline=False)
    
    # Informations sur le filtrage
    embed.add_field(name="ℹ️ À propos du filtrage", value="""
Lorsque des mots-clés sont configurés, seuls les articles contenant au moins un de ces mots-clés seront publiés.
Le filtrage s'applique au titre, à la description et au contenu des articles.
Si aucun mot-clé n'est configuré, tous les articles seront publiés.
""", inline=False)
    
    # Informations sur la fréquence de vérification
    embed.add_field(name="⏱️ Fréquence de vérification", value="""
Le bot vérifie les flux RSS **toutes les 5 minutes** par défaut.
Utilisez `!checkrss` pour forcer une vérification immédiate.
""", inline=False)
    
    # Ajouter un pied de page
    embed.set_footer(text=f"Demandé par {interaction.user.display_name} • Bot RSS v2.0", 
                     icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    
    await interaction.followup.send(embed=embed)

# Commande slash pour forcer la vérification des flux RSS
@bot.tree.command(name="checkrss", description="Force une vérification immédiate des flux RSS")
async def slash_force_check_rss(interaction: discord.Interaction):
    # Vérifier les permissions
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ Vous n'avez pas les permissions nécessaires pour utiliser cette commande.", ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ Vérification forcée des flux RSS en cours...")
    
    # Créer un contexte simulé pour la fonction check_rss_once
    class SimulatedContext:
        def __init__(self, interaction):
            self.author = interaction.user
            self.send = interaction.followup.send
    
    # Créer une tâche asynchrone pour la vérification
    asyncio.create_task(check_rss_once(SimulatedContext(interaction)))
    
    logger.info(f"Vérification forcée des flux RSS demandée par {interaction.user}")

@tasks.loop(minutes=5)
async def check_rss():
    """Vérifie périodiquement les flux RSS pour de nouveaux articles"""
    try:
        logger.info("Vérification des flux RSS...")
        
        for guild_id, config in list(rss_configs.items()):
            channel = bot.get_channel(config["channel"])
            if not channel:
                logger.warning(f"Channel introuvable pour guild {guild_id}")
                continue

            # Obtenir les mots-clés pour ce serveur
            keywords = server_keywords.get(guild_id, [])
            
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
                    
                    # Obtenir le titre du flux
                    feed_title = feed.feed.title if hasattr(feed.feed, 'title') else "Flux RSS"
                    
                    # Obtenir une couleur pour ce flux
                    color = get_color_for_url(rss_url)
                    
                    # Obtenir l'icône du flux
                    feed_icon = None
                    if hasattr(feed.feed, 'image') and hasattr(feed.feed.image, 'href'):
                        feed_icon = feed.feed.image.href
                    
                    # Envoyer les nouvelles entrées
                    for entry in reversed(new_entries):  # Envoyer dans l'ordre chronologique
                        try:
                            # Vérifier si l'article contient des mots-clés (si configurés)
                            if keywords and not contains_keywords(entry, keywords):
                                logger.info(f"Article filtré (ne contient pas de mots-clés): {entry.title}")
                                continue
                            
                            # Obtenir la date de publication
                            pub_date = parse_date(entry)
                            
                            # Obtenir la description/résumé
                            description = ""
                            if hasattr(entry, 'summary'):
                                description = clean_html(entry.summary)
                            elif hasattr(entry, 'description'):
                                description = clean_html(entry.description)
                            
                            # Limiter la longueur de la description
                            if len(description) > 300:
                                description = description[:300] + "..."
                            
                            # Créer un embed moderne pour l'article
                            embed = discord.Embed(
                                title=entry.title,
                                url=entry.link,
                                description=description,
                                color=color,
                                timestamp=pub_date
                            )
                            
                            # Ajouter l'auteur avec l'icône du flux
                            if feed_icon:
                                embed.set_author(name=feed_title, 
                                                url=feed.feed.link if hasattr(feed.feed, 'link') else None,
                                                icon_url=feed_icon)
                            else:
                                embed.set_author(name=feed_title, 
                                                url=feed.feed.link if hasattr(feed.feed, 'link') else None)
                            
                            # Ajouter l'image de l'article si disponible
                            image_url = None
                            
                            # Vérifier les médias
                            if hasattr(entry, 'media_content') and entry.media_content:
                                for media in entry.media_content:
                                    if 'url' in media and media['url'].endswith(('.jpg', '.jpeg', '.png', '.gif')):
                                        image_url = media['url']
                                        break
                            
                            # Vérifier les enclosures
                            if not image_url and hasattr(entry, 'enclosures') and entry.enclosures:
                                for enclosure in entry.enclosures:
                                    if 'type' in enclosure and enclosure['type'].startswith('image/'):
                                        image_url = enclosure['href']
                                        break
                            
                            # Vérifier les liens
                            if not image_url and hasattr(entry, 'links'):
                                for link in entry.links:
                                    if 'type' in link and link['type'].startswith('image/'):
                                        image_url = link['href']
                                        break
                            
                            if image_url:
                                embed.set_image(url=image_url)
                            
                            # Ajouter l'auteur si disponible
                            if hasattr(entry, 'author'):
                                embed.add_field(name="✍️ Auteur", value=entry.author, inline=True)
                            
                            # Ajouter les catégories si disponibles
                            if hasattr(entry, 'tags'):
                                categories = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
                                if categories:
                                    embed.add_field(name="🏷️ Catégories", value=", ".join(categories[:5]) + 
                                                  ("..." if len(categories) > 5 else ""), inline=True)
                            
                            # Ajouter un pied de page
                            formatted_date = pub_date.strftime(DATE_FORMAT)
                            embed.set_footer(text=f"Publié le {formatted_date}")
                            
                            await channel.send(embed=embed)
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
                await asyncio.sleep(2)

        logger.info("Cycle de vérification terminé")

    except Exception as e:
        logger.error(f"Erreur dans check_rss: {e}")

@check_rss.before_loop
async def before_check_rss():
    """Attend que le bot soit prêt avant de démarrer la tâche"""
    await bot.wait_until_ready()

# Remplacez par votre token
TOKEN = "MTM0NjQ5MjgxMDA5Nzg1MjQ3OA.Gux0S5.hajy49Ip9Q3hV_9bPXzCHSLCm_RRzeNY_bN0XI"  # Remplacez par votre vrai token

# Démarrer le bot
if __name__ == "__main__":
    bot.run(TOKEN)