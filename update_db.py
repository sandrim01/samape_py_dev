from app import app
from database import db
from sqlalchemy import text

def add_profile_image_column():
    """Add profile_image column to user table if it doesn't exist"""
    with app.app_context():
        # Verificar se a coluna já existe
        result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='user' AND column_name='profile_image'"))
        column_exists = result.fetchone() is not None
        
        if not column_exists:
            print("Adicionando coluna profile_image à tabela user...")
            db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN profile_image VARCHAR(255) DEFAULT 'default_profile.png'"))
            db.session.commit()
            print("Coluna profile_image adicionada com sucesso!")
        else:
            print("Coluna profile_image já existe, nenhuma ação necessária.")

if __name__ == "__main__":
    add_profile_image_column()