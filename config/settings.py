# Configuration du projet

class Config:
    # Paths
    DATA_DIR = "data"
    RAW_SVG_DIR = "data/raw/svg"
    RAW_GCODE_DIR = "data/raw/gcode"
    PROCESSED_DIR = "data/processed"
    GENERATED_DIR = "data/generated"
    MODEL_DIR = "models"
    
    # Model settings
    MODEL_NAME = "gpt2"
    TOKENIZER_NAME = "gpt2"
    MAX_LENGTH = 1024
    BATCH_SIZE = 8
    EPOCHS = 10
    LEARNING_RATE = 5e-5
    
    # Generation settings
    GENERATION_TEMPERATURE = 0.9
    TOP_P = 0.95
    TOP_K = 50
    REPETITION_PENALTY = 1.2
    
    # Dataset settings
    MIN_SVG_LENGTH = 100
    MAX_SVG_LENGTH = 5000
    TRAIN_TEST_SPLIT = 0.8
    
    # Plotter settings
    PLOTTER_PORT = "/dev/ttyUSB0"
    PLOTTER_BAUDRATE = 115200
    PLOTTER_WIDTH_MM = 300
    PLOTTER_HEIGHT_MM = 210
    
    # Validation
    SVG_NAMESPACE = "http://www.w3.org/2000/svg"
    GCODE_SAFE_HEIGHT = 5
    GCODE_DRAW_HEIGHT = 0

config = Config()
