@app.route('/ordem/<int:id>/visualizar')
@login_required
def view_service_order_alt(id):
    # Simplesmente redireciona para a implementação principal
    return redirect(url_for('view_service_order', id=id))