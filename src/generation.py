"""
Module pour la génération d'œuvres d'art
"""
import torch
from transformers import GPT2Tokenizer, GPT2LMHeadModel
from typing import List, Dict, Optional
import random
import re
from pathlib import Path
import json

class ArtGenerator:
    """Générateur d'art algorithmique"""
    
    def __init__(self, model_dir: str, config):
        self.config = config
        self.model_dir = Path(model_dir)
        
        # Charger le tokenizer et le modèle
        self.tokenizer = GPT2Tokenizer.from_pretrained(str(self.model_dir))
        self.model = GPT2LMHeadModel.from_pretrained(str(self.model_dir))
        
        # Configurer le device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        # Mode évaluation
        self.model.eval()
        
    def generate_svg(self, 
                    prompt: str = "<svg",
                    max_length: int = 2000,
                    temperature: float = 0.9,
                    top_p: float = 0.95,
                    num_return_sequences: int = 1) -> List[str]:
        """Génère des œuvres SVG"""
        
        # Préparer le prompt
        if not prompt.strip().startswith('<svg'):
            prompt = f'<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">\n{prompt}'
        
        print(f"Génération SVG avec prompt: {prompt[:100]}...")
        
        # Tokeniser le prompt
        inputs = self.tokenizer.encode(prompt, return_tensors='pt').to(self.device)
        
        # Générer
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                top_k=self.config.TOP_K,
                repetition_penalty=self.config.REPETITION_PENALTY,
                do_sample=True,
                num_return_sequences=num_return_sequences,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Décoder les résultats
        generated_svgs = []
        for i, output in enumerate(outputs):
            generated_text = self.tokenizer.decode(output, skip_special_tokens=True)
            
            # Nettoyer le résultat
            cleaned_svg = self._clean_generated_svg(generated_text)
            generated_svgs.append(cleaned_svg)
            
            print(f"Génération {i+1}: {len(cleaned_svg)} caractères")
        
        return generated_svgs
    
    def generate_gcode(self,
                      prompt: str = "G21",
                      max_length: int = 1000,
                      temperature: float = 0.8,
                      num_return_sequences: int = 1) -> List[str]:
        """Génère des œuvres G-code"""
        
        print(f"Génération G-code avec prompt: {prompt[:100]}...")
        
        # Tokeniser le prompt
        inputs = self.tokenizer.encode(prompt, return_tensors='pt').to(self.device)
        
        # Générer
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_length=max_length,
                temperature=temperature,
                top_p=self.config.TOP_P,
                top_k=self.config.TOP_K,
                repetition_penalty=self.config.REPETITION_PENALTY,
                do_sample=True,
                num_return_sequences=num_return_sequences,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Décoder les résultats
        generated_gcodes = []
        for i, output in enumerate(outputs):
            generated_text = self.tokenizer.decode(output, skip_special_tokens=True)
            
            # Nettoyer le résultat
            cleaned_gcode = self._clean_generated_gcode(generated_text)
            generated_gcodes.append(cleaned_gcode)
            
            print(f"Génération {i+1}: {len(cleaned_gcode.splitlines())} lignes")
        
        return generated_gcodes
    
    def generate_conditional(self,
                           format_type: str = "svg",
                           style_prompt: str = "",
                           constraints: Optional[Dict] = None) -> str:
        """Génère avec des contraintes spécifiques"""
        
        # Construire le prompt conditionnel
        if format_type == "svg":
            base_prompt = self._build_svg_prompt(style_prompt, constraints)
            return self.generate_svg(base_prompt)[0]
        else:
            base_prompt = self._build_gcode_prompt(style_prompt, constraints)
            return self.generate_gcode(base_prompt)[0]
    
    def _clean_generated_svg(self, svg_text: str) -> str:
        """Nettoie le SVG généré"""
        
        # Trouver la première balise <svg
        start_idx = svg_text.find('<svg')
        if start_idx == -1:
            # Si pas de balise svg, en créer une
            svg_text = f'<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">\n{svg_text}\n</svg>'
            start_idx = 0
        
        # Trouver la dernière balise </svg>
        end_idx = svg_text.rfind('</svg>')
        if end_idx == -1:
            # Ajouter la balise fermante
            svg_text = svg_text[start_idx:] + '\n</svg>'
        else:
            # Extraire seulement la partie SVG valide
            svg_text = svg_text[start_idx:end_idx + 6]  # +6 pour inclure </svg>
        
        # Supprimer les balises invalides ou incomplètes
        lines = []
        for line in svg_text.split('\n'):
            line = line.strip()
            if line:
                # Vérifier les balises ouvrantes/fermantes
                open_tags = re.findall(r'<(\w+)[^>]*>', line)
                close_tags = re.findall(r'</(\w+)>', line)
                
                # Filtrer les lignes avec des balises manifestement incorrectes
                if '<|' not in line and '|>' not in line:
                    lines.append(line)
        
        cleaned_svg = '\n'.join(lines)
        
        # Vérifier que le SVG a au moins une forme
        if not re.search(r'<(circle|rect|line|polygon|path|ellipse)', cleaned_svg):
            # Ajouter une forme par défaut
            cleaned_svg = cleaned_svg.replace(
                '</svg>',
                '<circle cx="400" cy="300" r="50" fill="red" />\n</svg>'
            )
        
        return cleaned_svg
    
    def _clean_generated_gcode(self, gcode_text: str) -> str:
        """Nettoie le G-code généré"""
        
        # Supprimer tout avant la première commande G
        lines = gcode_text.split('\n')
        cleaned_lines = []
        
        found_g_command = False
        for line in lines:
            line = line.strip().upper()
            
            if not line:
                continue
            
            # Vérifier que c'est une commande valide
            if re.match(r'^[GM][0-9]', line):
                found_g_command = True
            
            if found_g_command or line.startswith(';'):
                # Nettoyer la ligne
                line = re.sub(r'\s+', ' ', line)
                cleaned_lines.append(line)
        
        # S'assurer d'avoir les commandes essentielles
        if not any('G21' in line for line in cleaned_lines):
            cleaned_lines.insert(0, 'G21 ; Unités en mm')
        
        if not any('G90' in line for line in cleaned_lines):
            cleaned_lines.insert(1, 'G90 ; Positionnement absolu')
        
        # Ajouter la fin de programme si manquante
        if not any(line.startswith('M2') or line.startswith('M30') for line in cleaned_lines):
            cleaned_lines.append('M2 ; Fin du programme')
        
        return '\n'.join(cleaned_lines)
    
    def _build_svg_prompt(self, style_prompt: str, constraints: Optional[Dict]) -> str:
        """Construit un prompt conditionnel pour SVG"""
        
        base_prompt = '<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">\n'
        
        if style_prompt:
            base_prompt += f'<!-- Style: {style_prompt} -->\n'
        
        if constraints:
            if constraints.get("shapes"):
                shapes = ", ".join(constraints["shapes"])
                base_prompt += f'<!-- Utiliser les formes: {shapes} -->\n'
            
            if constraints.get("colors"):
                colors = ", ".join(constraints["colors"])
                base_prompt += f'<!-- Utiliser les couleurs: {colors} -->\n'
            
            if constraints.get("complexity"):
                complexity = constraints["complexity"]
                if complexity == "low":
                    base_prompt += '<!-- Style minimaliste, peu d\'éléments -->\n'
                elif complexity == "high":
                    base_prompt += '<!-- Style complexe, motifs détaillés -->\n'
        
        return base_prompt
    
    def _build_gcode_prompt(self, style_prompt: str, constraints: Optional[Dict]) -> str:
        """Construit un prompt conditionnel pour G-code"""
        
        base_prompt = 'G21 ; Unités en mm\nG90 ; Positionnement absolu\n'
        
        if style_prompt:
            base_prompt += f'; Style: {style_prompt}\n'
        
        if constraints:
            if constraints.get("movement_type"):
                movement = constraints["movement_type"]
                base_prompt += f'; Mouvement: {movement}\n'
            
            if constraints.get("bounds"):
                bounds = constraints["bounds"]
                base_prompt += f'; Limites: X{0}-{bounds["max_x"]}, Y{0}-{bounds["max_y"]}\n'
        
        return base_prompt
    
    def batch_generate(self,
                      num_pieces: int = 5,
                      format_type: str = "svg",
                      output_dir: Optional[str] = None) -> List[Dict]:
        """Génère plusieurs œuvres en batch"""
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        
        generated_pieces = []
        
        for i in range(num_pieces):
            print(f"Génération de l'œuvre {i+1}/{num_pieces}")
            
            if format_type == "svg":
                # Varier les prompts
                prompts = [
                    "<svg",
                    "<svg width='1000' height='800'",
                    "<!-- Geometric art -->\n<svg",
                    "<!-- Abstract composition -->\n<svg"
                ]
                prompt = random.choice(prompts)
                
                artwork = self.generate_svg(prompt)[0]
                ext = "svg"
                
            else:
                prompts = [
                    "G21",
                    "; Start drawing\nG21",
                    "G21\nG90\n; Begin artwork"
                ]
                prompt = random.choice(prompts)
                
                artwork = self.generate_gcode(prompt)[0]
                ext = "gcode"
            
            # Sauvegarder si un répertoire est spécifié
            if output_dir:
                filename = f"generated_{i+1:03d}.{ext}"
                filepath = output_path / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(artwork)
                
                # Sauvegarder les métadonnées
                metadata = {
                    "id": f"gen_{i+1:03d}",
                    "format": format_type,
                    "prompt": prompt,
                    "length": len(artwork),
                    "file_path": str(filepath)
                }
                
                metapath = output_path / f"generated_{i+1:03d}.json"
                with open(metapath, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
            
            generated_pieces.append({
                "id": i+1,
                "format": format_type,
                "content": artwork,
                "prompt": prompt
            })
        
        return generated_pieces