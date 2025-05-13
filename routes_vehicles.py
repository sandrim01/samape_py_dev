"""
Módulo para as rotas relacionadas ao controle de frota
"""
import os
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db, app
from models import Vehicle, Refueling, VehicleMaintenance, VehicleTravelLog, VehicleStatus
from forms import VehicleForm, RefuelingForm, VehicleMaintenanceForm, VehicleTravelLogForm, VehicleTravelLogCompleteForm, DeleteImageForm
import locale
from utils import allowed_file, delete_file, save_image, create_log, format_date
import uuid
import re

# Configurar o locale para formatação de números
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# Definir as pastas para salvar as imagens
UPLOAD_FOLDER = 'static/uploads/vehicles'
VEHICLE_IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'images')
RECEIPT_IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'receipts')
INVOICE_IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'invoices')

# Criar as pastas se não existirem
os.makedirs(VEHICLE_IMAGES_FOLDER, exist_ok=True)
os.makedirs(RECEIPT_IMAGES_FOLDER, exist_ok=True)
os.makedirs(INVOICE_IMAGES_FOLDER, exist_ok=True)

# Rota para listar todos os veículos
@app.route('/veiculos')
@login_required
def vehicles():
    """Lista todos os veículos da frota"""
    vehicles = Vehicle.query.order_by(Vehicle.plate).all()
    form = DeleteImageForm()
    
    # Estatísticas
    active_count = Vehicle.query.filter_by(status=VehicleStatus.ativo).count()
    maintenance_count = Vehicle.query.filter_by(status=VehicleStatus.em_manutencao).count()
    inactive_count = Vehicle.query.filter_by(status=VehicleStatus.inativo).count()
    
    return render_template(
        'vehicles/index.html',
        title='Controle de Frota',
        vehicles=vehicles,
        form=form,
        active_count=active_count,
        maintenance_count=maintenance_count,
        inactive_count=inactive_count
    )

# Rota para adicionar um novo veículo
@login_required
def add_vehicle():
    """Adiciona um novo veículo à frota"""
    form = VehicleForm()
    
    if form.validate_on_submit():
        # Salvar a imagem se fornecida
        image_filename = None
        if form.image.data:
            image_filename = save_image(form.image.data, VEHICLE_IMAGES_FOLDER)
        
        # Preparar os dados do veículo
        vehicle = Vehicle(
            model=form.model.data,
            brand=form.brand.data,
            plate=form.plate.data.upper(),
            year=form.year.data,
            color=form.color.data,
            chassis=form.chassis.data,
            renavam=form.renavam.data,
            fuel_type=form.fuel_type.data,
            status=form.status.data,
            current_km=form.current_km.data,
            acquisition_date=form.acquisition_date.data,
            insurance_expiry=form.insurance_expiry.data,
            insurance_policy=form.insurance_policy.data,
            next_maintenance_date=form.next_maintenance_date.data,
            next_maintenance_km=form.next_maintenance_km.data,
            responsible_id=form.responsible_id.data if form.responsible_id.data != 0 else None,
            notes=form.notes.data,
            image=image_filename
        )
        
        # Salvar o veículo no banco de dados
        db.session.add(vehicle)
        db.session.commit()
        
        # Criar log da ação
        create_log(f'Veículo adicionado: {vehicle.plate} - {vehicle.brand} {vehicle.model}')
        
        flash(f'Veículo {vehicle.plate} adicionado com sucesso!', 'success')
        return redirect(url_for('vehicles'))
    
    return render_template(
        'vehicles/add.html',
        title='Adicionar Veículo',
        form=form
    )

# Rota para visualizar detalhes de um veículo
@login_required
def view_vehicle(vehicle_id):
    """Exibe os detalhes de um veículo"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    delete_form = DeleteImageForm()
    
    # Obter registros relacionados
    refuelings = Refueling.query.filter_by(vehicle_id=vehicle_id).order_by(Refueling.date.desc()).all()
    maintenances = VehicleMaintenance.query.filter_by(vehicle_id=vehicle_id).order_by(VehicleMaintenance.date.desc()).all()
    travel_logs = VehicleTravelLog.query.filter_by(vehicle_id=vehicle_id).order_by(VehicleTravelLog.start_date.desc()).all()
    
    # Calcular estatísticas
    total_refueling_cost = sum(r.total_cost for r in refuelings)
    total_maintenance_cost = sum(m.cost for m in maintenances)
    total_travel_distance = sum(t.distance for t in travel_logs if t.distance is not None)
    
    return render_template(
        'vehicles/view.html',
        title=f'Veículo {vehicle.plate}',
        vehicle=vehicle,
        refuelings=refuelings,
        maintenances=maintenances,
        travel_logs=travel_logs,
        total_refueling_cost=total_refueling_cost,
        total_maintenance_cost=total_maintenance_cost,
        total_travel_distance=total_travel_distance,
        delete_form=delete_form
    )

# Rota para editar um veículo
@login_required
def edit_vehicle(vehicle_id):
    """Edita um veículo existente"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = VehicleForm(obj=vehicle)
    
    if form.validate_on_submit():
        # Processar a imagem se fornecida
        if form.image.data:
            if vehicle.image:
                delete_file(os.path.join(VEHICLE_IMAGES_FOLDER, vehicle.image))
            vehicle.image = save_image(form.image.data, VEHICLE_IMAGES_FOLDER)
        
        # Atualizar dados do veículo
        vehicle.model = form.model.data
        vehicle.brand = form.brand.data
        vehicle.plate = form.plate.data.upper()
        vehicle.year = form.year.data
        vehicle.color = form.color.data
        vehicle.chassis = form.chassis.data
        vehicle.renavam = form.renavam.data
        vehicle.fuel_type = form.fuel_type.data
        vehicle.status = form.status.data
        vehicle.current_km = form.current_km.data
        vehicle.acquisition_date = form.acquisition_date.data
        vehicle.insurance_expiry = form.insurance_expiry.data
        vehicle.insurance_policy = form.insurance_policy.data
        vehicle.next_maintenance_date = form.next_maintenance_date.data
        vehicle.next_maintenance_km = form.next_maintenance_km.data
        vehicle.responsible_id = form.responsible_id.data if form.responsible_id.data != 0 else None
        vehicle.notes = form.notes.data
        
        db.session.commit()
        
        # Criar log da ação
        create_log(f'Veículo editado: {vehicle.plate} - {vehicle.brand} {vehicle.model}')
        
        flash(f'Veículo {vehicle.plate} atualizado com sucesso!', 'success')
        return redirect(url_for('view_vehicle', vehicle_id=vehicle.id))
    
    return render_template(
        'vehicles/edit.html',
        title=f'Editar Veículo {vehicle.plate}',
        form=form,
        vehicle=vehicle
    )

# Rota para excluir um veículo
@login_required
def delete_vehicle(vehicle_id):
    """Exclui um veículo da frota"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Verificar se há dependências
    refuelings = Refueling.query.filter_by(vehicle_id=vehicle_id).count()
    maintenances = VehicleMaintenance.query.filter_by(vehicle_id=vehicle_id).count()
    travel_logs = VehicleTravelLog.query.filter_by(vehicle_id=vehicle_id).count()
    
    if refuelings > 0 or maintenances > 0 or travel_logs > 0:
        flash(f'Não é possível excluir o veículo {vehicle.plate}. Existem registros associados.', 'danger')
        return redirect(url_for('view_vehicle', vehicle_id=vehicle_id))
    
    # Excluir a imagem do veículo se existir
    if vehicle.image:
        delete_file(os.path.join(VEHICLE_IMAGES_FOLDER, vehicle.image))
    
    # Criar log da ação antes de excluir
    plate = vehicle.plate
    brand_model = f'{vehicle.brand} {vehicle.model}'
    
    # Excluir o veículo
    db.session.delete(vehicle)
    db.session.commit()
    
    create_log(f'Veículo excluído: {plate} - {brand_model}')
    
    flash(f'Veículo {plate} excluído com sucesso!', 'success')
    return redirect(url_for('vehicles'))

# Rota para excluir a imagem de um veículo
@login_required
def delete_vehicle_image(vehicle_id):
    """Remove a imagem de um veículo"""
    form = DeleteImageForm()
    if form.validate_on_submit():
        vehicle = Vehicle.query.get_or_404(vehicle_id)
        
        if vehicle.image:
            # Excluir o arquivo
            delete_file(os.path.join(VEHICLE_IMAGES_FOLDER, vehicle.image))
            
            # Atualizar o registro
            vehicle.image = None
            db.session.commit()
            
            create_log(f'Imagem removida do veículo: {vehicle.plate}')
            
            flash('Imagem removida com sucesso!', 'success')
        else:
            flash('Este veículo não possui imagem para excluir.', 'warning')
    
    return redirect(url_for('view_vehicle', vehicle_id=vehicle_id))

# ROTAS PARA ABASTECIMENTO

# Rota para listar todos os abastecimentos
@login_required
def refuelings():
    """Lista todos os registros de abastecimento"""
    refuelings = Refueling.query.order_by(Refueling.date.desc()).all()
    form = DeleteImageForm()
    
    # Cálculos estatísticos
    total_cost = sum(r.total_cost for r in refuelings)
    total_liters = sum(r.liters for r in refuelings)
    avg_price = total_cost / total_liters if total_liters > 0 else 0
    
    return render_template(
        'vehicles/refuelings/index.html',
        title='Registros de Abastecimento',
        refuelings=refuelings,
        form=form,
        total_cost=total_cost,
        total_liters=total_liters,
        avg_price=avg_price
    )

# Rota para adicionar um novo abastecimento
@login_required
def add_refueling():
    """Registra um novo abastecimento"""
    form = RefuelingForm()
    
    if form.validate_on_submit():
        # Salvar a imagem do comprovante se fornecida
        receipt_image = None
        if form.receipt_image.data:
            receipt_image = save_image(form.receipt_image.data, RECEIPT_IMAGES_FOLDER)
        
        # Preparar os dados do abastecimento
        refueling = Refueling(
            vehicle_id=form.vehicle_id.data,
            date=form.date.data,
            odometer=form.odometer.data,
            fuel_type=form.fuel_type.data,
            liters=form.liters.data,
            price_per_liter=form.price_per_liter.data,
            total_cost=form.total_cost.data,
            full_tank=form.full_tank.data,
            gas_station=form.gas_station.data,
            driver_id=form.driver_id.data if form.driver_id.data != 0 else None,
            service_order_id=form.service_order_id.data if form.service_order_id.data != 0 else None,
            receipt_image=receipt_image,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        # Salvar o abastecimento e atualizar o odômetro do veículo
        vehicle = Vehicle.query.get(form.vehicle_id.data)
        if vehicle and form.odometer.data > vehicle.current_km:
            vehicle.current_km = form.odometer.data
        
        db.session.add(refueling)
        db.session.commit()
        
        # Criar log da ação
        vehicle_plate = Vehicle.query.get(form.vehicle_id.data).plate
        create_log(f'Abastecimento registrado: {vehicle_plate} - {form.liters.data}L - R${form.total_cost.data:.2f}')
        
        flash('Abastecimento registrado com sucesso!', 'success')
        return redirect(url_for('refuelings'))
    
    return render_template(
        'vehicles/refuelings/add.html',
        title='Registrar Abastecimento',
        form=form
    )

# Rota para visualizar um abastecimento específico
@login_required
def view_refueling(refueling_id):
    """Exibe os detalhes de um abastecimento"""
    refueling = Refueling.query.get_or_404(refueling_id)
    delete_form = DeleteImageForm()
    
    return render_template(
        'vehicles/refuelings/view.html',
        title=f'Abastecimento #{refueling.id}',
        refueling=refueling,
        delete_form=delete_form
    )

# Rota para editar um abastecimento
@login_required
def edit_refueling(refueling_id):
    """Edita um registro de abastecimento"""
    refueling = Refueling.query.get_or_404(refueling_id)
    form = RefuelingForm(obj=refueling)
    
    if form.validate_on_submit():
        # Processar a imagem do comprovante se fornecida
        if form.receipt_image.data:
            if refueling.receipt_image:
                delete_file(os.path.join(RECEIPT_IMAGES_FOLDER, refueling.receipt_image))
            refueling.receipt_image = save_image(form.receipt_image.data, RECEIPT_IMAGES_FOLDER)
        
        # Atualizar dados do abastecimento
        refueling.vehicle_id = form.vehicle_id.data
        refueling.date = form.date.data
        refueling.odometer = form.odometer.data
        refueling.fuel_type = form.fuel_type.data
        refueling.liters = form.liters.data
        refueling.price_per_liter = form.price_per_liter.data
        refueling.total_cost = form.total_cost.data
        refueling.full_tank = form.full_tank.data
        refueling.gas_station = form.gas_station.data
        refueling.driver_id = form.driver_id.data if form.driver_id.data != 0 else None
        refueling.service_order_id = form.service_order_id.data if form.service_order_id.data != 0 else None
        refueling.notes = form.notes.data
        
        # Atualizar o odômetro do veículo se necessário
        vehicle = Vehicle.query.get(form.vehicle_id.data)
        if vehicle and form.odometer.data > vehicle.current_km:
            vehicle.current_km = form.odometer.data
        
        db.session.commit()
        
        # Criar log da ação
        vehicle_plate = Vehicle.query.get(form.vehicle_id.data).plate
        create_log(f'Abastecimento editado: {vehicle_plate} - {form.liters.data}L - R${form.total_cost.data:.2f}')
        
        flash('Abastecimento atualizado com sucesso!', 'success')
        return redirect(url_for('view_refueling', refueling_id=refueling.id))
    
    return render_template(
        'vehicles/refuelings/edit.html',
        title=f'Editar Abastecimento #{refueling.id}',
        form=form,
        refueling=refueling
    )

# Rota para excluir um abastecimento
@login_required
def delete_refueling(refueling_id):
    """Exclui um registro de abastecimento"""
    refueling = Refueling.query.get_or_404(refueling_id)
    
    # Excluir a imagem do comprovante se existir
    if refueling.receipt_image:
        delete_file(os.path.join(RECEIPT_IMAGES_FOLDER, refueling.receipt_image))
    
    # Criar log da ação
    vehicle_plate = Vehicle.query.get(refueling.vehicle_id).plate if refueling.vehicle_id else "Desconhecido"
    refueling_data = f'{vehicle_plate} - {refueling.liters}L - R${refueling.total_cost:.2f}'
    
    # Excluir o registro
    db.session.delete(refueling)
    db.session.commit()
    
    create_log(f'Abastecimento excluído: {refueling_data}')
    
    flash('Registro de abastecimento excluído com sucesso!', 'success')
    return redirect(url_for('refuelings'))

# Rota para excluir a imagem do comprovante
@login_required
def delete_refueling_receipt(refueling_id):
    """Remove a imagem do comprovante de abastecimento"""
    form = DeleteImageForm()
    if form.validate_on_submit():
        refueling = Refueling.query.get_or_404(refueling_id)
        
        if refueling.receipt_image:
            # Excluir o arquivo
            delete_file(os.path.join(RECEIPT_IMAGES_FOLDER, refueling.receipt_image))
            
            # Atualizar o registro
            refueling.receipt_image = None
            db.session.commit()
            
            create_log(f'Comprovante removido do abastecimento #{refueling.id}')
            
            flash('Comprovante removido com sucesso!', 'success')
        else:
            flash('Este registro não possui comprovante para excluir.', 'warning')
    
    return redirect(url_for('view_refueling', refueling_id=refueling_id))

# ROTAS PARA MANUTENÇÃO

# Rota para listar todas as manutenções
@login_required
def maintenances():
    """Lista todos os registros de manutenção"""
    maintenances = VehicleMaintenance.query.order_by(VehicleMaintenance.date.desc()).all()
    form = DeleteImageForm()
    
    # Cálculos estatísticos
    total_cost = sum(m.cost for m in maintenances)
    
    return render_template(
        'vehicles/maintenances/index.html',
        title='Registros de Manutenção',
        maintenances=maintenances,
        form=form,
        total_cost=total_cost
    )

# Rota para adicionar uma nova manutenção
@login_required
def add_maintenance():
    """Registra uma nova manutenção"""
    form = VehicleMaintenanceForm()
    
    if form.validate_on_submit():
        # Salvar a imagem da nota fiscal se fornecida
        invoice_image = None
        if form.invoice_image.data:
            invoice_image = save_image(form.invoice_image.data, INVOICE_IMAGES_FOLDER)
        
        # Preparar os dados da manutenção
        maintenance = VehicleMaintenance(
            vehicle_id=form.vehicle_id.data,
            date=form.date.data,
            odometer=form.odometer.data,
            maintenance_type=form.maintenance_type.data,
            description=form.description.data,
            cost=form.cost.data,
            workshop=form.workshop.data,
            service_order_id=form.service_order_id.data if form.service_order_id.data != 0 else None,
            invoice_number=form.invoice_number.data,
            invoice_image=invoice_image,
            completed=form.completed.data,
            next_maintenance_date=form.next_maintenance_date.data,
            next_maintenance_km=form.next_maintenance_km.data,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        # Salvar a manutenção e atualizar o odômetro do veículo
        vehicle = Vehicle.query.get(form.vehicle_id.data)
        if vehicle:
            if form.odometer.data > vehicle.current_km:
                vehicle.current_km = form.odometer.data
            if form.next_maintenance_date.data:
                vehicle.next_maintenance_date = form.next_maintenance_date.data
            if form.next_maintenance_km.data:
                vehicle.next_maintenance_km = form.next_maintenance_km.data
        
        db.session.add(maintenance)
        db.session.commit()
        
        # Criar log da ação
        vehicle_plate = Vehicle.query.get(form.vehicle_id.data).plate
        create_log(f'Manutenção registrada: {vehicle_plate} - {form.maintenance_type.data} - R${form.cost.data:.2f}')
        
        flash('Manutenção registrada com sucesso!', 'success')
        return redirect(url_for('maintenances'))
    
    return render_template(
        'vehicles/maintenances/add.html',
        title='Registrar Manutenção',
        form=form
    )

# Rota para visualizar uma manutenção específica
@login_required
def view_maintenance(maintenance_id):
    """Exibe os detalhes de uma manutenção"""
    maintenance = VehicleMaintenance.query.get_or_404(maintenance_id)
    delete_form = DeleteImageForm()
    
    return render_template(
        'vehicles/maintenances/view.html',
        title=f'Manutenção #{maintenance.id}',
        maintenance=maintenance,
        delete_form=delete_form
    )

# Rota para editar uma manutenção
@login_required
def edit_maintenance(maintenance_id):
    """Edita um registro de manutenção"""
    maintenance = VehicleMaintenance.query.get_or_404(maintenance_id)
    form = VehicleMaintenanceForm(obj=maintenance)
    
    if form.validate_on_submit():
        # Processar a imagem da nota fiscal se fornecida
        if form.invoice_image.data:
            if maintenance.invoice_image:
                delete_file(os.path.join(INVOICE_IMAGES_FOLDER, maintenance.invoice_image))
            maintenance.invoice_image = save_image(form.invoice_image.data, INVOICE_IMAGES_FOLDER)
        
        # Atualizar dados da manutenção
        maintenance.vehicle_id = form.vehicle_id.data
        maintenance.date = form.date.data
        maintenance.odometer = form.odometer.data
        maintenance.maintenance_type = form.maintenance_type.data
        maintenance.description = form.description.data
        maintenance.cost = form.cost.data
        maintenance.workshop = form.workshop.data
        maintenance.service_order_id = form.service_order_id.data if form.service_order_id.data != 0 else None
        maintenance.invoice_number = form.invoice_number.data
        maintenance.completed = form.completed.data
        maintenance.next_maintenance_date = form.next_maintenance_date.data
        maintenance.next_maintenance_km = form.next_maintenance_km.data
        maintenance.notes = form.notes.data
        
        # Atualizar o veículo se necessário
        vehicle = Vehicle.query.get(form.vehicle_id.data)
        if vehicle:
            if form.odometer.data > vehicle.current_km:
                vehicle.current_km = form.odometer.data
            if form.next_maintenance_date.data:
                vehicle.next_maintenance_date = form.next_maintenance_date.data
            if form.next_maintenance_km.data:
                vehicle.next_maintenance_km = form.next_maintenance_km.data
        
        db.session.commit()
        
        # Criar log da ação
        vehicle_plate = Vehicle.query.get(form.vehicle_id.data).plate
        create_log(f'Manutenção editada: {vehicle_plate} - {form.maintenance_type.data} - R${form.cost.data:.2f}')
        
        flash('Manutenção atualizada com sucesso!', 'success')
        return redirect(url_for('view_maintenance', maintenance_id=maintenance.id))
    
    return render_template(
        'vehicles/maintenances/edit.html',
        title=f'Editar Manutenção #{maintenance.id}',
        form=form,
        maintenance=maintenance
    )

# Rota para excluir uma manutenção
@login_required
def delete_maintenance(maintenance_id):
    """Exclui um registro de manutenção"""
    maintenance = VehicleMaintenance.query.get_or_404(maintenance_id)
    
    # Excluir a imagem da nota fiscal se existir
    if maintenance.invoice_image:
        delete_file(os.path.join(INVOICE_IMAGES_FOLDER, maintenance.invoice_image))
    
    # Criar log da ação
    vehicle_plate = Vehicle.query.get(maintenance.vehicle_id).plate if maintenance.vehicle_id else "Desconhecido"
    maintenance_data = f'{vehicle_plate} - {maintenance.maintenance_type} - R${maintenance.cost:.2f}'
    
    # Excluir o registro
    db.session.delete(maintenance)
    db.session.commit()
    
    create_log(f'Manutenção excluída: {maintenance_data}')
    
    flash('Registro de manutenção excluído com sucesso!', 'success')
    return redirect(url_for('maintenances'))

# Rota para excluir a imagem da nota fiscal
@login_required
def delete_maintenance_invoice(maintenance_id):
    """Remove a imagem da nota fiscal de manutenção"""
    form = DeleteImageForm()
    if form.validate_on_submit():
        maintenance = VehicleMaintenance.query.get_or_404(maintenance_id)
        
        if maintenance.invoice_image:
            # Excluir o arquivo
            delete_file(os.path.join(INVOICE_IMAGES_FOLDER, maintenance.invoice_image))
            
            # Atualizar o registro
            maintenance.invoice_image = None
            db.session.commit()
            
            create_log(f'Nota fiscal removida da manutenção #{maintenance.id}')
            
            flash('Nota fiscal removida com sucesso!', 'success')
        else:
            flash('Este registro não possui nota fiscal para excluir.', 'warning')
    
    return redirect(url_for('view_maintenance', maintenance_id=maintenance_id))

# ROTAS PARA VIAGENS/DESLOCAMENTOS

# Rota para listar todas as viagens
@login_required
def travel_logs():
    """Lista todos os registros de viagens/deslocamentos"""
    travel_logs = VehicleTravelLog.query.order_by(VehicleTravelLog.start_date.desc()).all()
    
    # Separar viagens em andamento e concluídas
    ongoing_travels = [t for t in travel_logs if t.status == 'em_andamento']
    completed_travels = [t for t in travel_logs if t.status == 'concluido']
    
    # Cálculos estatísticos
    total_distance = sum(t.distance for t in travel_logs if t.distance is not None)
    
    return render_template(
        'vehicles/travel_logs/index.html',
        title='Registros de Viagens',
        ongoing_travels=ongoing_travels,
        completed_travels=completed_travels,
        total_distance=total_distance
    )

# Rota para adicionar uma nova viagem
@login_required
def add_travel_log():
    """Registra uma nova viagem/deslocamento"""
    form = VehicleTravelLogForm()
    
    if form.validate_on_submit():
        # Preparar os dados da viagem
        travel_log = VehicleTravelLog(
            vehicle_id=form.vehicle_id.data,
            driver_id=form.driver_id.data,
            service_order_id=form.service_order_id.data if form.service_order_id.data != 0 else None,
            start_date=form.start_date.data,
            start_odometer=form.start_odometer.data,
            destination=form.destination.data,
            purpose=form.purpose.data,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        db.session.add(travel_log)
        db.session.commit()
        
        # Criar log da ação
        vehicle_plate = Vehicle.query.get(form.vehicle_id.data).plate
        create_log(f'Viagem iniciada: {vehicle_plate} - {form.destination.data}')
        
        flash('Viagem registrada com sucesso!', 'success')
        return redirect(url_for('travel_logs'))
    
    return render_template(
        'vehicles/travel_logs/add.html',
        title='Registrar Viagem',
        form=form
    )

# Rota para visualizar uma viagem específica
@login_required
def view_travel_log(travel_log_id):
    """Exibe os detalhes de uma viagem"""
    travel_log = VehicleTravelLog.query.get_or_404(travel_log_id)
    complete_form = VehicleTravelLogCompleteForm() if travel_log.status == 'em_andamento' else None
    
    return render_template(
        'vehicles/travel_logs/view.html',
        title=f'Viagem #{travel_log.id}',
        travel_log=travel_log,
        complete_form=complete_form
    )

# Rota para editar uma viagem
@login_required
def edit_travel_log(travel_log_id):
    """Edita um registro de viagem"""
    travel_log = VehicleTravelLog.query.get_or_404(travel_log_id)
    
    # Não permitir edição de viagens já concluídas
    if travel_log.status != 'em_andamento':
        flash('Viagens concluídas não podem ser editadas.', 'warning')
        return redirect(url_for('view_travel_log', travel_log_id=travel_log.id))
    
    form = VehicleTravelLogForm(obj=travel_log)
    
    if form.validate_on_submit():
        # Atualizar dados da viagem
        travel_log.vehicle_id = form.vehicle_id.data
        travel_log.driver_id = form.driver_id.data
        travel_log.service_order_id = form.service_order_id.data if form.service_order_id.data != 0 else None
        travel_log.start_date = form.start_date.data
        travel_log.start_odometer = form.start_odometer.data
        travel_log.destination = form.destination.data
        travel_log.purpose = form.purpose.data
        travel_log.notes = form.notes.data
        
        db.session.commit()
        
        # Criar log da ação
        vehicle_plate = Vehicle.query.get(form.vehicle_id.data).plate
        create_log(f'Viagem editada: {vehicle_plate} - {form.destination.data}')
        
        flash('Viagem atualizada com sucesso!', 'success')
        return redirect(url_for('view_travel_log', travel_log_id=travel_log.id))
    
    return render_template(
        'vehicles/travel_logs/edit.html',
        title=f'Editar Viagem #{travel_log.id}',
        form=form,
        travel_log=travel_log
    )

# Rota para finalizar uma viagem
@login_required
def complete_travel_log(travel_log_id):
    """Finaliza uma viagem em andamento"""
    travel_log = VehicleTravelLog.query.get_or_404(travel_log_id)
    
    # Verificar se a viagem já foi concluída
    if travel_log.status != 'em_andamento':
        flash('Esta viagem já foi finalizada.', 'warning')
        return redirect(url_for('view_travel_log', travel_log_id=travel_log.id))
    
    form = VehicleTravelLogCompleteForm()
    
    if form.validate_on_submit():
        # Verificar se o odômetro final é maior que o inicial
        if form.end_odometer.data <= travel_log.start_odometer:
            flash('O odômetro final deve ser maior que o inicial.', 'danger')
            return redirect(url_for('view_travel_log', travel_log_id=travel_log.id))
        
        # Finalizar a viagem
        travel_log.end_date = datetime.utcnow()
        travel_log.end_odometer = form.end_odometer.data
        travel_log.distance = form.end_odometer.data - travel_log.start_odometer
        travel_log.status = 'concluido'
        
        # Atualizar o odômetro do veículo
        vehicle = Vehicle.query.get(travel_log.vehicle_id)
        if vehicle and form.end_odometer.data > vehicle.current_km:
            vehicle.current_km = form.end_odometer.data
        
        db.session.commit()
        
        # Criar log da ação
        vehicle_plate = Vehicle.query.get(travel_log.vehicle_id).plate
        create_log(f'Viagem finalizada: {vehicle_plate} - {travel_log.destination} - {travel_log.distance} km')
        
        flash('Viagem finalizada com sucesso!', 'success')
        return redirect(url_for('view_travel_log', travel_log_id=travel_log.id))
    
    return redirect(url_for('view_travel_log', travel_log_id=travel_log.id))

# Rota para cancelar uma viagem
@login_required
def cancel_travel_log(travel_log_id):
    """Cancela uma viagem em andamento"""
    travel_log = VehicleTravelLog.query.get_or_404(travel_log_id)
    
    # Verificar se a viagem já foi concluída
    if travel_log.status != 'em_andamento':
        flash('Esta viagem não pode ser cancelada pois já foi finalizada.', 'warning')
        return redirect(url_for('view_travel_log', travel_log_id=travel_log.id))
    
    # Cancelar a viagem
    travel_log.status = 'cancelado'
    db.session.commit()
    
    # Criar log da ação
    vehicle_plate = Vehicle.query.get(travel_log.vehicle_id).plate
    create_log(f'Viagem cancelada: {vehicle_plate} - {travel_log.destination}')
    
    flash('Viagem cancelada com sucesso!', 'success')
    return redirect(url_for('travel_logs'))

# Rota para excluir uma viagem
@login_required
def delete_travel_log(travel_log_id):
    """Exclui um registro de viagem"""
    travel_log = VehicleTravelLog.query.get_or_404(travel_log_id)
    
    # Criar log da ação
    vehicle_plate = Vehicle.query.get(travel_log.vehicle_id).plate if travel_log.vehicle_id else "Desconhecido"
    travel_data = f'{vehicle_plate} - {travel_log.destination}'
    
    # Excluir o registro
    db.session.delete(travel_log)
    db.session.commit()
    
    create_log(f'Viagem excluída: {travel_data}')
    
    flash('Registro de viagem excluído com sucesso!', 'success')
    return redirect(url_for('travel_logs'))