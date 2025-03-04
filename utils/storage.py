import os
import json
import logging

logger = logging.getLogger(__name__)

# Définir le chemin du fichier de configuration
CONFIG_FILE = os.path.join("data", "config.json")

# Variables globales
rss_configs = {}  # Dictionnaire pour stocker les configurations RSS
server_keywords = {}  # Dictionnaire pour stocker les mots-clés par serveur
log_channels = {}  # Dictionnaire pour stocker les canaux de logs

def save_config():
    """Sauvegarde les configurations dans un fichier JSON"""
    config_data = {
        "rss_configs": rss_configs,
        "server_keywords": server_keywords,
        "log_channels": log_channels
    }
    
    # Créer le dossier data s'il n'existe pas
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)
    
    logger.debug(f"Configuration sauvegardée: {len(rss_configs)} serveurs, {len(log_channels)} canaux de logs")

def load_config():
    """Charge les configurations depuis un fichier JSON"""
    global rss_configs, server_keywords, log_channels

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                rss_configs = config_data.get("rss_configs", {})
                server_keywords = config_data.get("server_keywords", {})
                log_channels = config_data.get("log_channels", {})
            logger.info(f"Configuration chargée: {len(rss_configs)} serveurs, {len(log_channels)} canaux de logs")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
    else:
        logger.info("Aucun fichier de configuration trouvé. Utilisation des valeurs par défaut.")

# Charger la configuration au démarrage
load_config()