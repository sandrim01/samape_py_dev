from app import app
from database import db
import models
import os

with app.app_context():
    db.create_all()
    print('Tabelas criadas com sucesso!')

    # Criação do usuário administrador Alessandro_jr
    if not models.User.query.filter_by(username="Alessandro_jr").first():
        # Senha padrão - DEVE SER ALTERADA NO PRIMEIRO LOGIN
        default_password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "admin123")
        
        user = models.User(
            username="Alessandro_jr",
            name="Alessandro Junior",
            email="alessandro_jr@example.com",
            role=models.UserRole.admin,
            active=True
        )
        user.set_password(default_password)
        db.session.add(user)
        db.session.commit()
        print(f"Usuário administrador Alessandro_jr criado com sucesso!")
        print(f"IMPORTANTE: Altere a senha padrão no primeiro login!")
    else:
        print("Usuário Alessandro_jr já existe.")
