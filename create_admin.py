"""
Script para criar um usuário administrador se não existir nenhum.
"""
from app import app, db
from models import User, UserRole

def create_admin_user():
    """Cria um usuário administrador no sistema."""
    with app.app_context():
        # Verificar se existe algum usuário no sistema
        user_count = User.query.count()
        
        if user_count == 0:
            print("Nenhum usuário encontrado. Criando usuário administrador padrão...")
            
            try:
                # Criar um usuário admin
                admin = User(
                    username="admin",
                    name="Administrador",
                    email="admin@samape.com",
                    role=UserRole.admin,
                    active=True
                )
                admin.set_password("admin123")
                
                db.session.add(admin)
                db.session.commit()
                
                print("Usuário administrador criado com sucesso!")
                print("Nome de usuário: admin")
                print("Senha: admin123")
                print("Importante: Altere esta senha após o primeiro login!")
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao criar usuário administrador: {e}")
        else:
            # Verificar se existe algum administrador
            admin_count = User.query.filter_by(role=UserRole.admin).count()
            
            if admin_count == 0:
                print("Nenhum administrador encontrado. Criando usuário administrador padrão...")
                
                try:
                    # Criar um usuário admin
                    admin = User(
                        username="admin",
                        name="Administrador",
                        email="admin@samape.com",
                        role=UserRole.admin,
                        active=True
                    )
                    admin.set_password("admin123")
                    
                    db.session.add(admin)
                    db.session.commit()
                    
                    print("Usuário administrador criado com sucesso!")
                    print("Nome de usuário: admin")
                    print("Senha: admin123")
                    print("Importante: Altere esta senha após o primeiro login!")
                except Exception as e:
                    db.session.rollback()
                    print(f"Erro ao criar usuário administrador: {e}")
            else:
                print(f"Já existem {admin_count} administradores no sistema.")
                admins = User.query.filter_by(role=UserRole.admin).all()
                for admin in admins:
                    print(f"- {admin.username} ({admin.email})")

if __name__ == "__main__":
    create_admin_user()