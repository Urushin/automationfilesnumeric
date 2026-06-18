# AutomatisationNumericFiles

Système d'automatisation pour générer des designs de découpe laser et les publier sur Etsy.

## 🎯 Fonctionnalités

- **Scraping Etsy RSS** : Récupère automatiquement les produits tendance (fichiers SVG/DXF pour découpe laser)
- **Banque d'idées** : Affiche les produits scrapés avec images, titres, descriptions et scores de tendance
- **Génération IA** : Crée des designs vectoriels (SVG) similaires aux tendances via Google AI Studio
- **Pipeline automatisé** : Vectorisation, conversion CAD, PDF, upscaling, mockups
- **SEO bilingue** : Génération automatique de fiches produits FR/EN
- **Publication Etsy** : Publication directe sur Etsy avec upload automatique des fichiers

## 🏗️ Architecture

```
AutomatisationNumericFiles/
├── backend/                 # API FastAPI (Python)
│   ├── app/
│   │   ├── routers/        # Endpoints API
│   │   ├── services/       # Logique métier (scraper, générateur, SEO)
│   │   └── models.py       # Modèles SQLAlchemy
│   └── storage/            # Fichiers générés (SVG, DXF, PDF, images)
├── frontend/               # Interface Next.js (TypeScript)
│   ├── app/
│   │   ├── page.tsx        # Création de designs
│   │   ├── trends/         # Banque d'idées Etsy
│   │   └── review/         # Révision et publication
│   └── components/
└── .gitignore             # Fichiers exclus de Git
```

## 📦 Installation

### Prérequis
- Python 3.9+
- Node.js 18+
- SQLite (inclus avec Python)

### Backend

```bash
cd backend

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement (optionnel)
cp .env.example .env
# Éditer .env avec vos clés API (OpenAI, Etsy, etc.)

# Lancer le serveur
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend

```bash
cd frontend

# Installer les dépendances
npm install

# Configurer l'URL du backend (optionnel)
# Créer un fichier .env.local avec :
# NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000

# Lancer le serveur de développement
npm run dev
```

## 🚀 Utilisation

1. **Accéder à l'application** : http://localhost:3000
2. **Explorer les tendances** : Aller dans "Tendances" pour voir les produits Etsy scrapés
3. **Créer un design** : Cliquer sur "Créer similaire" sur une tendance, ou entrer un thème
4. **Réviser** : Modifier titres, descriptions, tags avant publication
5. **Publier** : Publier directement sur Etsy (nécessite connexion OAuth)

## 🔧 Configuration

### Variables d'environnement Backend (.env)

```env
# APIs (optionnel mais recommandé)
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
GEMINI_API_KEY=...

# Etsy OAuth (pour publication réelle)
ETSY_CLIENT_ID=...
ETSY_CLIENT_SECRET=...
ETSY_OAUTH_TOKEN=...

# Outils (optionnel)
POTRACE_PATH=potrace
INKSCAPE_PATH=inkscape
```

### Variables d'environnement Frontend (.env.local)

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## 📊 Base de données

Le projet utilise SQLite pour stocker :
- `ideas_bank` : Produits Etsy scrapés
- `creations` : Designs générés
- `settings` : Configuration utilisateur

Les migrations sont automatiques au démarrage du backend.

## 🧪 Tests

```bash
# Backend
cd backend
python -m pytest tests/

# Frontend
cd frontend
npm test
```

## 📝 Licence

Projet privé - Tous droits réservés

## 🤝 Contribution

Ce projet est en développement interne. Contacter le propriétaire pour toute contribution.

---

**Note** : Les fichiers sensibles (.env, bases de données, clés API) sont automatiquement exclus de Git via `.gitignore`.
