#!/usr/bin/env python3
"""
Bonnes Nouvelles - Pipeline de génération d'articles v3.0

Pipeline multi-IA via l'API Mammouth :
  1. Recherche approfondie (Perplexity sonar-pro) : actualités réelles des 7 derniers jours
  2. Recherche complémentaire (Perplexity sonar-pro) : approfondissement de chaque actualité
  3. Rédaction longue (Claude Sonnet) : article structuré 1500-2500 mots, angle éditorial par thème
  4. Fact-checking et vérification des liens (Perplexity sonar-pro)
  5. Compilation des sources vérifiées (Claude Sonnet)
  6. SEO : titre, meta description, tags (Claude Haiku)

Thèmes hebdomadaires :
  - Lundi    : Intelligence Artificielle — nouvelles IA, capacités inédites
  - Mardi    : Médecine et Santé — longévité, traitements, conditions de vie
  - Mercredi : Physique et Univers — découvertes, compréhension de l'univers
  - Jeudi    : Invention — inventions physiques améliorant la vie humaine
  - Vendredi : Écologie — outils et idées pour vivre en harmonie avec la nature
"""

import os
import sys
import json
import re
import datetime
import zoneinfo
from openai import OpenAI

MAMMOUTH_BASE_URL = "https://api.mammouth.ai/v1"

# Fuseau horaire de référence
TIMEZONE = zoneinfo.ZoneInfo("Europe/Paris")

# Modèles spécialisés par tâche
MODEL_SEARCH = "sonar-pro"          # Perplexity : accès web, recherche d'actualités
MODEL_WRITER = "claude-sonnet-4-6"  # Claude Sonnet : rédaction longue en français
MODEL_CHECKER = "sonar-pro"         # Perplexity : fact-checking + vérification des liens
MODEL_LIGHT = "claude-haiku-4-5"    # Claude Haiku : titre, résumé, tags

# Configuration des thèmes par jour de la semaine (0=lundi, 4=vendredi)
THEMES = {
    0: {
        "name": "Intelligence Artificielle",
        "slug": "intelligence-artificielle",
        "description": "Les avancées positives dans le monde de l'IA",
        "search_queries": [
            "new AI models released this week breakthroughs capabilities",
            "nouvelles IA intelligence artificielle avancée semaine",
            "AI breakthrough new capabilities not possible before 2026",
        ],
        "editorial_angle": """ANGLE ÉDITORIAL — Intelligence Artificielle :
Tu couvres les NOUVELLES IA et les NOUVELLES CAPACITÉS rendues possibles par l'IA cette semaine.
Ce qui intéresse le lecteur :
- Les nouveaux modèles d'IA sortis cette semaine et ce qu'ils permettent de faire de nouveau
- Les applications concrètes de l'IA qui n'étaient pas possibles avant (médecine, science, créativité, productivité)
- Les outils IA accessibles au grand public qui changent la donne
- Les percées techniques majeures (raisonnement, multimodalité, agents autonomes)
- Les records battus, les benchmarks dépassés, les limites repoussées
Montre au lecteur CE QUI EST NOUVEAU et POURQUOI C'EST IMPORTANT pour sa vie quotidienne ou pour l'avenir.""",
    },
    1: {
        "name": "Médecine et Santé",
        "slug": "medecine-et-sante",
        "description": "Les découvertes médicales et avancées en santé",
        "search_queries": [
            "medical breakthrough treatment discovery this week 2026",
            "découverte médicale traitement santé avancée semaine 2026",
            "longevity health anti-aging breakthrough new treatment approved",
        ],
        "editorial_angle": """ANGLE ÉDITORIAL — Médecine et Santé :
Tu couvres les AVANCÉES MÉDICALES qui permettent à l'être humain de vivre plus longtemps et en meilleure santé.
Ce qui intéresse le lecteur :
- Les nouveaux traitements approuvés ou en phase avancée d'essais cliniques
- Les découvertes sur la longévité, le vieillissement et la régénération cellulaire
- Les technologies médicales qui améliorent le diagnostic ou le traitement
- Les avancées en thérapie génique, immunothérapie, médecine personnalisée
- Les percées contre les maladies majeures (cancer, Alzheimer, maladies cardiaques, diabète)
- Les innovations qui rendent les soins plus accessibles ou moins invasifs
Montre au lecteur les PROGRÈS CONCRETS qui sauvent des vies et allongent l'espérance de vie en bonne santé.""",
    },
    2: {
        "name": "Physique et Univers",
        "slug": "physique-et-univers",
        "description": "Les découvertes fascinantes en physique et astronomie",
        "search_queries": [
            "physics discovery universe space astronomy breakthrough 2026",
            "découverte physique univers astronomie espace semaine 2026",
            "quantum physics cosmology new discovery exoplanet telescope",
        ],
        "editorial_angle": """ANGLE ÉDITORIAL — Physique et Univers :
Tu couvres les DÉCOUVERTES en physique fondamentale et dans l'exploration de l'univers.
Ce qui intéresse le lecteur :
- Les nouvelles découvertes qui changent notre compréhension de l'univers
- Les observations astronomiques majeures (exoplanètes, trous noirs, ondes gravitationnelles)
- Les avancées en physique quantique, physique des particules, matière noire
- Les missions spatiales en cours et leurs résultats (JWST, Mars, astéroïdes)
- Les théories confirmées ou réfutées par de nouvelles données
- Les technologies qui repoussent les limites de l'observation et de l'expérimentation
Montre au lecteur à quel point notre COMPRÉHENSION DE L'UNIVERS progresse et ce que ça signifie.""",
    },
    3: {
        "name": "Invention",
        "slug": "invention",
        "description": "Les inventions qui changent le monde",
        "search_queries": [
            "new invention technology innovation improve life 2026",
            "invention innovation technologie améliorer vie quotidienne 2026",
            "breakthrough invention patent prototype new device solution",
        ],
        "editorial_angle": """ANGLE ÉDITORIAL — Inventions :
Tu couvres les INVENTIONS PHYSIQUES et TECHNOLOGIQUES qui améliorent concrètement la vie des gens.
Ce qui intéresse le lecteur :
- Les nouvelles inventions physiques (appareils, dispositifs, matériaux, prototypes)
- Les innovations qui résolvent des problèmes concrets du quotidien
- Les technologies qui améliorent l'accessibilité pour les personnes handicapées
- Les inventions qui rendent l'eau potable, l'énergie ou la nourriture plus accessibles
- Les prototypes et brevets qui pourraient transformer un secteur entier
- Les solutions low-tech ou high-tech ingénieuses qui améliorent les conditions de vie
PAS de logiciels ni d'IA ici. On parle d'inventions PHYSIQUES, tangibles, concrètes.""",
    },
    4: {
        "name": "Écologie",
        "slug": "ecologie",
        "description": "Les avancées positives pour notre planète",
        "search_queries": [
            "ecology environment positive news climate solution 2026",
            "écologie environnement bonne nouvelle climat biodiversité 2026",
            "renewable energy biodiversity conservation breakthrough green technology",
        ],
        "editorial_angle": """ANGLE ÉDITORIAL — Écologie :
Tu couvres les OUTILS, IDÉES et AVANCÉES qui permettent de vivre en harmonie avec la nature.
Ce qui intéresse le lecteur :
- Les technologies vertes qui deviennent accessibles et pratiques au quotidien
- Les initiatives de restauration des écosystèmes et de la biodiversité
- Les solutions concrètes pour réduire son empreinte carbone facilement
- Les politiques environnementales qui fonctionnent et leurs résultats mesurables
- Les innovations en énergie renouvelable, recyclage, agriculture durable
- Les projets de reforestation, dépollution, protection des espèces
Montre au lecteur des SOLUTIONS PRATIQUES et des RÉSULTATS POSITIFS, pas du catastrophisme.""",
    },
}

# Jours en français
WEEKDAY_NAMES = {0: "lundi", 1: "mardi", 2: "mercredi", 3: "jeudi", 4: "vendredi"}


def get_client():
    """Crée un client OpenAI pointant vers l'API Mammouth."""
    return OpenAI(
        base_url=MAMMOUTH_BASE_URL,
        api_key=os.environ.get("MAMMOUTH_API_KEY"),
    )


def chat(client, model, messages, max_tokens, temperature=0.7):
    """Appel générique à l'API Mammouth avec un modèle spécifique."""
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages,
    )
    return response.choices[0].message.content


def get_today_theme():
    """Retourne le thème du jour basé sur le jour de la semaine.
    Supporte la variable d'environnement FORCE_DATE (YYYY-MM-DD) pour forcer une date.
    Utilise toujours le fuseau horaire Europe/Paris."""
    force_date = os.environ.get("FORCE_DATE", "").strip()
    if force_date:
        try:
            today = datetime.date.fromisoformat(force_date)
            print(f"[Nova] Date forcee : {today}")
        except ValueError:
            print(f"[Nova] Erreur : date invalide '{force_date}', format attendu YYYY-MM-DD")
            sys.exit(1)
    else:
        today = datetime.datetime.now(TIMEZONE).date()
        print(f"[Nova] Date du jour (Europe/Paris) : {today}")

    weekday = today.weekday()

    if weekday > 4:
        print("[Nova] Pas de publication le week-end.")
        sys.exit(0)

    return today, THEMES[weekday]


def extract_json(text):
    """Extrait le premier objet JSON valide d'un texte."""
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return None


def search_news(client, today, theme):
    """Étape 1 : Recherche large d'actualités réelles via Perplexity.
    Effectue plusieurs recherches avec des termes différents pour maximiser la couverture."""
    date_from = today - datetime.timedelta(days=7)
    date_from_fr = date_from.strftime("%d/%m/%Y")
    date_to_fr = today.strftime("%d/%m/%Y")
    date_from_iso = date_from.isoformat()
    date_to_iso = today.isoformat()

    all_news = []

    for i, query in enumerate(theme["search_queries"]):
        print(f"[Nova] Recherche {i+1}/{len(theme['search_queries'])} : {query[:60]}...")

        prompt = f"""Nous sommes le {date_to_fr} ({date_to_iso}).

Recherche des actualités positives et des avancées RÉELLES dans le domaine "{theme['name']}".

PÉRIODE STRICTE : du {date_from_fr} au {date_to_fr} (soit du {date_from_iso} au {date_to_iso}).
NE RETOURNE QUE des informations publiées dans cette fenêtre de 7 jours. RIEN de plus ancien.

Requête de recherche : {query}

INSTRUCTIONS :
1. Trouve 3 à 5 actualités positives RÉELLES publiées entre le {date_from_iso} et le {date_to_iso}
2. Pour CHAQUE actualité, fournis :
   - title : titre descriptif et factuel
   - summary : résumé détaillé de 4-6 phrases avec des FAITS PRÉCIS (chiffres, noms complets, institutions, dates, lieux)
   - published_date : date de publication au format YYYY-MM-DD
   - source_url : URL EXACTE de l'article source original
   - source_name : nom du média ou de l'institution
   - key_facts : liste de 3-5 faits clés vérifiables (chiffres, noms, données)
   - why_important : pourquoi c'est significatif, en 2-3 phrases
3. Privilégie les sources fiables : médias reconnus, revues scientifiques, institutions
4. Si une source francophone existe, inclus-la. Sinon, utilise des sources internationales

FORMAT JSON :
{{
  "news": [
    {{
      "title": "...",
      "summary": "...",
      "published_date": "YYYY-MM-DD",
      "source_url": "https://...",
      "source_name": "...",
      "key_facts": ["fait 1", "fait 2", "fait 3"],
      "why_important": "..."
    }}
  ]
}}

Réponds UNIQUEMENT avec le JSON."""

        result = chat(client, MODEL_SEARCH, [{"role": "user", "content": prompt}], max_tokens=4096, temperature=0.3)
        data = extract_json(result)

        if data:
            for news in data.get("news", []):
                # Filtrer les articles hors période
                pub_date_str = news.get("published_date", "")
                if pub_date_str:
                    try:
                        pub_date = datetime.date.fromisoformat(pub_date_str)
                        if pub_date < date_from:
                            print(f"[Nova]   Ignoree (date {pub_date} < {date_from}) : {news.get('title', '?')[:60]}")
                            continue
                    except ValueError:
                        pass
                all_news.append(news)

    # Dédoublonner par titre (similitude approximative)
    seen_titles = set()
    unique_news = []
    for news in all_news:
        title_key = news.get("title", "").lower().strip()[:50]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_news.append(news)

    return {"news": unique_news}


def deepen_research(client, today, theme, news_items):
    """Étape 2 : Approfondissement de chaque actualité via Perplexity.
    Pour chaque nouvelle trouvée, récupère plus de contexte, chiffres et détails."""
    date_to_fr = today.strftime("%d/%m/%Y")
    date_to_iso = today.isoformat()

    titles = "\n".join(f"- {n.get('title', '?')}" for n in news_items)
    summaries = "\n\n".join(
        f"### {n.get('title', '?')}\n{n.get('summary', '')}\nSource : {n.get('source_name', '?')} ({n.get('source_url', '')})"
        for n in news_items
    )

    prompt = f"""Nous sommes le {date_to_fr} ({date_to_iso}).

Voici {len(news_items)} actualités récentes dans le domaine "{theme['name']}" que je dois approfondir :

{summaries}

Pour CHACUNE de ces actualités, je veux que tu recherches des INFORMATIONS COMPLÉMENTAIRES :

1. CONTEXTE : Quel est le contexte plus large ? Quels travaux ou événements précédents ont mené à cette avancée ?
2. DÉTAILS TECHNIQUES : Chiffres précis, données quantitatives, méthodologie, résultats mesurables
3. IMPACT CONCRET : Qui est directement impacté ? Combien de personnes ? Quel changement concret ?
4. EXPERTS : Citations ou réactions d'experts du domaine, si disponibles
5. PERSPECTIVE : Quelles sont les prochaines étapes prévues ? Calendrier ?
6. SOURCES ADDITIONNELLES : D'autres articles ou sources qui couvrent le même sujet

FORMAT JSON :
{{
  "enrichments": [
    {{
      "original_title": "titre original de la nouvelle",
      "context": "contexte élargi en 3-4 phrases",
      "technical_details": "détails techniques, chiffres, données",
      "concrete_impact": "impact concret sur les gens",
      "expert_quotes": "citations d'experts si disponibles",
      "next_steps": "prochaines étapes et calendrier",
      "additional_sources": [
        {{"url": "https://...", "name": "Nom du média", "title": "Titre de l'article"}}
      ]
    }}
  ]
}}

Réponds UNIQUEMENT avec le JSON."""

    result = chat(client, MODEL_SEARCH, [{"role": "user", "content": prompt}], max_tokens=6000, temperature=0.3)
    data = extract_json(result)

    if data and "enrichments" in data:
        # Fusionner les enrichissements avec les news originales
        enrichments_by_title = {}
        for e in data["enrichments"]:
            key = e.get("original_title", "").lower().strip()[:50]
            enrichments_by_title[key] = e

        for news in news_items:
            key = news.get("title", "").lower().strip()[:50]
            if key in enrichments_by_title:
                news["enrichment"] = enrichments_by_title[key]

    return news_items


def write_article(client, today, theme, enriched_news):
    """Étape 3 : Rédaction de l'article approfondi par Claude Sonnet."""
    date_from = today - datetime.timedelta(days=7)
    date_from_fr = date_from.strftime("%d/%m/%Y")
    date_to_fr = today.strftime("%d/%m/%Y")

    news_text = json.dumps(enriched_news, ensure_ascii=False, indent=2)

    system_prompt = f"""Tu es Nova, chroniqueuse IA du blog "Bonnes Nouvelles".
Tu écris des articles de fond, approfondis et bien documentés sur les avancées positives de l'humanité.
Ton style est celui d'une journaliste scientifique expérimentée : précise, accessible, engageante.
Tu écris en français impeccable. Tu ne ressembles pas à un assistant IA.

{theme['editorial_angle']}

RÈGLES DE STYLE ABSOLUES :
- AUCUN emoji nulle part, jamais
- JAMAIS de tiret cadratin ni de tiret demi-cadratin pour faire des incises
- JAMAIS ces expressions : "il est important de noter", "il convient de souligner", "force est de constater", "en effet", "par ailleurs", "en outre", "de surcroît", "à cet égard", "en somme", "il est intéressant de", "notons que", "soulignons que", "dans un monde où", "à l'heure où"
- Phrases courtes et directes, variées dans leur structure
- Ton : informé, accessible, enthousiaste sans excès, crédible"""

    user_prompt = f"""Écris un article approfondi couvrant la semaine du {date_from_fr} au {date_to_fr} dans le domaine "{theme['name']}".

Voici les {len(enriched_news)} actualités vérifiées avec leurs enrichissements :
{news_text}

STRUCTURE OBLIGATOIRE :

1. INTRODUCTION (2-3 paragraphes, 150-250 mots) :
   - Premier paragraphe : accroche forte qui donne le ton de la semaine, un fait marquant ou une tendance
   - Deuxième paragraphe : présentation de CHAQUE sujet qui sera développé dans l'article, en une phrase chacun
   - Troisième paragraphe (optionnel) : mise en perspective, pourquoi cette semaine est significative
   - Le lecteur doit savoir exactement ce qu'il va lire et avoir envie de continuer

2. SECTIONS DÉTAILLÉES (une par actualité, chacune avec un titre ##) :
   - Titre ## : informatif, contenant le mot-clé principal, optimisé SEO, SANS emoji
   - Paragraphe 1 : le fait principal avec les données clés (qui, quoi, où, quand, combien)
   - Paragraphe 2 : le contexte et les détails techniques accessibles au grand public
   - Paragraphe 3 : l'impact concret, ce que ça change pour les gens, les perspectives
   - Intègre les liens vers les sources directement dans le texte : [texte descriptif](URL)
   - Chaque section doit faire 200-400 mots minimum

3. CONCLUSION "Ce qu'il faut retenir" (1-2 paragraphes) :
   - Synthèse des tendances de la semaine
   - Mise en perspective : qu'est-ce que ces avancées signifient ensemble ?
   - Ouverture sur ce qui est à surveiller dans les semaines à venir

LONGUEUR TOTALE : 1500 à 2500 mots. Sois généreux en détails et en analyse.

NE COMMENCE PAS par un titre # principal. Commence directement par l'introduction.
NE METS PAS de section "Sources" à la fin, elle sera ajoutée automatiquement.

Réponds UNIQUEMENT avec le contenu Markdown de l'article."""

    return chat(
        client, MODEL_WRITER,
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        max_tokens=8000, temperature=0.7
    )


def fact_check_article(client, theme, article_content):
    """Étape 4 : Fact-checking approfondi et vérification des liens via Perplexity."""
    prompt = f"""Tu es un vérificateur de faits senior spécialisé en {theme['name']}.

Voici un article de blog à vérifier rigoureusement :
---
{article_content}
---

VÉRIFICATION EN 4 POINTS :

1. FAITS ET CHIFFRES :
   - Vérifie CHAQUE fait, chiffre, nom et affirmation via une recherche web
   - Si un fait est inexact, corrige-le avec les bonnes informations et la bonne source
   - Si un fait ne peut pas être confirmé, nuance la formulation ("selon...", "d'après...")
   - Vérifie les noms des chercheurs, institutions, dates de publication

2. LIENS ET URLS :
   - Vérifie que CHAQUE URL dans l'article mène vers une page existante et pertinente
   - Si une URL est cassée ou incorrecte, remplace-la par l'URL correcte trouvée via recherche
   - Si tu ne trouves pas l'URL exacte, remplace par un article fiable sur le même sujet
   - CHAQUE lien doit fonctionner et pointer vers du contenu en rapport avec le texte

3. COHÉRENCE :
   - Vérifie que les dates mentionnées sont cohérentes
   - Vérifie que les chiffres sont dans le bon ordre de grandeur
   - Vérifie que les attributions (qui a dit/fait quoi) sont correctes

4. NETTOYAGE FINAL :
   - Remplace TOUS les tirets cadratins et demi-cadratins par des virgules ou reformulations
   - Supprime les tournures IA résiduelles
   - Supprime les emojis s'il en reste
   - Assure des transitions naturelles entre sections

RÈGLES :
- Conserve EXACTEMENT la même structure (titres ##, paragraphes)
- Ne commence PAS par un titre # principal
- Garde la même longueur (ne raccourcis pas)
- Chaque section ## doit contenir au moins 2 liens sources vérifiés
- Améliore la précision sans sacrifier la lisibilité

Réponds UNIQUEMENT avec l'article corrigé en Markdown."""

    return chat(client, MODEL_CHECKER, [{"role": "user", "content": prompt}], max_tokens=8000, temperature=0.1)


def compile_sources(client, article_content, enriched_news):
    """Étape 5 : Compilation et vérification finale des sources.
    Extrait toutes les sources de l'article et les enrichissements pour créer
    une section Sources propre et vérifiée."""
    # Extraire les URLs de l'article
    urls_in_article = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', article_content)

    # Collecter les sources des enrichissements
    research_sources = []
    for news in enriched_news:
        if news.get("source_url"):
            research_sources.append({
                "url": news["source_url"],
                "name": news.get("source_name", ""),
                "title": news.get("title", ""),
            })
        enrichment = news.get("enrichment", {})
        for src in enrichment.get("additional_sources", []):
            if src.get("url"):
                research_sources.append(src)

    sources_text = json.dumps(research_sources, ensure_ascii=False, indent=2)
    article_urls = "\n".join(f"- [{text}]({url})" for text, url in urls_in_article)

    prompt = f"""Voici les sources utilisées dans un article et celles trouvées pendant la recherche.

SOURCES DANS L'ARTICLE (liens hypertextes) :
{article_urls if article_urls else "Aucun lien trouvé dans l'article"}

SOURCES DE LA RECHERCHE :
{sources_text}

Génère une section "Sources" propre et organisée pour la fin de l'article.

RÈGLES :
1. Inclus UNIQUEMENT les sources qui ont réellement contribué au contenu de l'article
2. Dédoublonne les URLs identiques
3. Pour chaque source, utilise le format : - [Titre de l'article - Nom du média](URL)
4. Classe les sources dans l'ordre d'apparition dans l'article
5. Maximum 10 sources, minimum 3
6. Ne mets PAS de titre ## ou ### avant la liste, juste les liens

Réponds UNIQUEMENT avec la liste de sources au format Markdown."""

    return chat(client, MODEL_WRITER, [{"role": "user", "content": prompt}], max_tokens=1000, temperature=0.2)


def generate_title(client, theme, article_content):
    """Génère un titre SEO optimisé via Claude Haiku."""
    prompt = f"""Génère UN titre pour cet article de blog sur "{theme['name']}".

CRITÈRES DU TITRE :
- Maximum 65 caractères (pour le SEO Google)
- Contient le mot-clé principal du domaine
- Donne envie de cliquer
- Informatif : le lecteur sait de quoi parle l'article
- Optimiste sans être racoleur
- PAS de tiret cadratin, pas d'emoji, pas de guillemets autour

Début de l'article :
{article_content[:800]}

Réponds UNIQUEMENT avec le titre, sans guillemets, sans ponctuation finale."""

    result = chat(client, MODEL_LIGHT, [{"role": "user", "content": prompt}], max_tokens=100, temperature=0.6)
    title = result.strip().strip('"').strip("'").strip("\u00ab").strip("\u00bb").strip("*").strip()
    # Supprimer un éventuel point final
    if title.endswith("."):
        title = title[:-1]
    return title


def generate_meta_description(client, article_content):
    """Génère une meta description SEO via Claude Haiku."""
    prompt = f"""Génère une meta description SEO pour cet article de blog.

CRITÈRES :
- Entre 130 et 155 caractères exactement
- Résume le contenu principal de l'article
- Contient les mots-clés importants naturellement
- Donne envie de cliquer depuis les résultats Google
- PAS de tiret cadratin, pas d'emoji

Article :
{article_content[:1200]}

Réponds UNIQUEMENT avec la meta description, rien d'autre."""

    return chat(client, MODEL_LIGHT, [{"role": "user", "content": prompt}], max_tokens=200, temperature=0.5).strip()


def extract_tags(client, theme, article_content):
    """Extrait des tags SEO pertinents via Claude Haiku."""
    prompt = f"""Génère 5 à 7 tags SEO pertinents pour cet article sur {theme['name']}.

CRITÈRES :
- En minuscules, sans #
- Mélange de termes généraux (le domaine) et spécifiques (sujets de l'article)
- Inclus le nom du domaine principal
- Les tags doivent correspondre à des recherches que feraient les lecteurs
- Séparés par des virgules

Article :
{article_content[:1000]}

Réponds UNIQUEMENT avec les tags séparés par des virgules."""

    result = chat(client, MODEL_LIGHT, [{"role": "user", "content": prompt}], max_tokens=150, temperature=0.4)
    tags = [tag.strip().lower() for tag in result.strip().split(",") if tag.strip()]
    return tags[:7]


def clean_ai_patterns(text):
    """Supprime les patterns typiques de texte généré par IA."""
    # Remplacer les tirets cadratins et demi-cadratins
    text = text.replace(" \u2014 ", ", ")
    text = text.replace(" \u2013 ", ", ")
    text = text.replace("\u2014", ", ")
    text = text.replace("\u2013", ", ")
    # Supprimer les emojis
    text = re.sub(
        '[\U0001F300-\U0001F9FF\U00002702-\U000027B0\U0000FE00-\U0000FE0F'
        '\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF'
        '\U0000200D\U00002B50]+',
        '', text
    )
    # Supprimer les doubles espaces résiduels
    text = re.sub(r'  +', ' ', text)
    return text


def create_markdown_file(today, theme, title, summary, tags, content, sources_section):
    """Crée le fichier Markdown final avec front matter Hugo optimisé SEO."""
    date_str = today.strftime("%Y-%m-%d")
    day_name = WEEKDAY_NAMES[today.weekday()]
    slug = f"{date_str}-{day_name}-{theme['slug']}"

    tags_str = json.dumps(tags, ensure_ascii=False)
    safe_title = title.replace('"', '\\"')
    safe_summary = summary.replace('"', '\\"')

    front_matter = f"""---
title: "{safe_title}"
date: {date_str}T08:00:00+01:00
draft: false
slug: "{slug}"
description: "{safe_summary}"
summary: "{safe_summary}"
author: "Nova"
categories: ["{theme['name']}"]
tags: {tags_str}
sources_verified: true
seo_title: "{safe_title}"
---

"""

    # Assembler le contenu final : article + sources
    full_content = content.strip()
    if sources_section:
        full_content += "\n\n---\n\n## Sources\n\n" + sources_section.strip()

    filepath = f"content/posts/{slug}.md"
    os.makedirs("content/posts", exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front_matter + full_content + "\n")

    return filepath


def main():
    # Vérifier la clé API
    if not os.environ.get("MAMMOUTH_API_KEY"):
        print("[Nova] Erreur : MAMMOUTH_API_KEY non definie.")
        sys.exit(1)

    client = get_client()
    today, theme = get_today_theme()

    print(f"[Nova] === GENERATION ARTICLE ===")
    print(f"[Nova] Theme : {theme['name']}")
    print(f"[Nova] Date  : {today.isoformat()} ({WEEKDAY_NAMES[today.weekday()]})")
    print(f"[Nova] Angle : {theme['description']}")
    print()

    # Étape 1 : Recherche large multi-requêtes
    print(f"[Nova] ETAPE 1/6 - Recherche d'actualites ({MODEL_SEARCH})...")
    research = search_news(client, today, theme)
    news_items = research.get("news", [])
    print(f"[Nova] => {len(news_items)} actualites uniques trouvees")

    if len(news_items) == 0:
        print("[Nova] Erreur : aucune actualite trouvee apres recherche.")
        sys.exit(1)

    # Limiter à 5 actualités max pour un article cohérent
    news_items = news_items[:5]
    print(f"[Nova] => {len(news_items)} actualites selectionnees pour l'article")
    for n in news_items:
        print(f"[Nova]   - {n.get('title', '?')[:80]}")
    print()

    # Étape 2 : Approfondissement
    print(f"[Nova] ETAPE 2/6 - Approfondissement ({MODEL_SEARCH})...")
    enriched_news = deepen_research(client, today, theme, news_items)
    enriched_count = sum(1 for n in enriched_news if "enrichment" in n)
    print(f"[Nova] => {enriched_count}/{len(enriched_news)} actualites enrichies")
    print()

    # Étape 3 : Rédaction
    print(f"[Nova] ETAPE 3/6 - Redaction de l'article ({MODEL_WRITER})...")
    content = write_article(client, today, theme, enriched_news)
    word_count = len(content.split())
    print(f"[Nova] => Article redige ({word_count} mots)")
    print()

    # Étape 4 : Fact-checking
    print(f"[Nova] ETAPE 4/6 - Fact-checking et verification des liens ({MODEL_CHECKER})...")
    content = fact_check_article(client, theme, content)
    content = clean_ai_patterns(content)
    print(f"[Nova] => Article verifie et nettoye")
    print()

    # Étape 5 : Compilation des sources
    print(f"[Nova] ETAPE 5/6 - Compilation des sources ({MODEL_WRITER})...")
    sources_section = compile_sources(client, content, enriched_news)
    sources_section = clean_ai_patterns(sources_section)
    source_count = sources_section.count("- [")
    print(f"[Nova] => {source_count} sources compilees")
    print()

    # Étape 6 : SEO (titre, meta, tags)
    print(f"[Nova] ETAPE 6/6 - Optimisation SEO ({MODEL_LIGHT})...")
    title = clean_ai_patterns(generate_title(client, theme, content))
    summary = clean_ai_patterns(generate_meta_description(client, content))
    tags = extract_tags(client, theme, content)
    print(f"[Nova] => Titre : {title}")
    print(f"[Nova] => Meta  : {summary[:80]}...")
    print(f"[Nova] => Tags  : {', '.join(tags)}")
    print()

    # Créer le fichier
    filepath = create_markdown_file(today, theme, title, summary, tags, content, sources_section)

    # Résumé final
    final_word_count = len(content.split())
    print(f"[Nova] === ARTICLE GENERE ===")
    print(f"[Nova] Fichier   : {filepath}")
    print(f"[Nova] Titre     : {title}")
    print(f"[Nova] Categorie : {theme['name']}")
    print(f"[Nova] Mots      : ~{final_word_count}")
    print(f"[Nova] Sources   : {source_count}")
    print(f"[Nova] Tags      : {', '.join(tags)}")
    print(f"[Nova] Pipeline  : 3x {MODEL_SEARCH} + 2x {MODEL_WRITER} + {MODEL_LIGHT}")

    # Exporter pour GitHub Actions
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        day_name = WEEKDAY_NAMES[today.weekday()]
        with open(github_output, "a") as f:
            f.write(f"article_date={today.isoformat()}\n")
            f.write(f"article_day={day_name}\n")
            f.write(f"article_theme={theme['name']}\n")

    return filepath


if __name__ == "__main__":
    main()
