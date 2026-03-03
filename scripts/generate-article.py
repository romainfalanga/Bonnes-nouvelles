#!/usr/bin/env python3
"""
Script de génération automatique d'articles pour Bonnes Nouvelles.
Utilise l'API Anthropic (Claude) pour rechercher et rédiger des articles
sur les bonnes nouvelles du monde.

Thèmes par jour :
  - Lundi : Intelligence Artificielle
  - Mardi : Technologie
  - Mercredi : Écologie
  - Jeudi : Innovation
  - Vendredi : Idées Incroyables
"""

import os
import sys
import json
import datetime
import re
import anthropic

# Configuration des thèmes par jour de la semaine (0=lundi, 4=vendredi)
THEMES = {
    0: {
        "name": "Intelligence Artificielle",
        "slug": "intelligence-artificielle",
        "emoji": "🤖",
        "search_terms": "bonnes nouvelles intelligence artificielle IA",
        "description": "Les avancées positives dans le monde de l'IA",
    },
    1: {
        "name": "Technologie",
        "slug": "technologie",
        "emoji": "💻",
        "search_terms": "bonnes nouvelles technologie innovation tech",
        "description": "Les bonnes nouvelles du monde de la technologie",
    },
    2: {
        "name": "Écologie",
        "slug": "ecologie",
        "emoji": "🌿",
        "search_terms": "bonnes nouvelles écologie environnement climat",
        "description": "Les avancées positives pour notre planète",
    },
    3: {
        "name": "Innovation",
        "slug": "innovation",
        "emoji": "💡",
        "search_terms": "innovation découverte scientifique breakthrough",
        "description": "Les innovations qui changent le monde",
    },
    4: {
        "name": "Idées Incroyables",
        "slug": "idees-incroyables",
        "emoji": "✨",
        "search_terms": "idées incroyables inventions inspirantes solutions créatives",
        "description": "Les idées les plus inspirantes de la semaine",
    },
}


def get_today_theme():
    """Retourne le thème du jour basé sur le jour de la semaine."""
    today = datetime.date.today()
    weekday = today.weekday()  # 0=lundi, 6=dimanche

    if weekday > 4:  # Week-end
        print("Pas de publication le week-end.")
        sys.exit(0)

    return today, THEMES[weekday]


def generate_article(today, theme):
    """Génère un article en utilisant Claude avec recherche web."""
    client = anthropic.Anthropic()

    date_str = today.strftime("%Y-%m-%d")
    date_from = (today - datetime.timedelta(days=7)).strftime("%d/%m/%Y")
    date_to = today.strftime("%d/%m/%Y")

    prompt = f"""Tu es un journaliste optimiste pour le blog "Bonnes Nouvelles".
Ta mission : écrire un article en français sur les BONNES NOUVELLES dans le domaine "{theme['name']}" de la semaine du {date_from} au {date_to}.

INSTRUCTIONS :
1. Recherche les actualités positives récentes (derniers 7 jours) dans le domaine "{theme['name']}" en utilisant les termes : {theme['search_terms']}
2. Sélectionne les 3 à 5 nouvelles les plus marquantes et positives
3. Rédige un article structuré, engageant et optimiste en français

FORMAT DE L'ARTICLE (en Markdown) :
- Commence directement par une introduction engageante (2-3 phrases)
- Pour chaque bonne nouvelle, crée une section avec un titre ## accrocheur
- Chaque section fait 2-3 paragraphes avec des détails concrets
- Termine par une conclusion optimiste sur les tendances positives
- Ton : enthousiaste mais factuel, accessible à tous
- Longueur : 800-1200 mots environ

IMPORTANT :
- Ne commence PAS par le titre de l'article (il sera dans les métadonnées)
- Utilise des faits vérifiables et cite les sources quand possible
- Garde un ton positif et inspirant
- Écris en français courant, pas trop formel

Réponds UNIQUEMENT avec le contenu Markdown de l'article, rien d'autre."""

    # Use Claude with web search via tool use
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def generate_title(theme, article_content):
    """Génère un titre accrocheur pour l'article."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": f"""Génère UN titre court et accrocheur (max 80 caractères) pour cet article de blog sur les bonnes nouvelles en {theme['name']}.
Le titre doit être optimiste et donner envie de lire.
Ne mets PAS de guillemets autour du titre.

Début de l'article :
{article_content[:500]}

Réponds UNIQUEMENT avec le titre, rien d'autre.""",
            }
        ],
    )

    return response.content[0].text.strip().strip('"').strip("«").strip("»").strip()


def generate_summary(article_content):
    """Génère un résumé court pour la carte de l'article."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": f"""Génère un résumé de 1-2 phrases (max 160 caractères) pour cet article.
Le résumé doit donner envie de lire l'article complet.

Article :
{article_content[:1000]}

Réponds UNIQUEMENT avec le résumé, rien d'autre.""",
            }
        ],
    )

    return response.content[0].text.strip()


def extract_tags(theme, article_content):
    """Extrait des tags pertinents de l'article."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": f"""Génère 3-5 tags pertinents pour cet article sur {theme['name']}.
Format : une liste de mots séparés par des virgules, en minuscules, sans #.
Exemple : intelligence artificielle, santé, recherche

Article :
{article_content[:800]}

Réponds UNIQUEMENT avec les tags séparés par des virgules.""",
            }
        ],
    )

    tags = [tag.strip() for tag in response.content[0].text.strip().split(",")]
    return tags


def create_markdown_file(today, theme, title, summary, tags, content):
    """Crée le fichier Markdown avec les métadonnées Hugo."""
    date_str = today.strftime("%Y-%m-%d")
    weekday_names = {
        0: "lundi",
        1: "mardi",
        2: "mercredi",
        3: "jeudi",
        4: "vendredi",
    }
    day_name = weekday_names[today.weekday()]

    # Slug pour le nom de fichier
    slug = f"{date_str}-{day_name}-{theme['slug']}"

    # Métadonnées Hugo (front matter)
    tags_str = json.dumps(tags, ensure_ascii=False)
    front_matter = f"""---
title: "{title}"
date: {date_str}T12:00:00+01:00
draft: false
categories: ["{theme['name']}"]
tags: {tags_str}
emoji: "{theme['emoji']}"
summary: "{summary}"
---

"""

    filepath = f"content/posts/{slug}.md"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front_matter + content)

    return filepath


def main():
    # Vérifier la clé API
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Erreur : ANTHROPIC_API_KEY non définie.")
        sys.exit(1)

    # Obtenir le thème du jour
    today, theme = get_today_theme()
    print(f"📰 Génération de l'article du jour : {theme['emoji']} {theme['name']}")
    print(f"📅 Date : {today.strftime('%A %d %B %Y')}")

    # Générer l'article
    print("✍️  Rédaction de l'article en cours...")
    content = generate_article(today, theme)

    # Générer le titre
    print("📝 Génération du titre...")
    title = generate_title(theme, content)

    # Générer le résumé
    print("📋 Génération du résumé...")
    summary = generate_summary(content)

    # Extraire les tags
    print("🏷️  Extraction des tags...")
    tags = extract_tags(theme, content)

    # Créer le fichier
    filepath = create_markdown_file(today, theme, title, summary, tags, content)
    print(f"✅ Article créé : {filepath}")
    print(f"   Titre : {title}")
    print(f"   Catégorie : {theme['name']}")
    print(f"   Tags : {', '.join(tags)}")

    return filepath


if __name__ == "__main__":
    main()
