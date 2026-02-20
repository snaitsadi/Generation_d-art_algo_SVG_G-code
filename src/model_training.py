"""
Module pour l'entraînement des modèles de génération
"""
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import GPT2Tokenizer, GPT2LMHeadModel, Trainer, TrainingArguments, DataCollatorForLanguageModeling
from datasets import Dataset as HFDataset
import json
from pathlib import Path
from typing import List, Tuple, Dict
import numpy as np
from tqdm import tqdm
import wandb

class ArtDataset(Dataset):
    """Dataset personnalisé pour l'art algorithmique"""
    
    def __init__(self, artworks: List[Dict], tokenizer, max_length=1024):
        self.artworks = artworks
        self.tokenizer = tokenizer
        self.max_length = max_length
        
    def __len__(self):
        return len(self.artworks)
    
    def __getitem__(self, idx):
        artwork = self.artworks[idx]
        content = artwork["content"]
        
        # Tokeniser
        encoding = self.tokenizer(
            content,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'labels': encoding['input_ids'].squeeze()
        }

class ModelTrainer:
    """Entraîneur pour les modèles de génération"""
    
    def __init__(self, config):
        self.config = config
        self.tokenizer = None
        self.model = None
        
    def prepare_data(self, data_dir: str, format_type: str = "svg") -> Dataset:
        """Prépare les données pour l'entraînement en lisant le contenu depuis les fichiers"""
        data_path = Path(data_dir)
        index_path = data_path / "dataset_index.json"
    
        with open(index_path, 'r', encoding='utf-8') as f:
            all_artworks = json.load(f)
    
    # Filtrer par format
        artworks = [art for art in all_artworks if art["format_type"] == format_type]
    
        if not artworks:
            raise ValueError(f"Aucune œuvre trouvée pour le format {format_type}")
    
    # Charger le contenu de chaque fichier
        dataset_list = []
        for art in artworks:
            file_path = Path(art["file_path"])
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                dataset_list.append({
                    "content": content,
                    "format_type": art["format_type"],
                    "metadata": art.get("metadata", {})
                })
            else:
                print(f"⚠️ Fichier manquant : {file_path}")
    
        print(f"Chargement de {len(dataset_list)} œuvres au format {format_type}")
    
    # Convertir en dataset Hugging Face
        # Convertir la liste de dictionnaires en dictionnaire de listes
        hf_dataset = HFDataset.from_dict({
            'content': [item['content'] for item in dataset_list],
            'format_type': [item['format_type'] for item in dataset_list],
            'metadata': [item.get('metadata', {}) for item in dataset_list]
        })
    # Split train/test
        split_dataset = hf_dataset.train_test_split(test_size=0.1, seed=42)
        return split_dataset
    
    def train(self, train_dataset, val_dataset, format_type: str = "svg"):
        """Entraîne le modèle"""
        print(f"Entraînement d'un modèle pour le format {format_type}")
        
        # Initialiser le tokenizer et le modèle
        self.tokenizer = GPT2Tokenizer.from_pretrained(self.config.TOKENIZER_NAME)
        
        # Ajouter un token de padding si nécessaire
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = GPT2LMHeadModel.from_pretrained(
            self.config.MODEL_NAME,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        # Redimensionner les embeddings du tokenizer
        self.model.resize_token_embeddings(len(self.tokenizer))
        
        # Préparer les données
        def tokenize_function(examples):
            return self.tokenizer(
                examples["content"],
                truncation=True,
                padding="max_length",
                max_length=self.config.MAX_LENGTH
            )
        
        tokenized_train = train_dataset.map(tokenize_function, batched=True, remove_columns=train_dataset.column_names)
        tokenized_val = val_dataset.map(tokenize_function, batched=True, remove_columns=val_dataset.column_names)
        
        # Configurer l'entraînement
        training_args = TrainingArguments(
            output_dir=f"./models/{format_type}_model",
            num_train_epochs=self.config.EPOCHS,
            per_device_train_batch_size=self.config.BATCH_SIZE,
            per_device_eval_batch_size=self.config.BATCH_SIZE,
            warmup_steps=100,
            weight_decay=0.01,
            logging_dir=f"./logs/{format_type}",
            logging_steps=50,
            eval_steps=200,
            save_steps=500,
            save_total_limit=3,
            fp16=torch.cuda.is_available(),
            remove_unused_columns=False,  # important pour les datasets personnalisés
        )
        
        # Créer le data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )
        
        # Initialiser le trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            data_collator=data_collator,
            train_dataset=tokenized_train,
            eval_dataset=tokenized_val,
        )
        
        # Démarrer l'entraînement
        print("Début de l'entraînement...")
        trainer.train()
        
        # Sauvegarder le modèle
        output_dir = Path(f"./models/{format_type}_model_final")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        trainer.save_model(str(output_dir))
        self.tokenizer.save_pretrained(str(output_dir))
        
        print(f"Modèle sauvegardé dans {output_dir}")
        
        return trainer
    
    def train_multi_format(self, svg_data_dir: str, gcode_data_dir: str):
        """Entraîne un modèle multi-format"""
        print("Entraînement d'un modèle multi-format...")
        
        # Charger les données SVG
        svg_artworks = self._load_artworks(svg_data_dir, "svg")
        
        # Charger les données G-code
        gcode_artworks = self._load_artworks(gcode_data_dir, "gcode")
        
        # Combiner les datasets
        all_artworks = svg_artworks + gcode_artworks
        
        # Ajouter des tokens spéciaux pour les formats
        self.tokenizer = GPT2Tokenizer.from_pretrained(self.config.TOKENIZER_NAME)
        
        # Ajouter des tokens spéciaux
        special_tokens = {
            'additional_special_tokens': [
                '[SVG_START]', '[SVG_END]',
                '[GCODE_START]', '[GCODE_END]',
                '[DRAW]', '[MOVE]', '[SHAPE]'
            ]
        }
        self.tokenizer.add_special_tokens(special_tokens)
        
        # Initialiser le modèle
        self.model = GPT2LMHeadModel.from_pretrained(
            self.config.MODEL_NAME,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        # Redimensionner pour les nouveaux tokens
        self.model.resize_token_embeddings(len(self.tokenizer))
        
        # Préparer les données avec format
        formatted_artworks = []
        for art in all_artworks:
            if art["format_type"] == "svg":
                formatted_content = f"[SVG_START] {art['content']} [SVG_END]"
            else:
                formatted_content = f"[GCODE_START] {art['content']} [GCODE_END]"
            
            formatted_artworks.append({
                "content": formatted_content,
                "format_type": art["format_type"]
            })
        
        # Créer le dataset
        dataset = HFDataset.from_list(formatted_artworks)
        split_dataset = dataset.train_test_split(test_size=0.1, seed=42)
        
        # Tokeniser
        def tokenize_multi(examples):
            return self.tokenizer(
                examples["content"],
                truncation=True,
                padding="max_length",
                max_length=self.config.MAX_LENGTH
            )
        
        tokenized_train = split_dataset["train"].map(tokenize_multi, batched=True)
        tokenized_val = split_dataset["test"].map(tokenize_multi, batched=True)
        
        # Entraîner
        training_args = TrainingArguments(
            output_dir="./models/multi_format_model",
            num_train_epochs=self.config.EPOCHS,
            per_device_train_batch_size=self.config.BATCH_SIZE,
            save_strategy="steps",
            save_steps=500,
            evaluation_strategy="steps",
            eval_steps=200,
            logging_steps=50,
            learning_rate=self.config.LEARNING_RATE,
            weight_decay=0.01,
            fp16=torch.cuda.is_available(),
        )
        
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_train,
            eval_dataset=tokenized_val,
            data_collator=DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False
            )
        )
        
        trainer.train()
        
        # Sauvegarder
        output_dir = Path("./models/multi_format_model_final")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        trainer.save_model(str(output_dir))
        self.tokenizer.save_pretrained(str(output_dir))
        
        print(f"Modèle multi-format sauvegardé dans {output_dir}")
        
        return trainer
    
    def _load_artworks(self, data_dir: str, format_type: str) -> List[Dict]:
        """Charge les artworks depuis un répertoire"""
        data_path = Path(data_dir)
        
        if not data_path.exists():
            return []
        
        artworks = []
        
        # Charger depuis l'index ou scanner les fichiers
        index_path = data_path / "dataset_index.json"
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            for item in index_data:
                if item.get("format_type") == format_type:
                    file_path = Path(item["file_path"])
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        artworks.append({
                            "content": content,
                            "format_type": format_type,
                            "metadata": item.get("metadata", {})
                        })
        
        return artworks