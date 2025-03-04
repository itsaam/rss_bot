import discord
from discord.ext import commands, tasks
import logging
import asyncio
import random
import os
from config import TOKEN, PREFIX, ACTIVITY_CHANGE_INTERVAL
from utils.storage import load_config, rss_configs

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration du bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Désactiver la commande help par défaut
bot.remove_command('help')

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
    
    # Démarrer les tâches
    check_rss.start()
    change_activity.start()
    
    # Définir l'activité initiale
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help pour l'aide"))

@tasks.loop(minutes=ACTIVITY_CHANGE_INTERVAL)
async def change_activity():
    """Change l'activité du bot périodiquement"""
    activities = [
        discord.Activity(type=discord.ActivityType.watching, name="les flux RSS"),
        discord.Activity(type=discord.ActivityType.listening, name="les nouvelles"),
        discord.Game(name=f"{PREFIX}help pour l'aide"),
        discord.Activity(type=discord.ActivityType.watching, name=f"{len(rss_configs)} serveurs"),
        discord.Game(name="Surveiller l'actualité"),
        discord.Activity(type=discord.ActivityType.listening, name=f"{PREFIX}checkrss")
    ]
    
    activity = random.choice(activities)
    await bot.change_presence(activity=activity)
    logger.info(f"Activité changée: {activity.name}")

@tasks.loop(minutes=5)
async def check_rss():
    """Vérifie périodiquement les flux RSS pour de nouveaux articles"""
    from cogs.rss_commands import check_rss_feeds
    await check_rss_feeds(bot)

@check_rss.before_loop
async def before_check_rss():
    """Attend que le bot soit prêt avant de démarrer la tâche"""
    await bot.wait_until_ready()

# Charger les extensions (cogs)
async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            logger.info(f"Extension chargée: {filename[:-3]}")

# Démarrer le bot
async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())