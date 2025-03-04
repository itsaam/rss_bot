import discord
import logging
from datetime import datetime
from utils.storage import log_channels

logger = logging.getLogger(__name__)

async def send_log(bot, guild_id, message, color=discord.Color.blue(), title=None):
    """Envoie un message de log dans le canal configuré"""
    try:
        guild_id_str = str(guild_id)
        
        if guild_id_str not in log_channels:
            logger.debug(f"Pas de canal de logs configuré pour le serveur {guild_id}")
            return False
        
        channel_id = log_channels[guild_id_str]
        channel = bot.get_channel(channel_id)
        
        if not channel:
            logger.warning(f"Canal de logs introuvable pour le serveur {guild_id} (ID: {channel_id})")
            return False
        
        embed = discord.Embed(
            description=message,
            color=color,
            timestamp=datetime.now()
        )
        
        if title:
            embed.title = title
            
        embed.set_footer(text=f"Bot RSS • Log")
        
        await channel.send(embed=embed)
        logger.debug(f"Log envoyé au canal {channel_id} pour le serveur {guild_id}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du log: {e}")
        return False