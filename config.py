# Configuration du bot
TOKEN = ""  # Remplacez par votre vrai token
PREFIX = "!"
DATE_FORMAT = "%d %b %Y %H:%M:%S"
CONFIG_FILE = "data/rss_config.json"
ACTIVITY_CHANGE_INTERVAL = 10  # minutes
# Configuration pour les logs
LOG_CHANNELS = {}  # Format: {"guild_id": channel_id}
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