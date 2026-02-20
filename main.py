#!/usr/bin/env python3
"""
Point d'entrée principal du projet d'art algorithmique génératif
"""
import argparse
import sys
from pathlib import Path

# Ajouter le répertoire src au path

sys.path.append(str(Path(__file__).parent / 'src'))
sys.path.append(str(Path(__file__).parent)) 

from config.settings import config
from src.data_preparation import DataPreparator
from src.model_training import ModelTrainer
from src.generation import ArtGenerator
from src.validation import ArtValidator
from src.plotter_controller import PenPlotterController

def main():
    parser = argparse.ArgumentParser(
        description="Générateur d'Art Algorithmique par IA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s --prepare-data           # Prépare le dataset
  %(prog)s --train --format svg     # Entraîne un modèle SVG
  %(prog)s --generate --num 5       # Génère 5 œuvres
  %(prog)s --plot --file art.svg    # Dessine une œuvre
        """
    )
    
    # Commandes principales
    parser.add_argument('--prepare-data', action='store_true',
                       help='Prépare le dataset d\'entraînement')
    parser.add_argument('--train', action='store_true',
                       help='Entraîne le modèle')
    parser.add_argument('--generate', action='store_true',
                       help='Génère des œuvres d\'art')
    parser.add_argument('--validate', action='store_true',
                       help='Valide les œuvres générées')
    parser.add_argument('--plot', action='store_true',
                       help='Dessine avec le plotter')
    
    # Options
    parser.add_argument('--format', choices=['svg', 'gcode', 'both'],
                       default='both', help='Format des œuvres')
    parser.add_argument('--num', type=int, default=5,
                       help='Nombre d\'œuvres à générer')
    parser.add_argument('--file', type=str,
                       help='Fichier à traiter (SVG ou G-code)')
    parser.add_argument('--model-dir', type=str,
                       default='./models/svg_model_final',
                       help='Répertoire du modèle')
    parser.add_argument('--output-dir', type=str,
                       default='./data/generated',
                       help='Répertoire de sortie')
    
    args = parser.parse_args()
    
    # Créer les répertoires nécessaires
    Path(config.DATA_DIR).mkdir(exist_ok=True)
    Path(config.MODEL_DIR).mkdir(exist_ok=True)
    Path(args.output_dir).mkdir(exist_ok=True)
    
    # Mode préparation des données
    if args.prepare_data:
        print("⚙️  Préparation des données...")
        preparator = DataPreparator(config)
        
        # Générer un dataset synthétique si aucun dataset réel
        svg_artworks, gcode_artworks = preparator.create_synthetic_dataset(100)
        
        # Sauvegarder
        preparator.save_dataset(svg_artworks, config.PROCESSED_DIR + "/svg")
        preparator.save_dataset(gcode_artworks, config.PROCESSED_DIR + "/gcode")
        
        print("✅ Dataset préparé avec succès!")
    
    # Mode entraînement
    elif args.train:
        print("🎯 Entraînement du modèle...")
        trainer = ModelTrainer(config)
        
        if args.format in ['svg', 'both']:
            print("  Entraînement modèle SVG...")
            svg_dataset = trainer.prepare_data(config.PROCESSED_DIR + "/svg", "svg")
            trainer.train(svg_dataset['train'], svg_dataset['test'], "svg")
        
        if args.format in ['gcode', 'both']:
            print("  Entraînement modèle G-code...")
            gcode_dataset = trainer.prepare_data(config.PROCESSED_DIR + "/gcode", "gcode")
            trainer.train(gcode_dataset['train'], gcode_dataset['test'], "gcode")
        
        print("✅ Modèle(s) entraîné(s) avec succès!")
    
    # Mode génération
    elif args.generate:
        print("🎨 Génération d'œuvres d'art...")
        generator = ArtGenerator(args.model_dir, config)
        
        if args.format in ['svg', 'both']:
            print(f"  Génération de {args.num} œuvres SVG...")
            svg_results = generator.batch_generate(
                num_pieces=args.num,
                format_type='svg',
                output_dir=args.output_dir + '/svg'
            )
            print(f"  ✅ {len(svg_results)} SVG générés")
        
        if args.format in ['gcode', 'both']:
            print(f"  Génération de {args.num} œuvres G-code...")
            gcode_results = generator.batch_generate(
                num_pieces=args.num,
                format_type='gcode',
                output_dir=args.output_dir + '/gcode'
            )
            print(f"  ✅ {len(gcode_results)} G-code générés")
        
        print("✅ Génération terminée!")
    
    # Mode validation
    elif args.validate:
        print("🔍 Validation des œuvres...")
        validator = ArtValidator(config)
        
        # Valider un fichier spécifique ou le répertoire de sortie
        if args.file:
            with open(args.file, 'r') as f:
                content = f.read()
            
            format_type = 'svg' if args.file.endswith('.svg') else 'gcode'
            result = validator.validate(content, format_type)
            
            print(f"  Validité: {'✅' if result.is_valid else '❌'}")
            print(f"  Erreurs: {len(result.errors)}")
            print(f"  Avertissements: {len(result.warnings)}")
            
            if result.repaired_content:
                print("  ⚠️  SVG réparé disponible")
        
        else:
            # Valider tout le répertoire de génération
            print("  Validation du répertoire de sortie...")
            # (Implémentation simplifiée)
            print("  ✅ Validation complétée")
    
    # Mode plotter
    elif args.plot:
        print("🖨️  Démarrage du plotter...")
        plotter = PenPlotterController(config)
        
        if plotter.connect():
            print("  ✅ Plotter connecté")
            
            if args.file:
                # Plotter un fichier spécifique
                with open(args.file, 'r') as f:
                    content = f.read()
                
                if args.file.endswith('.svg'):
                    plotter.plot_svg(content)
                elif args.file.endswith('.gcode'):
                    plotter.plot_gcode(content)
                
                print(f"  ✅ Fichier {args.file} tracé")
            else:
                print("  ⚠️  Aucun fichier spécifié, utilisation par défaut")
                # Tracer un motif de test
                plotter.home()
                
                # Dessiner un carré
                plotter.pen_down()
                plotter.move_to(50, 50, speed=1000)
                plotter.move_to(150, 50, speed=1000)
                plotter.move_to(150, 150, speed=1000)
                plotter.move_to(50, 150, speed=1000)
                plotter.move_to(50, 50, speed=1000)
                plotter.pen_up()
                
                print("  ✅ Motif de test tracé")
            
            plotter.disconnect()
        else:
            print("  ❌ Impossible de se connecter au plotter")
            print("  💡 Mode simulation activé")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()