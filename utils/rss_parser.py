import feedparser
from datetime import datetime
import hashlib
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
import logging

logger = logging.getLogger(__name__)

def get_color_for_url(url):
    """Génère une couleur basée sur l'URL du flux"""
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

def parse_date(entry):
    """Parse la date d'un article RSS"""
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

def clean_html(html_text):
    """Nettoie le HTML"""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, 'html.parser')
    return soup.get_text(separator=' ', strip=True)

def contains_keywords(entry, keywords):
    """Vérifie si un article contient des mots-clés"""
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

def get_feed_image(feed):
    """Récupère l'image du flux"""
    if hasattr(feed, 'image') and hasattr(feed.image, 'href'):
        return feed.image.href
    return None

def get_entry_image(entry):
    """Récupère l'image d'un article"""
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
    
    return image_url

def get_entry_categories(entry):
    """Récupère les catégories d'un article"""
    if hasattr(entry, 'tags'):
        return [tag.term for tag in entry.tags if hasattr(tag, 'term')]
    return []