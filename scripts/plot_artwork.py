#!/usr/bin/env python3
"""
Script pour dessiner avec le pen plotter
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.plotter_controller import PenPlotterController
#from config.settings import config
import argparse
import time

def plot_file(filepath, simulate=False):
    """Trace un fichier avec le plotter"""
    print(f"🖨️  Préparation du tracé: {filepath}")
    
    plotter = PenPlotterController(config)
    
    if not simulate:
        # Mode réel - connexion au plotter
        if plotter.connect():
            print("✅ Plotter connecté")
        else:
            print("❌ Échec de connexion, passage en mode simulation")
            simulate = True
    
    # Lire le fichier
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Tracer selon le format
    if filepath.endswith('.svg'):
        print("  Format: SVG")
        if simulate:
            print("  [SIMULATION] Conversion SVG → G-code")
            gcode = plotter._svg_to_gcode(content)
            print(f"  [SIMULATION] {len(gcode.splitlines())} lignes G-code générées")
        else:
            plotter.plot_svg(content)
    
    elif filepath.endswith('.gcode'):
        print("  Format: G-code")
        if simulate:
            print(f"  [SIMULATION] {len(content.splitlines())} lignes à tracer")
            # Simuler le tracé
            for i, line in enumerate(content.splitlines()[:10], 1):
                if line.strip() and not line.strip().startswith(';'):
                    print(f"  [SIMULATION] Ligne {i}: {line[:50]}...")
                    time.sleep(0.1)
        else:
            plotter.plot_gcode(content)
    
    else:
        print(f"❌ Format non supporté: {filepath}")
        return
    
    if not simulate:
        plotter.disconnect()
        print("✅ Tracé terminé")
    else:
        print("✅ Simulation terminée")

def plot_test_pattern():
    """Trace un motif de test"""
    print("🖨️  Tracé du motif de test...")
    
    plotter = PenPlotterController(config)
    
    if plotter.connect():
        print("✅ Plotter connecté")
        
        # Motif de test
        plotter.home()
        
        print("  Dessin d'un motif géométrique...")
        
        # Carré
        plotter.pen_down()
        positions = [(50, 50), (150, 50), (150, 150), (50, 150), (50, 50)]
        for x, y in positions:
            plotter.move_to(x, y, speed=1000)
        
        plotter.pen_up()
        
        # Cercle (approximation avec segments)
        plotter.move_to(100, 100)
        plotter.pen_down()
        
        import math
        radius = 40
        for angle in range(0, 361, 10):
            rad = math.radians(angle)
            x = 100 + radius * math.cos(rad)
            y = 100 + radius * math.sin(rad)
            plotter.move_to(x, y, speed=800)
        
        plotter.pen_up()
        
        plotter.home()
        plotter.disconnect()
        
        print("✅ Motif de test tracé")
    else:
        print("❌ Impossible de se connecter au plotter")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Contrôle du pen plotter")
    parser.add_argument('--file', type=str,
                       help='Fichier à tracer (SVG ou G-code)')
    parser.add_argument('--test', action='store_true',
                       help='Trace un motif de test')
    parser.add_argument('--simulate', action='store_true',
                       help='Mode simulation (pas de connexion réelle)')
    parser.add_argument('--port', type=str,
                       default=config.PLOTTER_PORT,
                       help='Port série du plotter')
    
    args = parser.parse_args()
    
    # Mettre à jour le port si spécifié
    if args.port != config.PLOTTER_PORT:
        config.PLOTTER_PORT = args.port
    
    if args.file:
        plot_file(args.file, args.simulate)
    elif args.test:
        plot_test_pattern()
    else:
        parser.print_help()
        print("\n💡 Exemples:")
        print("  python plot_artwork.py --file data/generated/artwork.svg")
        print("  python plot_artwork.py --test --simulate")
        print("  python plot_artwork.py --file drawing.gcode --port /dev/ttyUSB0")