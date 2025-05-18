from app import app
from flask import redirect, url_for, render_template, flash, request
from flask_login import login_user, current_user, logout_user, login_required
from models import User
from forms import LoginForm

# Adicionar rota de login diretamente aqui para garantir funcionamento básico
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(form.password.data) and user.active:
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard')
            return redirect(next_page)
        else:
            flash('Nome de usuário ou senha inválidos.', 'danger')
    
    return render_template('login_standalone.html', form=form)

# Adicionar rota de dashboard simplificado
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Adicionar rota para ordens de serviço
@app.route('/ordens-servico')
@login_required
def service_orders():
    return render_template('service_orders/index.html', service_orders=[])

# Rota de visualização de ordens
@app.route('/os/<int:id>')
@login_required
def view_service_order(id):
    return render_template('service_orders/simple_view.html', ordem={'id': id}, cliente={}, equipamentos=[], financeiros=[])

# Rota alternativa que redireciona para a implementação principal
@app.route('/ordem/<int:id>/visualizar')
@login_required
def view_service_order_alt(id):
    return redirect(url_for('view_service_order', id=id))

# Executar aplicação com as rotas simples
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
