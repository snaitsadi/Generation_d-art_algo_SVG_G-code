#!/usr/bin/env python3
"""
Script de génération d'œuvres d'art
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.generation import ArtGenerator
from src.validation import ArtValidator
#from config.settings import config
import argparse
import json

def generate_artworks(num_pieces=5, format_type="svg", model_dir=None, output_dir=None):
    """Génère plusieurs œuvres d'art"""
    if model_dir is None:
        model_dir = f"./models/{format_type}_model_final"
    
    if output_dir is None:
        output_dir = f"./data/generated/{format_type}"
    
    print(f"🎨 Génération de {num_pieces} œuvres {format_type.upper()}...")
    
    # Initialiser le générateur
    generator = ArtGenerator(model_dir, config)
    
    # Générer les œuvres
    artworks = generator.batch_generate(
        num_pieces=num_pieces,
        format_type=format_type,
        output_dir=output_dir
    )
    
    # Valider les œuvres générées
    validator = ArtValidator(config)
    
    for i, art in enumerate(artworks):
        validation = validator.validate(art['content'], format_type)
        
        print(f"  Artwork {i+1}:")
        print(f"    Longueur: {len(art['content'])} caractères")
        print(f"    Valide: {'✅' if validation.is_valid else '❌'}")
        
        if validation.warnings:
            print(f"    Avertissements: {len(validation.warnings)}")
    
    # Sauvegarder le rapport
    report_path = Path(output_dir) / "generation_report.json"
    with open(report_path, 'w') as f:
        json.dump({
            "count": len(artworks),
            "format": format_type,
            "model": model_dir,
            "artworks": [
                {
                    "id": art['id'],
                    "prompt": art['prompt'],
                    "length": len(art['content']),
                    "valid": validator.validate(art['content'], format_type).is_valid
                }
                for art in artworks
            ]
        }, f, indent=2)
    
    print(f"✅ Génération terminée! Rapport: {report_path}")
    return artworks

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génération d'œuvres d'art")
    parser.add_argument('--num', type=int, default=5,
                       help='Nombre d\'œuvres à générer')
    parser.add_argument('--format', choices=['svg', 'gcode'],
                       default='svg', help='Format de sortie')
    parser.add_argument('--model-dir', type=str,
                       help='Répertoire du modèle')
    parser.add_argument('--output-dir', type=str,
                       help='Répertoire de sortie')
    
    args = parser.parse_args()
    
    generate_artworks(
        num_pieces=args.num,
        format_type=args.format,
        model_dir=args.model_dir,
        output_dir=args.output_dir
    )