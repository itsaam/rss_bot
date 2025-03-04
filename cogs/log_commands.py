import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from utils.storage import log_channels, save_config
from utils.embed_builder import create_confirmation_embed

logger = logging.getLogger(__name__)

class LogCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setlogchannel")
    @commands.has_permissions(administrator=True)  # Limite aux administrateurs
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """Configure le canal pour les logs du bot"""
        guild_id = str(ctx.guild.id)
        
        if channel is None:
            # Si aucun canal n'est spécifié, utiliser le canal actuel
            channel = ctx.channel
        
        log_channels[guild_id] = channel.id
        save_config()
        
        embed = create_confirmation_embed(
            title="✅ Canal de logs configuré",
            description=f"Les logs du bot seront envoyés dans {channel.mention}.",
            color=discord.Color.green(),
            author=ctx.author
        )
        
        await ctx.send(embed=embed)
        logger.info(f"Canal de logs configuré pour le serveur {guild_id}: {channel.id}")
        
        # Envoyer un message de test dans le canal de logs
        test_embed = discord.Embed(
            title="📝 Configuration des logs",
            description="Ce canal a été configuré pour recevoir les logs du bot RSS.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        test_embed.add_field(name="ℹ️ Information", value="Vous recevrez des notifications pour :\n• Ajout/suppression de flux RSS\n• Vérifications périodiques\n• Nouveaux articles publiés\n• Erreurs éventuelles", inline=False)
        test_embed.set_footer(text=f"Configuré par {ctx.author.display_name}", 
                             icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await channel.send(embed=test_embed)

    @commands.command(name="removelogchannel")
    @commands.has_permissions(administrator=True)  # Limite aux administrateurs
    async def remove_log_channel(self, ctx):
        """Désactive les logs du bot"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in log_channels:
            await ctx.send("Aucun canal de logs n'est configuré pour ce serveur.")
            return
        
        del log_channels[guild_id]
        save_config()
        
        embed = create_confirmation_embed(
            title="🚫 Logs désactivés",
            description="Les logs du bot ont été désactivés pour ce serveur.",
            color=discord.Color.red(),
            author=ctx.author
        )
        
        await ctx.send(embed=embed)
        logger.info(f"Canal de logs supprimé pour le serveur {guild_id}")

    # Commandes slash
    @app_commands.command(name="setlogchannel", description="Configure le canal pour les logs du bot")
    @app_commands.describe(channel="Le canal où les logs seront envoyés")
    async def slash_set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        # Vérifier les permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Vous n'avez pas les permissions nécessaires pour utiliser cette commande.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        guild_id = str(interaction.guild_id)
        
        if channel is None:
            # Si aucun canal n'est spécifié, utiliser le canal actuel
            channel = interaction.channel
        
        log_channels[guild_id] = channel.id
        save_config()
        
        embed = create_confirmation_embed(
            title="✅ Canal de logs configuré",
            description=f"Les logs du bot seront envoyés dans {channel.mention}.",
            color=discord.Color.green(),
            author=interaction.user
        )
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Canal de logs configuré pour le serveur {guild_id}: {channel.id}")
        
        # Envoyer un message de test dans le canal de logs
        test_embed = discord.Embed(
            title="📝 Configuration des logs",
            description="Ce canal a été configuré pour recevoir les logs du bot RSS.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        test_embed.add_field(name="ℹ️ Information", value="Vous recevrez des notifications pour :\n• Ajout/suppression de flux RSS\n• Vérifications périodiques\n• Nouveaux articles publiés\n• Erreurs éventuelles", inline=False)
        test_embed.set_footer(text=f"Configuré par {interaction.user.display_name}", 
                             icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        
        await channel.send(embed=test_embed)

async def setup(bot):
    await bot.add_cog(LogCommands(bot))