// Funcionalidade para cálculo de R$/KM em ordens de serviço
document.addEventListener('DOMContentLoaded', function() {
    // Configuração para mostrar/esconder seções do veículo e calcular R$/KM
    const vehicleTypeSelect = document.getElementById('vehicle_type');
    const fleetVehicleSection = document.getElementById('fleet-vehicle-section');
    const kmCalculationSection = document.getElementById('km-calculation-section');
    const distanceInput = document.getElementById('distance_km');
    const costPerKmInput = document.getElementById('cost_per_km');
    const totalVehicleCostInput = document.getElementById('total_vehicle_cost');
    const estimatedValueInput = document.getElementById('estimated_value');
    
    if (vehicleTypeSelect) {
        vehicleTypeSelect.addEventListener('change', function() {
            const selectedType = this.value;
            
            // Mostrar/esconder seção de veículo da frota
            if (selectedType === 'fleet') {
                fleetVehicleSection.classList.remove('d-none');
            } else {
                fleetVehicleSection.classList.add('d-none');
            }
            
            // Mostrar/esconder seção de cálculo de KM
            if (selectedType === 'fleet' || selectedType === 'rental') {
                kmCalculationSection.classList.remove('d-none');
                
                // Para veículos da frota, podemos pré-configurar alguns valores padrão
                if (selectedType === 'fleet') {
                    // Você pode definir um custo por km padrão para veículos da frota, se desejar
                    costPerKmInput.value = costPerKmInput.value || '1.50';
                } else {
                    // Para veículos alugados, o custo pode ser diferente
                    costPerKmInput.value = costPerKmInput.value || '2.50';
                }
            } else {
                kmCalculationSection.classList.add('d-none');
            }
            
            // Recalcular o custo total se necessário
            calculateTotalVehicleCost();
        });
    }
    
    // Configurar cálculo automático do custo total do veículo
    if (distanceInput && costPerKmInput && totalVehicleCostInput) {
        distanceInput.addEventListener('input', calculateTotalVehicleCost);
        costPerKmInput.addEventListener('input', calculateTotalVehicleCost);
        
        // Atualizar valor estimado da OS quando o custo do veículo for calculado
        totalVehicleCostInput.addEventListener('change', updateEstimatedValue);
    }
    
    function calculateTotalVehicleCost() {
        const distance = parseFloat(distanceInput.value) || 0;
        const costPerKm = parseFloat(costPerKmInput.value) || 0;
        
        if (distance > 0 && costPerKm > 0) {
            const total = distance * costPerKm;
            totalVehicleCostInput.value = total.toFixed(2);
            
            // Atualizar o valor estimado total da OS
            updateEstimatedValue();
        } else {
            totalVehicleCostInput.value = '';
        }
    }
    
    function updateEstimatedValue() {
        // Se o usuário já inseriu um valor estimado, adicionamos o custo do veículo
        // Se não, o valor do veículo se torna o valor estimado
        const currentEstimatedValue = parseFloat(estimatedValueInput.value) || 0;
        const vehicleCost = parseFloat(totalVehicleCostInput.value) || 0;
        
        if (vehicleCost > 0) {
            if (currentEstimatedValue > 0) {
                // Verificar se é necessário atualizar o valor estimado (se o usuário não mudou manualmente)
                const suggestion = confirm("Deseja atualizar o valor estimado da OS incluindo o custo do veículo?");
                if (suggestion) {
                    // Atualize apenas se o usuário confirmar
                    estimatedValueInput.value = (currentEstimatedValue + vehicleCost).toFixed(2);
                }
            } else {
                // Se não houver valor estimado, use o custo do veículo como valor inicial
                estimatedValueInput.value = vehicleCost.toFixed(2);
            }
        }
    }
});