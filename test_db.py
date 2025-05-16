import os
import sys
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Classe base do SQLAlchemy
class Base(DeclarativeBase):
    pass

# Inicializar app para teste
app = Flask(__name__)
db = SQLAlchemy(model_class=Base)

# Configurar conexão com banco de dados
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicializar db com app
db.init_app(app)

# Testar conexão
with app.app_context():
    try:
        from models import Vehicle
        # Tentar buscar todos os veículos
        vehicles = Vehicle.query.all()
        logger.info(f"Conexão com banco de dados bem-sucedida. Encontrados {len(vehicles)} veículos.")
        
        # Mostrar alguns detalhes dos veículos encontrados
        for i, vehicle in enumerate(vehicles[:3]):  # Mostrar apenas os 3 primeiros
            logger.info(f"Veículo {i+1}: {vehicle.brand} {vehicle.model}, Placa: {vehicle.plate}")
            logger.info(f"  - Status da imagem: {'Com imagem' if vehicle.image_data else 'Sem imagem'}")
            logger.info(f"  - Campo legado 'image': {vehicle.image}")
        
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}", exc_info=True)