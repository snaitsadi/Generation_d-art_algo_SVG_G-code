"""
Module pour contrôler le pen plotter
"""
import serial
import time
from typing import *
#from typing import List, Optional, Tuple, Dict
from pathlib import Path
import threading
from queue import Queue
import logging

class PenPlotterController:
    """Contrôleur pour pen plotter (ex: AxiDraw, DIY)"""
    
    def __init__(self, config):
        self.config = config
        self.serial_connection = None
        self.is_connected = False
        self.is_plotting = False
        self.plotting_queue = Queue()
        self.current_position = (0, 0, 5)  # (x, y, z) en mm, z=5 stylo levé
        
        # Configuration logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("PlotterController")
        
        # Configuration matérielle
        self.max_speed = 3000  # mm/min
        self.pen_up_speed = 3000
        self.pen_down_speed = 1500
        self.pen_up_height = 5  # mm
        self.pen_down_height = 0  # mm
        
    def connect(self, port: Optional[str] = None, baudrate: int = 115200) -> bool:
        """Établit la connexion avec le plotter"""
        if port is None:
            port = self.config.PLOTTER_PORT
        
        try:
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1,
                write_timeout=1
            )
            
            # Attendre l'initialisation
            time.sleep(2)
            
            # Envoyer une commande de test
            self._send_command("G21")  # Unités en mm
            self._send_command("G90")  # Positionnement absolu
            self._send_command("G0 Z5")  # Lever le stylo
            
            # Lire la réponse
            response = self._read_response()
            self.logger.info(f"Connexion établie: {response}")
            
            self.is_connected = True
            return True
            
        except serial.SerialException as e:
            self.logger.error(f"Erreur de connexion: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Erreur inattendue: {e}")
            return False
    
    def disconnect(self):
        """Ferme la connexion avec le plotter"""
        if self.serial_connection and self.serial_connection.is_open:
            # Lever le stylo et retourner à l'origine
            self._send_command("G0 Z5")
            self._send_command("G0 X0 Y0")
            
            # Fermer la connexion
            self.serial_connection.close()
            self.is_connected = False
            self.logger.info("Déconnexion du plotter")
    
    def _send_command(self, command: str):
        """Envoie une commande G-code au plotter"""
        if not self.serial_connection:
            raise ConnectionError("Plotter non connecté")
        
        # Ajouter un retour chariot
        full_command = command.strip() + '\n'
        
        # Envoyer la commande
        self.serial_connection.write(full_command.encode())
        
        # Log
        self.logger.debug(f"Envoyé: {command}")
    
    def _read_response(self, timeout: float = 2.0) -> str:
        """Lit la réponse du plotter"""
        if not self.serial_connection:
            return ""
        
        start_time = time.time()
        response = ""
        
        while time.time() - start_time < timeout:
            if self.serial_connection.in_waiting > 0:
                line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    response += line + "\n"
                    if 'ok' in line.lower():
                        break
        
        return response.strip()
    
    def _wait_for_acknowledge(self):
        """Attend l'acquittement 'ok' du plotter"""
        response = self._read_response()
        if 'ok' not in response.lower():
            self.logger.warning(f"Pas d'acquittement: {response}")
    
    def home(self):
        """Retourne à la position d'origine"""
        if not self.is_connected:
            self.logger.error("Plotter non connecté")
            return
        
        self._send_command("G0 Z5")  # Lever le stylo
        self._send_command("G0 X0 Y0")  # Aller à l'origine
        self._wait_for_acknowledge()
        
        self.current_position = (0, 0, 5)
        self.logger.info("Retour à l'origine")
    
    def move_to(self, x: float, y: float, z: Optional[float] = None, speed: Optional[int] = None):
        """Déplace le stylo à une position spécifique"""
        if not self.is_connected:
            self.logger.error("Plotter non connecté")
            return
        
        # Construire la commande
        cmd = "G0" if z is None or z == self.pen_up_height else "G1"
        cmd_parts = [cmd]
        
        # Ajouter les coordonnées
        if x is not None:
            cmd_parts.append(f"X{x}")
            self.current_position = (x, self.current_position[1], self.current_position[2])
        
        if y is not None:
            cmd_parts.append(f"Y{y}")
            self.current_position = (self.current_position[0], y, self.current_position[2])
        
        if z is not None:
            cmd_parts.append(f"Z{z}")
            self.current_position = (self.current_position[0], self.current_position[1], z)
        
        # Ajouter la vitesse
        if speed is not None:
            cmd_parts.append(f"F{speed}")
        
        # Envoyer la commande
        command = " ".join(cmd_parts)
        self._send_command(command)
        self._wait_for_acknowledge()
    
    def pen_up(self):
        """Lève le stylo"""
        self.move_to(z=self.pen_up_height, speed=self.pen_up_speed)
        self.logger.debug("Stylo levé")
    
    def pen_down(self):
        """Baisse le stylo"""
        self.move_to(z=self.pen_down_height, speed=self.pen_down_speed)
        self.logger.debug("Stylo baissé")
    
    def plot_gcode(self, gcode_content: str, auto_start: bool = True):
        """Exécute un G-code sur le plotter"""
        if not self.is_connected:
            self.logger.error("Plotter non connecté")
            return
        
        # Parse le G-code
        commands = self._parse_gcode(gcode_content)
        
        if auto_start:
            # Démarrer le plotting
            self._execute_commands(commands)
        else:
            # Ajouter à la queue
            for cmd in commands:
                self.plotting_queue.put(cmd)
    
    def _parse_gcode(self, gcode_content: str) -> List[Tuple[str, dict]]:
        """Parse le contenu G-code en commandes"""
        commands = []
        
        for line_num, line in enumerate(gcode_content.split('\n'), 1):
            line = line.strip()
            
            # Ignorer les lignes vides et commentaires
            if not line or line.startswith(';'):
                continue
            
            # Séparer le commentaire
            if ';' in line:
                line, comment = line.split(';', 1)
                line = line.strip()
            
            # Parser la commande
            parts = line.split()
            if not parts:
                continue
            
            cmd_type = parts[0].upper()
            params = {}
            
            # Extraire les paramètres
            for part in parts[1:]:
                if len(part) > 1:
                    param_type = part[0].upper()
                    param_value = part[1:]
                    
                    try:
                        # Convertir en float si numérique
                        if param_value.replace('.', '').replace('-', '').isdigit():
                            params[param_type] = float(param_value)
                        else:
                            params[param_type] = param_value
                    except:
                        params[param_type] = param_value
            
            commands.append((cmd_type, params, line))
        
        return commands
    
    def _execute_commands(self, commands: List[Tuple[str, dict]]):
        """Exécute une liste de commandes G-code"""
        self.is_plotting = True
        
        try:
            self.logger.info(f"Début du plotting de {len(commands)} commandes")
            
            for cmd_type, params, original_cmd in commands:
                if not self.is_plotting:
                    self.logger.info("Plotting interrompu")
                    break
                
                # Traiter la commande
                if cmd_type in ['G0', 'G1']:
                    # Mouvement linéaire
                    x = params.get('X', self.current_position[0])
                    y = params.get('Y', self.current_position[1])
                    z = params.get('Z', self.current_position[2])
                    speed = params.get('F', self.max_speed)
                    
                    # Envoyer la commande
                    cmd_str = f"{cmd_type} X{x} Y{y} Z{z} F{speed}"
                    self._send_command(cmd_str)
                    self._wait_for_acknowledge()
                    
                    # Mettre à jour la position
                    self.current_position = (x, y, z)
                    
                elif cmd_type in ['G2', 'G3']:
                    # Arc de cercle
                    x = params.get('X', self.current_position[0])
                    y = params.get('Y', self.current_position[1])
                    i = params.get('I', 0)
                    j = params.get('J', 0)
                    
                    cmd_str = f"{cmd_type} X{x} Y{y} I{i} J{j}"
                    self._send_command(cmd_str)
                    self._wait_for_acknowledge()
                    
                    self.current_position = (x, y, self.current_position[2])
                    
                elif cmd_type == 'G4':
                    # Pause
                    delay = params.get('P', 0)
                    time.sleep(delay / 1000)  # Convertir ms en secondes
                    
                elif cmd_type in ['M2', 'M30']:
                    # Fin de programme
                    self.logger.info("Fin de programme détectée")
                    break
                    
                else:
                    # Commande non supportée, envoyer telle quelle
                    self._send_command(original_cmd)
                    self._wait_for_acknowledge()
                
                # Petit délai pour éviter de surcharger le plotter
                time.sleep(0.01)
            
            self.logger.info("Plotting terminé avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur pendant le plotting: {e}")
            # Lever le stylo en cas d'erreur
            self.pen_up()
        
        finally:
            self.is_plotting = False
    
    def start_plotting_thread(self):
        """Démarre un thread pour le plotting"""
        if not self.plotting_queue.empty():
            thread = threading.Thread(target=self._plotting_worker)
            thread.daemon = True
            thread.start()
            return thread
        return None
    
    def _plotting_worker(self):
        """Worker pour exécuter les commandes depuis la queue"""
        while not self.plotting_queue.empty():
            cmd = self.plotting_queue.get()
            # Exécuter la commande
            # (simplifié pour l'exemple)
            self.logger.info(f"Exécution: {cmd}")
            self.plotting_queue.task_done()
    
    def plot_svg(self, svg_content: str, output_gcode_path: Optional[str] = None):
        """Convertit un SVG en G-code et le plot"""
        # Convertir SVG en G-code
        gcode = self._svg_to_gcode(svg_content)
        
        # Sauvegarder le G-code si demandé
        if output_gcode_path:
            with open(output_gcode_path, 'w') as f:
                f.write(gcode)
            self.logger.info(f"G-code sauvegardé: {output_gcode_path}")
        
        # Plotter le G-code
        self.plot_gcode(gcode)
    
    def _svg_to_gcode(self, svg_content: str) -> str:
        """Convertit un SVG en G-code (version simplifiée)"""
        
        # Parser le SVG (simplifié)
        # Dans une version réelle, utiliserait svgpathtools ou similaire
        
        gcode_lines = [
            "; G-code généré depuis SVG",
            "G21 ; Unités en mm",
            "G90 ; Positionnement absolu",
            "G0 Z5 ; Lever le stylo",
            "G0 X0 Y0 ; Aller à l'origine"
        ]
        
        # Ajouter des commandes basées sur le SVG
        # Ceci est une conversion très basique
        lines_added = 0
        
        # Chercher des paths dans le SVG
        import re
        path_pattern = r'd="([^"]+)"'
        paths = re.findall(path_pattern, svg_content, re.IGNORECASE)
        
        for path in paths[:10]:  # Limiter à 10 paths pour l'exemple
            # Convertir très basiquement
            gcode_lines.append("; Début path")
            gcode_lines.append("G1 Z0 F100 ; Baisser le stylo")
            
            # Points aléatoires (simulation)
            for i in range(5):
                x = i * 20
                y = (i % 3) * 20
                gcode_lines.append(f"G1 X{x} Y{y} F500")
                lines_added += 1
            
            gcode_lines.append("G0 Z5 ; Lever le stylo")
        
        if lines_added == 0:
            # Ajouter un dessin par défaut
            gcode_lines.extend([
                "; Aucun path trouvé, dessin par défaut",
                "G1 Z0 F100",
                "G1 X50 Y50 F500",
                "G1 X100 Y100 F500",
                "G1 X150 Y50 F500",
                "G1 X200 Y100 F500",
                "G0 Z5"
            ])
        
        # Fin de programme
        gcode_lines.extend([
            "G0 X0 Y0 ; Retour à l'origine",
            "M2 ; Fin du programme"
        ])
        
        return '\n'.join(gcode_lines)
    
    def get_status(self) -> Dict:
        """Retourne le statut actuel du plotter"""
        return {
            "connected": self.is_connected,
            "plotting": self.is_plotting,
            "current_position": self.current_position,
            "queue_size": self.plotting_queue.qsize(),
            "pen_up": self.current_position[2] >= self.pen_up_height - 1
        }
    
    def emergency_stop(self):
        """Arrêt d'urgence"""
        self.is_plotting = False
        
        if self.is_connected:
            # Envoyer une commande d'arrêt (dépend du firmware)
            self._send_command("M112")  # Arrêt d'urgence pour Marlin
            self._send_command("M108")  # Arrêt pour certains autres
            
            # Lever le stylo
            self.pen_up()
            
            self.logger.warning("ARRÊT D'URGENCE - Plotting interrompu")