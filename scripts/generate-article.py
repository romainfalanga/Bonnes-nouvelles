#!/usr/bin/env python3
"""
Script de génération automatique d'articles pour Bonnes Nouvelles.
Pipeline multi-IA via l'API Mammouth :
  - Perplexity (sonar-pro) : recherche d'actualités réelles + fact-checking
  - Claude Sonnet : rédaction de l'article
  - Claude Haiku : titre, résumé, tags (tâches légères)

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
import re
import datetime
from openai import OpenAI

MAMMOUTH_BASE_URL = "https://api.mammouth.ai/v1"

# Modèles spécialisés par tâche
MODEL_SEARCH = "sonar-pro"          # Perplexity : accès web, recherche d'actualités
MODEL_WRITER = "claude-sonnet-4-6"  # Claude Sonnet : rédaction en français
MODEL_CHECKER = "sonar-pro"         # Perplexity : vérification des faits + liens
MODEL_LIGHT = "claude-haiku-4-5"    # Claude Haiku : titre, résumé, tags

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


def chat(client, model, messages, max_tokens):
    """Appel générique à l'API Mammouth avec un modèle spécifique."""
    response = client.chat.completions.create(
        model=model,
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


def search_news(client, today, theme):
    """Étape 1 : Recherche d'actualités réelles via Perplexity (sonar-pro).
    Perplexity a un accès web natif et retourne des infos vérifiées avec sources."""
    date_from = (today - datetime.timedelta(days=7)).strftime("%d/%m/%Y")
    date_to = today.strftime("%d/%m/%Y")

    prompt = f"""Recherche les bonnes nouvelles et actualités positives RÉELLES et RÉCENTES
dans le domaine "{theme['name']}" entre le {date_from} et le {date_to}.

Termes de recherche : {theme['search_terms']}

INSTRUCTIONS :
1. Trouve 3 à 5 actualités positives RÉELLES et VÉRIFIÉES de la dernière semaine
2. Pour CHAQUE actualité, fournis :
   - Un titre descriptif
   - Un résumé de 3-4 phrases avec des faits précis (chiffres, noms, dates, lieux)
   - L'URL source EXACTE de l'article original (pas une URL inventée)
   - Le nom du média ou de l'institution source
3. Privilégie les sources francophones quand elles existent, sinon utilise des sources internationales fiables

FORMAT DE RÉPONSE (JSON) :
{{
  "news": [
    {{
      "title": "Titre de la nouvelle",
      "summary": "Résumé avec faits précis...",
      "source_url": "https://...",
      "source_name": "Nom du média",
      "why_good_news": "Pourquoi c'est une bonne nouvelle"
    }}
  ]
}}

Réponds UNIQUEMENT avec le JSON, rien d'autre."""

    result = chat(client, MODEL_SEARCH, [{"role": "user", "content": prompt}], max_tokens=4096)

    # Extraire le JSON de la réponse
    json_match = re.search(r'\{[\s\S]*\}', result)
    if json_match:
        return json.loads(json_match.group())
    return {"news": []}


def write_article(client, today, theme, research_data):
    """Étape 2 : Rédaction de l'article par Claude Sonnet à partir des données réelles."""
    date_from = (today - datetime.timedelta(days=7)).strftime("%d/%m/%Y")
    date_to = today.strftime("%d/%m/%Y")

    news_text = json.dumps(research_data["news"], ensure_ascii=False, indent=2)

    prompt = f"""Tu es un journaliste optimiste pour le blog "Bonnes Nouvelles".
Ta mission : écrire un article en français basé sur les actualités RÉELLES ci-dessous dans le domaine "{theme['name']}" de la semaine du {date_from} au {date_to}.

ACTUALITÉS VÉRIFIÉES À UTILISER :
{news_text}

INSTRUCTIONS :
1. Rédige un article structuré et engageant basé UNIQUEMENT sur ces actualités vérifiées
2. N'invente AUCUN fait, chiffre ou source — utilise uniquement les données fournies
3. Intègre les liens sources directement dans le texte de manière naturelle

FORMAT DE L'ARTICLE (en Markdown) :
- Commence directement par une introduction engageante (2-3 phrases)
- Pour chaque bonne nouvelle, crée une section avec un titre ## accrocheur
- Chaque section fait 2-3 paragraphes avec les détails concrets des sources
- Pour chaque fait, intègre un lien hypertexte vers la source : [texte](URL)
- Explique clairement POURQUOI c'est une bonne nouvelle et CE QUE ÇA CHANGE
- Termine par une conclusion optimiste sur les tendances positives
- Ton : enthousiaste mais factuel, accessible à tous
- Longueur : 800-1200 mots environ

IMPORTANT :
- Ne commence PAS par le titre de l'article (il sera dans les métadonnées)
- Utilise TOUS les liens sources fournis dans les actualités
- Garde un ton positif et inspirant
- Écris en français courant, pas trop formel

Réponds UNIQUEMENT avec le contenu Markdown de l'article, rien d'autre."""

    return chat(client, MODEL_WRITER, [{"role": "user", "content": prompt}], max_tokens=4096)


def fact_check_and_verify_links(client, theme, article_content):
    """Étape 3 : Fact-checking et vérification des liens via Perplexity.
    Perplexity peut vérifier les URLs et les faits grâce à son accès web."""
    prompt = f"""Tu es un vérificateur de faits spécialisé en {theme['name']}.

Voici un article de blog à vérifier :
---
{article_content}
---

MISSIONS :

1. VÉRIFICATION DES FAITS :
   - Vérifie chaque fait, chiffre et affirmation dans l'article via une recherche web
   - Si un fait est inexact, corrige-le avec les bonnes informations
   - Si un fait ne peut pas être confirmé, reformule avec des termes nuancés

2. VÉRIFICATION DES LIENS :
   - Vérifie que chaque URL dans l'article mène bien à un contenu existant et pertinent
   - Si une URL est cassée ou ne correspond pas au contenu mentionné, remplace-la par la bonne URL
   - Si tu ne trouves pas de bon lien de remplacement, remplace par un lien vers un article pertinent du même média ou d'un média fiable

3. QUALITÉ ÉDITORIALE :
   - Peaufine le style pour qu'il soit fluide et engageant
   - Assure-toi que les transitions entre sections sont naturelles
   - Garde le ton optimiste mais crédible

RÈGLES :
- Conserve la structure Markdown (## pour les titres)
- Ne commence PAS par un titre principal (pas de # en début)
- Garde une longueur similaire (800-1200 mots)
- Chaque section ## doit contenir au moins 1 lien source vérifié
- Les liens doivent être intégrés naturellement dans le texte

Réponds UNIQUEMENT avec l'article final corrigé en Markdown, rien d'autre."""

    return chat(client, MODEL_CHECKER, [{"role": "user", "content": prompt}], max_tokens=5000)


def generate_title(client, theme, article_content):
    """Génère un titre accrocheur via Claude Haiku."""
    prompt = f"""Génère UN titre court et accrocheur (max 80 caractères) pour cet article de blog sur les bonnes nouvelles en {theme['name']}.
Le titre doit être optimiste et donner envie de lire.
Ne mets PAS de guillemets autour du titre.

Début de l'article :
{article_content[:500]}

Réponds UNIQUEMENT avec le titre, rien d'autre."""

    result = chat(client, MODEL_LIGHT, [{"role": "user", "content": prompt}], max_tokens=100)
    return result.strip().strip('"').strip("«").strip("»").strip()


def generate_summary(client, article_content):
    """Génère un résumé court via Claude Haiku."""
    prompt = f"""Génère un résumé de 1-2 phrases (max 160 caractères) pour cet article.
Le résumé doit donner envie de lire l'article complet.

Article :
{article_content[:1000]}

Réponds UNIQUEMENT avec le résumé, rien d'autre."""

    return chat(client, MODEL_LIGHT, [{"role": "user", "content": prompt}], max_tokens=200).strip()


def extract_tags(client, theme, article_content):
    """Extrait des tags pertinents via Claude Haiku."""
    prompt = f"""Génère 3-5 tags pertinents pour cet article sur {theme['name']}.
Format : une liste de mots séparés par des virgules, en minuscules, sans #.
Exemple : intelligence artificielle, santé, recherche

Article :
{article_content[:800]}

Réponds UNIQUEMENT avec les tags séparés par des virgules."""

    result = chat(client, MODEL_LIGHT, [{"role": "user", "content": prompt}], max_tokens=100)
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

    # Étape 1 : Recherche d'actualités réelles via Perplexity
    print(f"🔎 Recherche d'actualités via Perplexity ({MODEL_SEARCH})...")
    research = search_news(client, today, theme)
    news_count = len(research.get("news", []))
    print(f"   → {news_count} actualités trouvées")

    if news_count == 0:
        print("Erreur : aucune actualité trouvée.")
        sys.exit(1)

    # Étape 2 : Rédaction de l'article par Claude Sonnet
    print(f"✍️  Rédaction de l'article via Claude Sonnet ({MODEL_WRITER})...")
    content = write_article(client, today, theme, research)

    # Étape 3 : Fact-checking et vérification des liens via Perplexity
    print(f"🔍 Vérification des faits et des liens via Perplexity ({MODEL_CHECKER})...")
    content = fact_check_and_verify_links(client, theme, content)

    # Étape 4 : Titre, résumé, tags via Claude Haiku (rapide et économique)
    print(f"📝 Génération du titre, résumé et tags via Claude Haiku ({MODEL_LIGHT})...")
    title = generate_title(client, theme, content)
    summary = generate_summary(client, content)
    tags = extract_tags(client, theme, content)

    # Étape 5 : Créer le fichier
    filepath = create_markdown_file(today, theme, title, summary, tags, content)
    print(f"✅ Article créé et vérifié : {filepath}")
    print(f"   Titre : {title}")
    print(f"   Catégorie : {theme['name']}")
    print(f"   Tags : {', '.join(tags)}")
    print(f"   Pipeline : {MODEL_SEARCH} → {MODEL_WRITER} → {MODEL_CHECKER} → {MODEL_LIGHT}")

    return filepath


if __name__ == "__main__":
    main()
