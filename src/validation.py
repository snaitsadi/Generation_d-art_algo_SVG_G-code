"""
Module pour la validation des œuvres générées
"""
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import json
import numpy as np
from dataclasses import dataclass
from lxml import etree

@dataclass
class ValidationResult:
    """Résultat de validation d'une œuvre"""
    is_valid: bool
    format_type: str
    errors: List[str]
    warnings: List[str]
    metrics: Dict
    repaired_content: Optional[str] = None

class ArtValidator:
    """Validateur pour les œuvres d'art algorithmique"""
    
    def __init__(self, config):
        self.config = config
        self.svg_schema = None
        
    def validate(self, content: str, format_type: str = "svg") -> ValidationResult:
        """Valide une œuvre selon son format"""
        
        if format_type == "svg":
            return self._validate_svg(content)
        elif format_type == "gcode":
            return self._validate_gcode(content)
        else:
            return ValidationResult(
                is_valid=False,
                format_type=format_type,
                errors=[f"Format non supporté: {format_type}"],
                warnings=[],
                metrics={}
            )
    
    def _validate_svg(self, svg_content: str) -> ValidationResult:
        """Valide un fichier SVG"""
        errors = []
        warnings = []
        metrics = {}
        
        try:
            # Vérification basique
            if not svg_content.strip():
                errors.append("Contenu vide")
                return ValidationResult(
                    is_valid=False,
                    format_type="svg",
                    errors=errors,
                    warnings=warnings,
                    metrics=metrics
                )
            
            # Vérifier la présence de la balise SVG
            if '<svg' not in svg_content.lower():
                errors.append("Balise SVG manquante")
            
            # Parser avec lxml pour une validation plus stricte
            try:
                parser = etree.XMLParser(recover=False)
                tree = etree.fromstring(svg_content.encode('utf-8'), parser)
                
                # Extraire des métriques
                metrics.update(self._extract_svg_metrics(tree, svg_content))
                
                # Vérifier la structure
                self._check_svg_structure(tree, errors, warnings)
                
            except etree.XMLSyntaxError as e:
                errors.append(f"Erreur de syntaxe XML: {str(e)}")
                
                # Essayer de réparer
                repaired = self._repair_svg(svg_content)
                if repaired:
                    warnings.append("SVG réparé automatiquement")
                    return ValidationResult(
                        is_valid=True,
                        format_type="svg",
                        errors=errors,
                        warnings=warnings,
                        metrics=metrics,
                        repaired_content=repaired
                    )
            
            # Vérifications supplémentaires
            self._check_svg_content(svg_content, errors, warnings)
            
        except Exception as e:
            errors.append(f"Erreur lors de la validation: {str(e)}")
        
        # Déterminer si valide
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            format_type="svg",
            errors=errors,
            warnings=warnings,
            metrics=metrics
        )
    
    def _validate_gcode(self, gcode_content: str) -> ValidationResult:
        """Valide un fichier G-code"""
        errors = []
        warnings = []
        metrics = {}
        
        try:
            lines = gcode_content.strip().split('\n')
            
            if not lines:
                errors.append("Contenu vide")
                return ValidationResult(
                    is_valid=False,
                    format_type="gcode",
                    errors=errors,
                    warnings=warnings,
                    metrics=metrics
                )
            
            # Vérifications de base
            essential_commands = ['G21', 'G90']
            missing_essentials = []
            
            for cmd in essential_commands:
                if not any(cmd in line for line in lines):
                    missing_essentials.append(cmd)
            
            if missing_essentials:
                warnings.append(f"Commandes essentielles manquantes: {missing_essentials}")
            
            # Analyser les commandes
            commands = []
            pen_up_count = 0
            pen_down_count = 0
            coordinates = []
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith(';'):
                    continue
                
                # Extraire la commande
                parts = line.split(';')[0].strip().split()
                if not parts:
                    continue
                
                command = parts[0].upper()
                commands.append(command)
                
                # Vérifier les commandes de stylo
                if 'Z' in line:
                    try:
                        z_match = re.search(r'Z\s*([-+]?\d*\.?\d+)', line.upper())
                        if z_match:
                            z_value = float(z_match.group(1))
                            if z_value > 2:  # Stylo levé
                                pen_up_count += 1
                            else:  # Stylo baissé
                                pen_down_count += 1
                    except:
                        pass
                
                # Extraire les coordonnées
                if 'X' in line and 'Y' in line:
                    try:
                        x_match = re.search(r'X\s*([-+]?\d*\.?\d+)', line.upper())
                        y_match = re.search(r'Y\s*([-+]?\d*\.?\d+)', line.upper())
                        
                        if x_match and y_match:
                            x = float(x_match.group(1))
                            y = float(y_match.group(1))
                            coordinates.append((x, y))
                    except:
                        warnings.append(f"Impossible de parser les coordonnées à la ligne {line_num}")
            
            # Calculer les métriques
            metrics = {
                "total_lines": len(lines),
                "command_count": len(commands),
                "unique_commands": len(set(commands)),
                "pen_up_count": pen_up_count,
                "pen_down_count": pen_down_count,
                "drawing_ratio": pen_down_count / max(1, pen_up_count + pen_down_count),
                "coordinate_count": len(coordinates)
            }
            
            # Vérifier les limites du plotter
            if coordinates:
                xs = [c[0] for c in coordinates]
                ys = [c[1] for c in coordinates]
                
                metrics.update({
                    "min_x": min(xs),
                    "max_x": max(xs),
                    "min_y": min(ys),
                    "max_y": max(ys),
                    "avg_x": np.mean(xs),
                    "avg_y": np.mean(ys)
                })
                
                # Vérifier les limites
                if max(xs) > self.config.PLOTTER_WIDTH_MM:
                    warnings.append(f"Dépassement largeur: {max(xs)} > {self.config.PLOTTER_WIDTH_MM}")
                
                if max(ys) > self.config.PLOTTER_HEIGHT_MM:
                    warnings.append(f"Dépassement hauteur: {max(ys)} > {self.config.PLOTTER_HEIGHT_MM}")
            
            # Vérifier les erreurs critiques
            if pen_down_count == 0:
                warnings.append("Aucun dessin détecté (stylo jamais baissé)")
            
            # Vérifier la fin du programme
            if not any(line.strip().upper().startswith(('M2', 'M30')) for line in lines):
                warnings.append("Commande de fin de programme manquante (M2 ou M30)")
            
        except Exception as e:
            errors.append(f"Erreur lors de la validation G-code: {str(e)}")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            format_type="gcode",
            errors=errors,
            warnings=warnings,
            metrics=metrics
        )
    
    def _extract_svg_metrics(self, tree: etree.Element, svg_content: str) -> Dict:
        """Extrait des métriques d'un SVG"""
        metrics = {
            "element_count": 0,
            "path_count": 0,
            "circle_count": 0,
            "rect_count": 0,
            "line_count": 0,
            "polygon_count": 0,
            "text_count": 0,
            "group_count": 0,
            "attribute_count": 0,
            "content_length": len(svg_content)
        }
        
        try:
            # Compter tous les éléments
            all_elements = list(tree.iter())
            metrics["element_count"] = len(all_elements)
            
            # Compter par type
            for elem in all_elements:
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                
                if tag == 'path':
                    metrics["path_count"] += 1
                elif tag == 'circle':
                    metrics["circle_count"] += 1
                elif tag == 'rect':
                    metrics["rect_count"] += 1
                elif tag == 'line':
                    metrics["line_count"] += 1
                elif tag == 'polygon':
                    metrics["polygon_count"] += 1
                elif tag == 'text':
                    metrics["text_count"] += 1
                elif tag == 'g':
                    metrics["group_count"] += 1
                
                # Compter les attributs
                metrics["attribute_count"] += len(elem.attrib)
            
            # Calculer la complexité
            metrics["complexity_score"] = (
                metrics["element_count"] * 0.3 +
                metrics["attribute_count"] * 0.1 +
                metrics["path_count"] * 0.4 +
                metrics["group_count"] * 0.2
            )
            
            # Extraire les couleurs
            colors = set()
            color_pattern = r'(?:fill|stroke|color)\s*[=:]\s*[\'"]([^"\']+)[\'"]'
            color_matches = re.findall(color_pattern, svg_content, re.IGNORECASE)
            colors.update(color_matches)
            
            hex_pattern = r'#([0-9a-fA-F]{3,6})'
            hex_matches = re.findall(hex_pattern, svg_content)
            colors.update([f'#{h}' for h in hex_matches])
            
            rgb_pattern = r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)'
            rgb_matches = re.findall(rgb_pattern, svg_content)
            colors.update([f'rgb({r},{g},{b})' for r, g, b in rgb_matches])
            
            metrics["color_count"] = len(colors)
            metrics["colors"] = list(colors)[:10]  # Garder seulement les 10 premiers
            
        except Exception as e:
            metrics["error"] = f"Erreur d'extraction: {str(e)}"
        
        return metrics
    
    def _check_svg_structure(self, tree: etree.Element, errors: List[str], warnings: List[str]):
        """Vérifie la structure du SVG"""
        
        # Vérifier l'élément racine
        if tree.tag != '{http://www.w3.org/2000/svg}svg':
            errors.append("L'élément racine n'est pas un SVG")
        
        # Vérifier les attributs essentiels
        if 'width' not in tree.attrib and 'viewBox' not in tree.attrib:
            warnings.append("Dimensions non spécifiées (width/height ou viewBox)")
        
        # Vérifier les éléments enfants
        child_elements = list(tree)
        if not child_elements:
            warnings.append("SVG vide (aucun élément enfant)")
        
        # Vérifier les IDs dupliqués
        id_set = set()
        for elem in tree.iter():
            if 'id' in elem.attrib:
                elem_id = elem.attrib['id']
                if elem_id in id_set:
                    warnings.append(f"ID dupliqué: {elem_id}")
                id_set.add(elem_id)
    
    def _check_svg_content(self, svg_content: str, errors: List[str], warnings: List[str]):
        """Vérifie le contenu du SVG"""
        
        # Vérifier les balises non fermées
        open_tags = re.findall(r'<(\w+)(?:\s[^>]*)?>', svg_content)
        close_tags = re.findall(r'</(\w+)>', svg_content)
        
        # Vérifier l'équilibre des balises
        for tag in set(open_tags):
            open_count = open_tags.count(tag)
            close_count = close_tags.count(tag)
            
            if open_count != close_count:
                warnings.append(f"Balise '{tag}' non équilibrée: {open_count} ouvertures, {close_count} fermetures")
        
        # Vérifier les URLs externes (peut être une sécurité)
        if 'http://' in svg_content or 'https://' in svg_content:
            warnings.append("Contient des URLs externes")
        
        # Vérifier la taille du fichier
        if len(svg_content) > 1000000:  # 1MB
            warnings.append("SVG très volumineux (>1MB)")
    
    def _repair_svg(self, svg_content: str) -> Optional[str]:
        """Tente de réparer un SVG mal formé"""
        try:
            # Essayer d'ajouter la balise SVG manquante
            if not svg_content.strip().startswith('<svg'):
                # Chercher la première balise
                lines = svg_content.split('\n')
                repaired = []
                found_start = False
                
                for line in lines:
                    stripped = line.strip()
                    if not found_start and stripped and stripped[0] == '<':
                        # Insérer la balise SVG avant la première balise
                        repaired.append('<svg xmlns="http://www.w3.org/2000/svg">')
                        found_start = True
                    repaired.append(line)
                
                if not found_start:
                    repaired.insert(0, '<svg xmlns="http://www.w3.org/2000/svg">')
                
                # Ajouter la balise fermante
                if '</svg>' not in svg_content:
                    repaired.append('</svg>')
                
                return '\n'.join(repaired)
            
            # Fermer les balises auto-fermantes mal formées
            repaired_content = re.sub(r'<(\w+)([^>]*[^/])>', r'<\1\2/>', svg_content)
            
            # Parser pour vérifier
            etree.fromstring(repaired_content.encode('utf-8'))
            
            return repaired_content
            
        except Exception:
            return None
    
    def validate_batch(self, artworks: List[Dict]) -> Dict:
        """Valide un batch d'œuvres"""
        results = {
            "total": len(artworks),
            "valid": 0,
            "invalid": 0,
            "with_warnings": 0,
            "details": [],
            "summary": {}
        }
        
        for i, art in enumerate(artworks):
            print(f"Validation {i+1}/{len(artworks)}...")
            
            validation_result = self.validate(
                art.get("content", ""),
                art.get("format", "svg")
            )
            
            result_data = {
                "id": art.get("id", i+1),
                "format": art.get("format", "svg"),
                "is_valid": validation_result.is_valid,
                "error_count": len(validation_result.errors),
                "warning_count": len(validation_result.warnings),
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "metrics": validation_result.metrics
            }
            
            results["details"].append(result_data)
            
            if validation_result.is_valid:
                results["valid"] += 1
            else:
                results["invalid"] += 1
            
            if validation_result.warnings:
                results["with_warnings"] += 1
        
        # Calculer les statistiques
        if artworks:
            results["summary"] = {
                "validity_rate": results["valid"] / results["total"],
                "avg_errors": sum(len(d["errors"]) for d in results["details"]) / results["total"],
                "avg_warnings": sum(len(d["warnings"]) for d in results["details"]) / results["total"]
            }
        
        return results
    
    def generate_validation_report(self, validation_results: Dict, output_path: str):
        """Génère un rapport de validation détaillé"""
        report = {
            "validation_summary": {
                "date": "2024-01-01",  # À remplacer avec datetime.now()
                "total_artworks": validation_results["total"],
                "valid_artworks": validation_results["valid"],
                "invalid_artworks": validation_results["invalid"],
                "validity_rate": validation_results["summary"].get("validity_rate", 0),
                "artworks_with_warnings": validation_results["with_warnings"]
            },
            "detailed_results": validation_results["details"],
            "common_issues": self._extract_common_issues(validation_results["details"]),
            "recommendations": self._generate_recommendations(validation_results)
        }
        
        # Sauvegarder le rapport
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"Rapport de validation sauvegardé: {output_path}")
        
        return report
    
    def _extract_common_issues(self, details: List[Dict]) -> Dict:
        """Extrait les problèmes communs"""
        issues = {
            "common_errors": {},
            "common_warnings": {},
            "format_specific": {
                "svg": {},
                "gcode": {}
            }
        }
        
        # Compter les erreurs
        for detail in details:
            for error in detail["errors"]:
                issues["common_errors"][error] = issues["common_errors"].get(error, 0) + 1
            
            for warning in detail["warnings"]:
                issues["common_warnings"][warning] = issues["common_warnings"].get(warning, 0) + 1
            
            # Par format
            fmt = detail["format"]
            if fmt in issues["format_specific"]:
                for error in detail["errors"]:
                    key = f"error_{error[:50]}"
                    issues["format_specific"][fmt][key] = issues["format_specific"][fmt].get(key, 0) + 1
        
        # Trier par fréquence
        issues["common_errors"] = dict(sorted(
            issues["common_errors"].items(),
            key=lambda x: x[1],
            reverse=True
        ))
        
        issues["common_warnings"] = dict(sorted(
            issues["common_warnings"].items(),
            key=lambda x: x[1],
            reverse=True
        ))
        
        return issues
    
    def _generate_recommendations(self, validation_results: Dict) -> List[str]:
        """Génère des recommandations basées sur les résultats"""
        recommendations = []
        
        validity_rate = validation_results["summary"].get("validity_rate", 0)
        
        if validity_rate < 0.5:
            recommendations.append(
                "Taux de validité faible (<50%). Considérez d'améliorer la génération ou d'ajouter plus de post-traitement."
            )
        
        # Analyser les erreurs communes
        details = validation_results["details"]
        
        # Vérifier les erreurs spécifiques
        xml_errors = sum(1 for d in details if any("XML" in e for e in d["errors"]))
        if xml_errors > 0:
            recommendations.append(
                f"{xml_errors} erreurs XML détectées. Améliorez la génération de balises."
            )
        
        # Pour G-code
        gcode_details = [d for d in details if d["format"] == "gcode"]
        if gcode_details:
            missing_end = sum(1 for d in gcode_details if any("M2" in w for w in d["warnings"]))
            if missing_end > 0:
                recommendations.append(
                    f"{missing_end} fichiers G-code sans commande de fin. Ajoutez 'M2' ou 'M30'."
                )
        
        return recommendations