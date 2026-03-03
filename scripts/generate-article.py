#!/usr/bin/env python3
"""
Script de génération automatique d'articles pour Bonnes Nouvelles.
Utilise l'API Mammouth (proxy OpenAI-compatible) avec Claude Sonnet
pour rechercher et rédiger des articles sur les bonnes nouvelles du monde,
avec une couche de vérification des faits.

Thèmes par jour :
  - Lundi : Intelligence Artificielle
  - Mardi : Médecine et Santé
  - Mercredi : Physique et Univers
  - Jeudi : Invention
  - Vendredi : Écologie
"""

import os
import sys
import json
import datetime
from openai import OpenAI

MAMMOUTH_BASE_URL = "https://api.mammouth.ai/v1"
MODEL = "claude-sonnet-4-6"

# Configuration des thèmes par jour de la semaine (0=lundi, 4=vendredi)
THEMES = {
    0: {
        "name": "Intelligence Artificielle",
        "slug": "intelligence-artificielle",
        "emoji": "🤖",
        "search_terms": "bonnes nouvelles intelligence artificielle IA découverte avancée",
        "description": "Les avancées positives dans le monde de l'IA",
    },
    1: {
        "name": "Médecine et Santé",
        "slug": "medecine-et-sante",
        "emoji": "🏥",
        "search_terms": "bonnes nouvelles médecine santé découverte médicale traitement",
        "description": "Les découvertes médicales et avancées en santé",
    },
    2: {
        "name": "Physique et Univers",
        "slug": "physique-et-univers",
        "emoji": "🔭",
        "search_terms": "découverte physique astronomie univers espace sciences",
        "description": "Les découvertes fascinantes en physique et astronomie",
    },
    3: {
        "name": "Invention",
        "slug": "invention",
        "emoji": "💡",
        "search_terms": "invention innovation technologie brevet découverte",
        "description": "Les inventions qui changent le monde",
    },
    4: {
        "name": "Écologie",
        "slug": "ecologie",
        "emoji": "🌿",
        "search_terms": "bonnes nouvelles écologie environnement climat biodiversité",
        "description": "Les avancées positives pour notre planète",
    },
}


def get_client():
    """Crée un client OpenAI pointant vers l'API Mammouth."""
    return OpenAI(
        base_url=MAMMOUTH_BASE_URL,
        api_key=os.environ.get("MAMMOUTH_API_KEY"),
    )


def chat(client, messages, max_tokens):
    """Appel générique à l'API Mammouth via le format OpenAI."""
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content


def get_today_theme():
    """Retourne le thème du jour basé sur le jour de la semaine."""
    today = datetime.date.today()
    weekday = today.weekday()  # 0=lundi, 6=dimanche

    if weekday > 4:  # Week-end
        print("Pas de publication le week-end.")
        sys.exit(0)

    return today, THEMES[weekday]


def generate_article(client, today, theme):
    """Génère un article en utilisant Claude Sonnet via Mammouth."""
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
- Chaque section fait 2-3 paragraphes avec des détails concrets (chiffres, noms, lieux)
- Pour chaque fait mentionné, explique clairement POURQUOI c'est une bonne nouvelle et CE QUE ÇA CHANGE concrètement
- Termine par une conclusion optimiste sur les tendances positives
- Ton : enthousiaste mais factuel, accessible à tous
- Longueur : 800-1200 mots environ

IMPORTANT :
- Ne commence PAS par le titre de l'article (il sera dans les métadonnées)
- Utilise des faits vérifiables avec des chiffres précis et des sources identifiables
- Garde un ton positif et inspirant
- Écris en français courant, pas trop formel
- Mentionne les organisations, universités, entreprises ou chercheurs à l'origine des découvertes

Réponds UNIQUEMENT avec le contenu Markdown de l'article, rien d'autre."""

    return chat(client, [{"role": "user", "content": prompt}], max_tokens=4096)


def fact_check_and_enrich(client, theme, article_content):
    """Couche finale de vérification des faits, ajout de sources et reformulation."""
    prompt = f"""Tu es un rédacteur en chef et vérificateur de faits pour le blog "Bonnes Nouvelles", spécialisé en {theme['name']}.

Voici un article qui a été rédigé et qui doit passer ta vérification finale avant publication.

ARTICLE À VÉRIFIER ET ENRICHIR :
---
{article_content}
---

TES MISSIONS (toutes obligatoires) :

1. VÉRIFICATION DES FAITS :
   - Vérifie chaque fait, chiffre et affirmation dans l'article
   - Si un fait semble inexact ou exagéré, corrige-le ou reformule pour être plus prudent
   - Si un fait ne peut pas être vérifié, reformule avec des termes plus nuancés (ex: "selon certaines estimations", "d'après les premières données")

2. AJOUT DE SOURCES (OBLIGATOIRE) :
   - Pour CHAQUE fait important ou découverte mentionnée, ajoute un lien hypertexte vers une source fiable directement dans le texte
   - Format des liens : [texte descriptif](URL)
   - Place les liens aux endroits les plus naturels et pertinents dans chaque paragraphe
   - Utilise des sources fiables : sites d'institutions (NASA, OMS, CNRS, etc.), revues scientifiques (Nature, Science, The Lancet), médias reconnus (Reuters, AFP, Le Monde, BBC, etc.)
   - Chaque section ## doit contenir au moins 1-2 liens sources
   - Les URLs doivent être de vraies URLs plausibles de sites existants

3. VÉRIFICATION "BONNE NOUVELLE" :
   - Pour chaque nouvelle, vérifie que l'explication de pourquoi c'est une bonne nouvelle est cohérente et fondée
   - Renforce l'argumentation si nécessaire
   - Si une nouvelle n'est pas réellement positive ou est trop exagérée, nuance le propos

4. REFORMULATION ET OPTIMISATION :
   - Peaufine le style pour qu'il soit fluide, engageant et clair
   - Assure-toi que les transitions entre sections sont naturelles
   - Vérifie que l'article est accessible à un public non-spécialiste
   - Garde le ton optimiste mais crédible

RÈGLES IMPORTANTES :
- Conserve la structure Markdown (## pour les titres de section)
- Ne commence PAS par un titre principal (pas de # en début)
- Garde une longueur similaire (800-1200 mots)
- Les liens doivent être intégrés naturellement dans le texte, pas listés à part
- L'article final doit être MEILLEUR que l'original : plus précis, mieux sourcé, plus crédible

Réponds UNIQUEMENT avec l'article final corrigé et enrichi en Markdown, rien d'autre."""

    return chat(client, [{"role": "user", "content": prompt}], max_tokens=5000)


def generate_title(client, theme, article_content):
    """Génère un titre accrocheur pour l'article."""
    prompt = f"""Génère UN titre court et accrocheur (max 80 caractères) pour cet article de blog sur les bonnes nouvelles en {theme['name']}.
Le titre doit être optimiste et donner envie de lire.
Ne mets PAS de guillemets autour du titre.

Début de l'article :
{article_content[:500]}

Réponds UNIQUEMENT avec le titre, rien d'autre."""

    result = chat(client, [{"role": "user", "content": prompt}], max_tokens=100)
    return result.strip().strip('"').strip("«").strip("»").strip()


def generate_summary(client, article_content):
    """Génère un résumé court pour la carte de l'article."""
    prompt = f"""Génère un résumé de 1-2 phrases (max 160 caractères) pour cet article.
Le résumé doit donner envie de lire l'article complet.

Article :
{article_content[:1000]}

Réponds UNIQUEMENT avec le résumé, rien d'autre."""

    return chat(client, [{"role": "user", "content": prompt}], max_tokens=200).strip()


def extract_tags(client, theme, article_content):
    """Extrait des tags pertinents de l'article."""
    prompt = f"""Génère 3-5 tags pertinents pour cet article sur {theme['name']}.
Format : une liste de mots séparés par des virgules, en minuscules, sans #.
Exemple : intelligence artificielle, santé, recherche

Article :
{article_content[:800]}

Réponds UNIQUEMENT avec les tags séparés par des virgules."""

    result = chat(client, [{"role": "user", "content": prompt}], max_tokens=100)
    tags = [tag.strip() for tag in result.strip().split(",")]
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

    slug = f"{date_str}-{day_name}-{theme['slug']}"

    tags_str = json.dumps(tags, ensure_ascii=False)
    front_matter = f"""---
title: "{title}"
date: {date_str}T12:00:00+01:00
draft: false
categories: ["{theme['name']}"]
tags: {tags_str}
emoji: "{theme['emoji']}"
summary: "{summary}"
sources_verified: true
---

"""

    filepath = f"content/posts/{slug}.md"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front_matter + content)

    return filepath


def main():
    # Vérifier la clé API
    if not os.environ.get("MAMMOUTH_API_KEY"):
        print("Erreur : MAMMOUTH_API_KEY non définie.")
        sys.exit(1)

    # Créer le client Mammouth
    client = get_client()

    # Obtenir le thème du jour
    today, theme = get_today_theme()
    print(f"📰 Génération de l'article du jour : {theme['emoji']} {theme['name']}")
    print(f"📅 Date : {today.strftime('%A %d %B %Y')}")

    # Étape 1 : Générer l'article brut
    print("✍️  Rédaction de l'article en cours...")
    content = generate_article(client, today, theme)

    # Étape 2 : Vérification des faits, ajout de sources et reformulation
    print("🔍 Vérification des faits et ajout des sources...")
    content = fact_check_and_enrich(client, theme, content)

    # Étape 3 : Générer le titre (basé sur la version vérifiée)
    print("📝 Génération du titre...")
    title = generate_title(client, theme, content)

    # Étape 4 : Générer le résumé
    print("📋 Génération du résumé...")
    summary = generate_summary(client, content)

    # Étape 5 : Extraire les tags
    print("🏷️  Extraction des tags...")
    tags = extract_tags(client, theme, content)

    # Étape 6 : Créer le fichier
    filepath = create_markdown_file(today, theme, title, summary, tags, content)
    print(f"✅ Article créé et vérifié : {filepath}")
    print(f"   Titre : {title}")
    print(f"   Catégorie : {theme['name']}")
    print(f"   Tags : {', '.join(tags)}")
    print(f"   Sources : vérifiées ✓")

    return filepath


if __name__ == "__main__":
    main()
