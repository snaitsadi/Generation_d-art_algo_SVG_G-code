"""
Module pour la préparation des données SVG et G-code
"""
import os
import re
import random
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict
import svgwrite
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class Artwork:
    """Classe pour représenter une œuvre d'art algorithmique"""
    id: str
    format_type: str  # "svg" ou "gcode"
    content: str
    metadata: Dict
    file_path: str
    
class DataPreparator:
    """Prépare les données d'entraînement"""
    
    def __init__(self, config):
        self.config = config
        self.artworks = []
        
    def load_svg_files(self, directory: str) -> List[Artwork]:
        """Charge tous les fichiers SVG d'un répertoire"""
        svg_files = []
        
        for file_path in Path(directory).glob("**/*.svg"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Nettoyer le SVG
                cleaned_content = self._clean_svg(content)
                
                # Extraire les métadonnées
                metadata = self._extract_svg_metadata(cleaned_content)
                
                artwork = Artwork(
                    id=f"svg_{Path(file_path).stem}",
                    format_type="svg",
                    content=cleaned_content,
                    metadata=metadata,
                    file_path=str(file_path)
                )
                
                svg_files.append(artwork)
                
            except Exception as e:
                print(f"Erreur lors du chargement de {file_path}: {e}")
                
        return svg_files
    
    def load_gcode_files(self, directory: str) -> List[Artwork]:
        """Charge tous les fichiers G-code d'un répertoire"""
        gcode_files = []
        
        for file_path in Path(directory).glob("**/*.gcode"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Nettoyer le G-code
                cleaned_content = self._clean_gcode(content)
                
                # Extraire les métadonnées
                metadata = self._extract_gcode_metadata(cleaned_content)
                
                artwork = Artwork(
                    id=f"gcode_{Path(file_path).stem}",
                    format_type="gcode",
                    content=cleaned_content,
                    metadata=metadata,
                    file_path=str(file_path)
                )
                
                gcode_files.append(artwork)
                
            except Exception as e:
                print(f"Erreur lors du chargement de {file_path}: {e}")
                
        return gcode_files
    
    def _clean_svg(self, svg_content: str) -> str:
        """Nettoie et normalise le contenu SVG"""
        # Supprimer les commentaires
        svg_content = re.sub(r'<!--.*?-->', '', svg_content, flags=re.DOTALL)
        
        # Supprimer les espaces multiples
        svg_content = re.sub(r'\s+', ' ', svg_content)
        
        # Standardiser les guillemets
        svg_content = svg_content.replace("'", '"')
        
        # Supprimer les déclarations XML inutiles
        if svg_content.startswith('<?xml'):
            # Garder seulement la partie après ?>
            parts = svg_content.split('?>', 1)
            if len(parts) > 1:
                svg_content = parts[1].strip()
        
        # S'assurer que le SVG a une balise racine
        if not svg_content.strip().startswith('<svg'):
            svg_content = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">\n{svg_content}\n</svg>'
        
        return svg_content.strip()
    
    def _clean_gcode(self, gcode_content: str) -> str:
        """Nettoie et normalise le contenu G-code"""
        lines = []
        
        for line in gcode_content.split('\n'):
            line = line.strip()
            
            # Supprimer les commentaires
            if ';' in line:
                line = line.split(';')[0].strip()
            
            # Ignorer les lignes vides
            if not line:
                continue
                
            # Normaliser les espaces
            line = ' '.join(line.split())
            
            # Convertir en majuscules pour la consistance
            line = line.upper()
            
            lines.append(line)
        
        return '\n'.join(lines)
    
    def _extract_svg_metadata(self, svg_content: str) -> Dict:
        """Extrait les métadonnées d'un SVG"""
        metadata = {
            "element_count": 0,
            "has_path": False,
            "has_circle": False,
            "has_rect": False,
            "has_line": False,
            "has_polygon": False,
            "width": 800,
            "height": 600
        }
        
        try:
            root = ET.fromstring(svg_content)
            
            # Compter les éléments
            elements = list(root.iter())
            metadata["element_count"] = len(elements)
            
            # Vérifier les types d'éléments
            for elem in elements:
                tag = elem.tag.split('}')[-1]  # Enlever le namespace
                if tag == 'path':
                    metadata["has_path"] = True
                elif tag == 'circle':
                    metadata["has_circle"] = True
                elif tag == 'rect':
                    metadata["has_rect"] = True
                elif tag == 'line':
                    metadata["has_line"] = True
                elif tag == 'polygon':
                    metadata["has_polygon"] = True
            
            # Extraire les dimensions
            if 'viewBox' in root.attrib:
                viewbox = root.attrib['viewBox'].split()
                if len(viewbox) >= 4:
                    metadata["width"] = float(viewbox[2])
                    metadata["height"] = float(viewbox[3])
            
        except Exception:
            pass
        
        return metadata
    
    def _extract_gcode_metadata(self, gcode_content: str) -> Dict:
        """Extrait les métadonnées d'un G-code"""
        metadata = {
            "line_count": 0,
            "has_g0": False,
            "has_g1": False,
            "has_g2": False,
            "has_g3": False,
            "max_x": 0,
            "max_y": 0,
            "min_x": 0,
            "min_y": 0
        }
        
        lines = gcode_content.split('\n')
        metadata["line_count"] = len(lines)
        
        # Analyser les commandes
        for line in lines:
            if 'G0' in line:
                metadata["has_g0"] = True
            if 'G1' in line:
                metadata["has_g1"] = True
            if 'G2' in line:
                metadata["has_g2"] = True
            if 'G3' in line:
                metadata["has_g3"] = True
            
            # Extraire les coordonnées (simplifié)
            if 'X' in line and 'Y' in line:
                try:
                    x_part = line.split('X')[1].split()[0]
                    y_part = line.split('Y')[1].split()[0]
                    x = float(x_part)
                    y = float(y_part)
                    
                    metadata["max_x"] = max(metadata["max_x"], x)
                    metadata["max_y"] = max(metadata["max_y"], y)
                    metadata["min_x"] = min(metadata["min_x"], x)
                    metadata["min_y"] = min(metadata["min_y"], y)
                except:
                    pass
        
        return metadata
    
    def create_synthetic_dataset(self, num_samples: int = 100) -> Tuple[List[Artwork], List[Artwork]]:
        """Crée un dataset synthétique d'art algorithmique"""
        svg_artworks = []
        gcode_artworks = []
        
        print(f"Création de {num_samples} échantillons synthétiques...")
        
        for i in range(num_samples):
            # Générer un SVG aléatoire
            svg_content = self._generate_random_svg(f"synth_{i}")
            svg_art = Artwork(
                id=f"synth_svg_{i:04d}",
                format_type="svg",
                content=svg_content,
                metadata={"synthetic": True, "complexity": random.uniform(0.1, 1.0)},
                file_path=f"data/raw/svg/synth_{i:04d}.svg"
            )
            svg_artworks.append(svg_art)
            
            # Générer un G-code correspondant
            gcode_content = self._generate_random_gcode(f"synth_{i}")
            gcode_art = Artwork(
                id=f"synth_gcode_{i:04d}",
                format_type="gcode",
                content=gcode_content,
                metadata={"synthetic": True, "complexity": random.uniform(0.1, 1.0)},
                file_path=f"data/raw/gcode/synth_{i:04d}.gcode"
            )
            gcode_artworks.append(gcode_art)
        
        return svg_artworks, gcode_artworks
    
    def _generate_random_svg(self, art_id: str) -> str:
        """Génère un SVG algorithmique aléatoire"""
        width = random.randint(600, 1200)
        height = random.randint(400, 800)
        
        dwg = svgwrite.Drawing(size=(f"{width}px", f"{height}px"))
        
        # Fond
        dwg.add(dwg.rect(
            insert=(0, 0),
            size=(f"{width}px", f"{height}px"),
            fill=f"rgb({random.randint(200, 255)}, {random.randint(200, 255)}, {random.randint(200, 255)})"
        ))
        
        # Générer des formes algorithmiques
        num_shapes = random.randint(10, 50)
        
        for _ in range(num_shapes):
            shape_type = random.choice(['circle', 'rect', 'line', 'polygon', 'path'])
            
            if shape_type == 'circle':
                dwg.add(dwg.circle(
                    center=(random.randint(50, width-50), random.randint(50, height-50)),
                    r=random.randint(10, min(width, height)//4),
                    fill='none',
                    stroke=f"rgb({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)})",
                    stroke_width=random.uniform(0.5, 5),
                    opacity=random.uniform(0.3, 1.0)
                ))
                
            elif shape_type == 'rect':
                dwg.add(dwg.rect(
                    insert=(random.randint(0, width-100), random.randint(0, height-100)),
                    size=(random.randint(20, 200), random.randint(20, 200)),
                    fill='none',
                    stroke=f"rgb({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)})",
                    stroke_width=random.uniform(0.5, 5),
                    transform=f"rotate({random.randint(0, 360)} {random.randint(0, width)} {random.randint(0, height)})"
                ))
                
            elif shape_type == 'line':
                for _ in range(random.randint(3, 10)):
                    dwg.add(dwg.line(
                        start=(random.randint(0, width), random.randint(0, height)),
                        end=(random.randint(0, width), random.randint(0, height)),
                        stroke=f"rgb({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)})",
                        stroke_width=random.uniform(0.5, 3)
                    ))
                    
            elif shape_type == 'polygon':
                points = []
                for _ in range(random.randint(3, 8)):
                    points.append((random.randint(0, width), random.randint(0, height)))
                dwg.add(dwg.polygon(
                    points=points,
                    fill='none',
                    stroke=f"rgb({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)})",
                    stroke_width=random.uniform(0.5, 4)
                ))
                
            elif shape_type == 'path':
                # Générer un chemin simple
                path_data = f"M{random.randint(0, width)},{random.randint(0, height)} "
                for _ in range(random.randint(3, 7)):
                    cmd = random.choice(['L', 'Q', 'C'])
                    if cmd == 'L':
                        path_data += f"L{random.randint(0, width)},{random.randint(0, height)} "
                    elif cmd == 'Q':
                        path_data += f"Q{random.randint(0, width)},{random.randint(0, height)} {random.randint(0, width)},{random.randint(0, height)} "
                    elif cmd == 'C':
                        path_data += f"C{random.randint(0, width)},{random.randint(0, height)} {random.randint(0, width)},{random.randint(0, height)} {random.randint(0, width)},{random.randint(0, height)} "
                
                dwg.add(dwg.path(
                    d=path_data.strip(),
                    fill='none',
                    stroke=f"rgb({random.randint(0, 255)}, {random.randint(0, 255)}, {random.randint(0, 255)})",
                    stroke_width=random.uniform(0.5, 3)
                ))
        
        return dwg.tostring()
    
    def _generate_random_gcode(self, art_id: str) -> str:
        """Génère un G-code algorithmique aléatoire"""
        lines = [
            "; G-code généré algorithmiquement",
            "; Art ID: " + art_id,
            "G21 ; Unités en mm",
            "G90 ; Positionnement absolu",
            "G0 Z5 ; Lever le stylo",
            f"G0 X0 Y0 ; Aller à l'origine"
        ]
        
        # Générer des mouvements algorithmiques
        num_moves = random.randint(20, 100)
        current_x, current_y = 0, 0
        
        for i in range(num_moves):
            # Choisir un type de mouvement
            move_type = random.choice(['line', 'arc', 'jump'])
            
            if move_type == 'line':
                # Mouvement linéaire (G1)
                target_x = random.randint(0, 300)
                target_y = random.randint(0, 210)
                
                # Baisser le stylo
                lines.append("G1 Z0 F100 ; Baisser le stylo")
                
                # Dessiner la ligne
                lines.append(f"G1 X{target_x} Y{target_y} F500 ; Dessiner")
                
                current_x, current_y = target_x, target_y
                
            elif move_type == 'arc':
                # Arc (G2/G3)
                target_x = random.randint(0, 300)
                target_y = random.randint(0, 210)
                offset_x = random.randint(-50, 50)
                offset_y = random.randint(-50, 50)
                direction = random.choice([2, 3])  # G2 ou G3
                
                lines.append("G1 Z0 F100 ; Baisser le stylo")
                lines.append(f"G{direction} X{target_x} Y{target_y} I{offset_x} J{offset_y} F300 ; Arc")
                
                current_x, current_y = target_x, target_y
                
            elif move_type == 'jump':
                # Saut sans dessiner (G0)
                lines.append("G0 Z5 ; Lever le stylo")
                
                target_x = random.randint(0, 300)
                target_y = random.randint(0, 210)
                lines.append(f"G0 X{target_x} Y{target_y} F1000 ; Sauter")
                
                current_x, current_y = target_x, target_y
            
            # Varier la vitesse parfois
            if random.random() < 0.1:
                lines.append(f"F{random.randint(200, 1000)} ; Changer vitesse")
        
        # Fin du programme
        lines.append("G0 Z5 ; Lever le stylo")
        lines.append("G0 X0 Y0 ; Retour à l'origine")
        lines.append("M2 ; Fin du programme")
        
        return '\n'.join(lines)
    
    def save_dataset(self, artworks: List[Artwork], output_dir: str):
        """Sauvegarde le dataset préparé"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder chaque œuvre
        for art in artworks:
            file_path = output_path / f"{art.id}.{art.format_type}"
            
            # Sauvegarder le contenu
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(art.content)
            
            # Sauvegarder les métadonnées
            meta_path = output_path / f"{art.id}.json"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "id": art.id,
                    "format_type": art.format_type,
                    "metadata": art.metadata,
                    "file_path": str(file_path)
                }, f, indent=2)
        
        # Sauvegarder l'index global
        index = [{
            "id": art.id,
            "format_type": art.format_type,
            "metadata": art.metadata,
            "file_path": str(output_path / f"{art.id}.{art.format_type}")
        } for art in artworks]
        
        with open(output_path / "dataset_index.json", 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)
        
        print(f"Dataset sauvegardé dans {output_dir} avec {len(artworks)} œuvres")