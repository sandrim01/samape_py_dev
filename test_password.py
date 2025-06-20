from app import app, db
import models

with app.app_context():
    user = models.User.query.filter_by(username="Alessandro_jr").first()
    if user:
        senha_teste = "Zx1205698979*#"
        if user.check_password(senha_teste):
            print("Senha correta para Alessandro_jr!")
        else:
            print("Senha INCORRETA para Alessandro_jr!")
    else:
        print("Usuário Alessandro_jr não encontrado.")
