import json
import os
import logging
from config import CONFIG_FILE

logger = logging.getLogger(__name__)

# Stockage des configurations RSS
rss_configs = {}
# Dictionnaire pour stocker les mots-clés par serveur
server_keywords = {}

def save_config():
    """Sauvegarde les configurations dans un fichier JSON"""
    config_data = {
        "rss_configs": rss_configs,
        "server_keywords": server_keywords
    }
    
    # Créer le dossier data s'il n'existe pas
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

def load_config():
    """Charge les configurations depuis un fichier JSON"""
    global rss_configs, server_keywords

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                rss_configs = config_data.get("rss_configs", {})
                server_keywords = config_data.get("server_keywords", {})
            logger.info(f"Configuration chargée: {len(rss_configs)} serveurs configurés")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
    else:
        logger.info("Aucun fichier de configuration trouvé. Utilisation des valeurs par défaut.")