import discord
from datetime import datetime
from config import DATE_FORMAT
from utils.rss_parser import get_color_for_url, get_feed_image, get_entry_image, get_entry_categories, parse_date, clean_html

def create_article_embed(entry, feed, rss_url):
    """Crée un embed pour un article RSS"""
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
    feed_icon = get_feed_image(feed.feed)
    if feed_icon:
        embed.set_author(name=feed_title, 
                        url=feed.feed.link if hasattr(feed.feed, 'link') else None,
                        icon_url=feed_icon)
    else:
        embed.set_author(name=feed_title, 
                        url=feed.feed.link if hasattr(feed.feed, 'link') else None)
    
    # Ajouter l'image de l'article si disponible
    image_url = get_entry_image(entry)
    if image_url:
        embed.set_image(url=image_url)
    
    # Ajouter l'auteur si disponible
    if hasattr(entry, 'author'):
        embed.add_field(name="✍️ Auteur", value=entry.author, inline=True)
    
    # Ajouter les catégories si disponibles
    categories = get_entry_categories(entry)
    if categories:
        embed.add_field(name="🏷️ Catégories", value=", ".join(categories[:5]) + 
                      ("..." if len(categories) > 5 else ""), inline=True)
    
    # Ajouter un pied de page
    formatted_date = pub_date.strftime(DATE_FORMAT)
    embed.set_footer(text=f"Publié le {formatted_date}")
    
    return embed

def create_confirmation_embed(title, description, color, author=None, timestamp=None):
    """Crée un embed de confirmation"""
    if timestamp is None:
        timestamp = datetime.now()
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=timestamp
    )
    
    if author:
        embed.set_footer(text=f"Action par {author.display_name}", 
                         icon_url=author.avatar.url if author.avatar else None)
    
    return embed