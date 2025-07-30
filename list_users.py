from app import app
from database import db
import models

with app.app_context():
    users = models.User.query.all()
    for user in users:
        print(f"ID: {user.id} | username: {user.username} | email: {user.email} | ativo: {user.active} | role: {user.role} | hash: {user.password_hash}")
