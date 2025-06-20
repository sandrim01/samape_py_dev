from app import app, db
import models

with app.app_context():
    db.create_all()
    print('Tabelas criadas com sucesso!')

    # Criação do usuário administrador Alessandro_jr
    if not models.User.query.filter_by(username="Alessandro_jr").first():
        user = models.User(
            username="Alessandro_jr",
            name="Alessandro Junior",
            email="alessandro_jr@example.com",
            role=models.UserRole.admin,
            active=True
        )
        user.set_password("Zx1205698979*#")
        db.session.add(user)
        db.session.commit()
        print("Usuário administrador Alessandro_jr criado com sucesso!")
    else:
        print("Usuário Alessandro_jr já existe.")
