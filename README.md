# 📰 RSS Bot pour Discord

Un bot Discord développé en Python permettant de récupérer automatiquement les flux RSS et de publier les nouvelles entrées dans des salons Discord. Léger, rapide et entièrement personnalisable, il est idéal pour automatiser la veille sur votre serveur.

## 🚀 Fonctionnalités

- 📡 Récupère plusieurs flux RSS en parallèle
- 🕒 Publication automatique à intervalles réguliers
- 🧹 Nettoyage du contenu via BeautifulSoup
- 🔄 Détection intelligente des nouveaux articles
- 📌 Personnalisation des salons Discord de destination
- 📋 Logs détaillés des événements

## 🧰 Technologies utilisées

- **Langage** : Python 3
- **Librairies** :
  - `discord.py` – pour l’interaction avec l’API Discord
  - `feedparser` – pour lire les flux RSS
  - `beautifulsoup4` – pour nettoyer le HTML dans les descriptions
  - `asyncio`, `logging`, `datetime`, `hashlib` – pour la logique interne

## 📦 Installation

```bash
git clone https://github.com/itsaam/rss_bot.git
cd rss_bot
pip install -r requirements.txt
