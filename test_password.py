from app import app
from database import db
import models
import os

with app.app_context():
    user = models.User.query.filter_by(username="Alessandro_jr").first()
    if user:
        # Use a senha do ambiente ou padrão para teste
        senha_teste = os.environ.get("ADMIN_DEFAULT_PASSWORD", "admin123")
        if user.check_password(senha_teste):
            print("Senha correta para Alessandro_jr!")
        else:
            print("Senha INCORRETA para Alessandro_jr!")
    else:
        print("Usuário Alessandro_jr não encontrado.")