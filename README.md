#  Generative Algorithmic Art with Language Models

Un projet explorant l'utilisation de modèles de langage pour générer de l'art algorithmique sous forme de fichiers SVG et G-code.

## Description

Ce projet vise à combiner l'art algorithmique historique (Vera Molnar, Sol LeWitt) avec les dernières avancées en IA générative. L'objectif est d'utiliser des modèles de langage pour générer directement des œuvres d'art sous forme de code (SVG pour l'art vectoriel, G-code pour les tables traçantes).

##  Fonctionnalités

- **Génération d'art algorithmique** via des modèles de langage
- **Support multi-format** : SVG (art vectoriel) et G-code (pen plotter/CNC)
- **Validation automatique** des œuvres générées
- **Intégration pen plotter** pour matérialisation physique
- **Interface en ligne de commande** complète

##  Installation

### Prérequis
- Python 3.9+
- Git
- (Optionnel) Pen plotter (AxiDraw, DIY)

### Installation des dépendances
```bash
# Cloner le dépôt
git clone https://github.com/votre-username/generative-art-ai.git
cd generative-art-ai

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# environnemnet
source activate
conda activate generative-art