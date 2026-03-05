#!/usr/bin/env python3
"""
Script de génération automatique d'articles pour Bonnes Nouvelles.
Pipeline multi-IA via l'API Mammouth :
  - Perplexity (sonar-pro) : recherche d'actualités réelles + fact-checking
  - Claude Sonnet : rédaction de l'article (persona Nova)
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
        "search_terms": "bonnes nouvelles intelligence artificielle IA découverte avancée",
        "description": "Les avancées positives dans le monde de l'IA",
    },
    1: {
        "name": "Médecine et Santé",
        "slug": "medecine-et-sante",
        "search_terms": "bonnes nouvelles médecine santé découverte médicale traitement",
        "description": "Les découvertes médicales et avancées en santé",
    },
    2: {
        "name": "Physique et Univers",
        "slug": "physique-et-univers",
        "search_terms": "découverte physique astronomie univers espace sciences",
        "description": "Les découvertes fascinantes en physique et astronomie",
    },
    3: {
        "name": "Invention",
        "slug": "invention",
        "search_terms": "invention innovation technologie brevet découverte",
        "description": "Les inventions qui changent le monde",
    },
    4: {
        "name": "Écologie",
        "slug": "ecologie",
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
    """Retourne le thème du jour basé sur le jour de la semaine.
    Supporte la variable d'environnement FORCE_DATE (YYYY-MM-DD) pour forcer une date."""
    force_date = os.environ.get("FORCE_DATE", "").strip()
    if force_date:
        try:
            today = datetime.date.fromisoformat(force_date)
            print(f"[Nova] Date forcee : {today}")
        except ValueError:
            print(f"[Nova] Erreur : date invalide '{force_date}', format attendu YYYY-MM-DD")
            sys.exit(1)
    else:
        today = datetime.date.today()

    weekday = today.weekday()  # 0=lundi, 6=dimanche

    if weekday > 4:  # Week-end
        print("[Nova] Pas de publication le week-end.")
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
    """Étape 2 : Rédaction de l'article par Claude Sonnet (persona Nova)."""
    date_from = (today - datetime.timedelta(days=7)).strftime("%d/%m/%Y")
    date_to = today.strftime("%d/%m/%Y")

    news_count = len(research_data["news"])
    news_text = json.dumps(research_data["news"], ensure_ascii=False, indent=2)

    prompt = f"""Tu es Nova, chroniqueuse IA du blog "Bonnes Nouvelles". Ta mission : documenter les progrès de l'humanité dans le domaine "{theme['name']}".

Écris un article en français basé sur les {news_count} actualités RÉELLES ci-dessous, couvrant la semaine du {date_from} au {date_to}.

ACTUALITÉS VÉRIFIÉES À UTILISER :
{news_text}

STRUCTURE OBLIGATOIRE DE L'ARTICLE :

1. INTRODUCTION (un paragraphe) :
   - Résume en 3-4 phrases les sujets qui seront abordés dans l'article
   - Donne au lecteur une vue d'ensemble de ce qu'il va découvrir
   - Mentionne brièvement chaque nouvelle pour donner envie de lire la suite
   - Exemple de structure : "Cette semaine en [domaine], [résumé nouvelle 1], [résumé nouvelle 2] et [résumé nouvelle 3]. Voici le détail de ces avancées."

2. SECTIONS (une par nouvelle) :
   - Titre ## en texte brut, accrocheur et optimisé SEO (mot-clé principal inclus)
   - AUCUN emoji dans les titres ni dans le texte
   - 2-3 paragraphes avec les détails concrets des sources
   - Pour chaque fait, intègre un lien hypertexte vers la source : [texte](URL)
   - Explique clairement POURQUOI c'est une bonne nouvelle et CE QUE ÇA CHANGE

3. CONCLUSION (un paragraphe) :
   - Synthèse des tendances positives de la semaine

STYLE D'ÉCRITURE OBLIGATOIRE :
- AUCUN emoji nulle part dans l'article
- N'utilise JAMAIS le tiret cadratin ou le tiret demi-cadratin pour faire des incises
- N'utilise JAMAIS "il est important de noter que", "il convient de souligner", "force est de constater"
- N'utilise JAMAIS "en effet", "par ailleurs", "en outre", "de surcroît", "à cet égard", "en somme"
- Évite les formulations génériques comme "dans un monde où...", "à l'heure où..."
- Préfère les phrases courtes et directes
- Varie la structure des phrases
- Écris comme un vrai journaliste humain, pas comme un assistant IA
- Ton : informé, accessible, légèrement enthousiaste sans en faire trop
- Longueur : 800-1200 mots environ

Réponds UNIQUEMENT avec le contenu Markdown de l'article, rien d'autre."""

    return chat(client, MODEL_WRITER, [{"role": "user", "content": prompt}], max_tokens=4096)


def fact_check_and_verify_links(client, theme, article_content):
    """Étape 3 : Fact-checking et vérification des liens via Perplexity."""
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
   - Si une URL est cassée ou ne correspond pas au contenu mentionné, remplace-la par la bonne URL trouvée via recherche web
   - Si tu ne trouves pas de bon lien de remplacement, remplace par un lien vers un article pertinent du même média ou d'un média fiable
   - CHAQUE lien dans l'article final doit pointer vers une page web qui existe réellement

3. NETTOYAGE DU STYLE :
   - Remplace TOUS les tirets cadratins et demi-cadratins par des virgules, parenthèses ou reformulations
   - Supprime les tournures typiques de l'IA : "il est important de noter", "il convient de souligner", "force est de constater", "en effet", "par ailleurs", "en outre", "de surcroît"
   - Remplace les formulations pompeuses par des phrases simples et directes
   - Supprime TOUS les emojis s'il en reste
   - Le texte doit sembler écrit par un journaliste humain

4. QUALITÉ ÉDITORIALE :
   - Peaufine le style pour qu'il soit fluide et engageant
   - Assure-toi que les transitions entre sections sont naturelles
   - Garde le ton optimiste mais crédible

RÈGLES :
- Conserve la structure Markdown (## pour les titres)
- Ne commence PAS par un titre principal (pas de # en début)
- Garde une longueur similaire (800-1200 mots)
- Chaque section ## doit contenir au moins 1 lien source vérifié
- Les liens doivent être intégrés naturellement dans le texte
- AUCUN tiret cadratin ni demi-cadratin dans le texte final
- AUCUN emoji dans le texte final

Réponds UNIQUEMENT avec l'article final corrigé en Markdown, rien d'autre."""

    return chat(client, MODEL_CHECKER, [{"role": "user", "content": prompt}], max_tokens=5000)


def generate_title(client, theme, article_content):
    """Génère un titre accrocheur via Claude Haiku."""
    prompt = f"""Génère UN titre court et accrocheur (max 65 caractères) pour cet article de blog sur les bonnes nouvelles en {theme['name']}.
Le titre doit :
- Être optimiste et donner envie de lire
- Contenir le mot-clé principal du sujet pour le SEO
- Ne PAS contenir de tiret cadratin ni de tiret demi-cadratin
- Ne PAS contenir d'emoji
- Ne PAS être entouré de guillemets

Début de l'article :
{article_content[:500]}

Réponds UNIQUEMENT avec le titre, rien d'autre."""

    result = chat(client, MODEL_LIGHT, [{"role": "user", "content": prompt}], max_tokens=100)
    return result.strip().strip('"').strip("«").strip("»").strip()


def generate_summary(client, article_content):
    """Génère un résumé court via Claude Haiku."""
    prompt = f"""Génère une meta description SEO de 1-2 phrases (entre 120 et 155 caractères) pour cet article.
La description doit :
- Donner envie de cliquer depuis les résultats Google
- Contenir les mots-clés principaux de l'article
- Ne PAS contenir de tiret cadratin ni de tiret demi-cadratin
- Ne PAS contenir d'emoji

Article :
{article_content[:1000]}

Réponds UNIQUEMENT avec la description, rien d'autre."""

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


def clean_ai_patterns(text):
    """Supprime les patterns typiques de texte généré par IA."""
    # Remplacer les tirets cadratins et demi-cadratins par des virgules
    text = text.replace(" — ", ", ")
    text = text.replace(" – ", ", ")
    text = text.replace("—", ", ")
    text = text.replace("–", ", ")
    # Supprimer les emojis courants dans les titres
    text = re.sub(
        r'[\U0001F300-\U0001F9FF\U00002702-\U000027B0\U0000FE00-\U0000FE0F'
        r'\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF'
        r'\U0000200D\U00002B50]+',
        '', text
    )
    return text


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
    safe_title = title.replace('"', '\\"')
    safe_summary = summary.replace('"', '\\"')
    front_matter = f"""---
title: "{safe_title}"
date: {date_str}T12:00:00+01:00
draft: false
description: "{safe_summary}"
author: "Nova"
categories: ["{theme['name']}"]
tags: {tags_str}
summary: "{safe_summary}"
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
    print(f"[Nova] Generation article : {theme['name']}")
    print(f"[Nova] Date : {today.strftime('%A %d %B %Y')}")

    # Étape 1 : Recherche d'actualités réelles via Perplexity
    print(f"[Nova] Recherche via Perplexity ({MODEL_SEARCH})...")
    research = search_news(client, today, theme)
    news_count = len(research.get("news", []))
    print(f"[Nova] {news_count} actualites trouvees")

    if news_count == 0:
        print("[Nova] Erreur : aucune actualite trouvee.")
        sys.exit(1)

    # Étape 2 : Rédaction de l'article par Claude Sonnet
    print(f"[Nova] Redaction via Claude Sonnet ({MODEL_WRITER})...")
    content = write_article(client, today, theme, research)

    # Étape 3 : Fact-checking et vérification des liens via Perplexity
    print(f"[Nova] Fact-checking via Perplexity ({MODEL_CHECKER})...")
    content = fact_check_and_verify_links(client, theme, content)

    # Étape 4 : Nettoyage des patterns IA résiduels
    content = clean_ai_patterns(content)

    # Étape 5 : Titre, résumé, tags via Claude Haiku
    print(f"[Nova] Titre, resume, tags via Claude Haiku ({MODEL_LIGHT})...")
    title = clean_ai_patterns(generate_title(client, theme, content))
    summary = clean_ai_patterns(generate_summary(client, content))
    tags = extract_tags(client, theme, content)

    # Étape 6 : Créer le fichier
    filepath = create_markdown_file(today, theme, title, summary, tags, content)
    print(f"[Nova] Article cree : {filepath}")
    print(f"[Nova] Titre : {title}")
    print(f"[Nova] Categorie : {theme['name']}")
    print(f"[Nova] Tags : {', '.join(tags)}")
    print(f"[Nova] Pipeline : {MODEL_SEARCH} > {MODEL_WRITER} > {MODEL_CHECKER} > {MODEL_LIGHT}")

    return filepath


if __name__ == "__main__":
    main()
