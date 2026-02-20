#!/usr/bin/env python3
"""
Script d'entraînement du modèle
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.model_training import ModelTrainer
#from config.settings import config
import argparse

def train_svg_model():
    """Entraîne un modèle pour le SVG"""
    print("🎯 Entraînement du modèle SVG...")
    trainer = ModelTrainer(config)
    
    # Préparer les données
    dataset = trainer.prepare_data(config.PROCESSED_DIR + "/svg", "svg")
    
    # Entraîner
    trainer.train(dataset['train'], dataset['test'], "svg")
    
    print("✅ Modèle SVG entraîné!")

def train_gcode_model():
    """Entraîne un modèle pour le G-code"""
    print("🎯 Entraînement du modèle G-code...")
    trainer = ModelTrainer(config)
    
    # Préparer les données
    dataset = trainer.prepare_data(config.PROCESSED_DIR + "/gcode", "gcode")
    
    # Entraîner
    trainer.train(dataset['train'], dataset['test'], "gcode")
    
    print("✅ Modèle G-code entraîné!")

def train_multi_model():
    """Entraîne un modèle multi-format"""
    print("🎯 Entraînement du modèle multi-format...")
    trainer = ModelTrainer(config)
    
    # Entraîner avec données SVG et G-code
    trainer.train_multi_format(
        config.PROCESSED_DIR + "/svg",
        config.PROCESSED_DIR + "/gcode"
    )
    
    print("✅ Modèle multi-format entraîné!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraînement des modèles")
    parser.add_argument('--model', choices=['svg', 'gcode', 'multi'],
                       default='svg', help='Type de modèle à entraîner')
    
    args = parser.parse_args()
    
    if args.model == 'svg':
        train_svg_model()
    elif args.model == 'gcode':
        train_gcode_model()
    elif args.model == 'multi':
        train_multi_model()