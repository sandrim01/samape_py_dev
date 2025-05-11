document.addEventListener('DOMContentLoaded', function() {
    // Setup tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Setup popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Client selection in service order form
    const clientSelect = document.getElementById('client_id');
    if (clientSelect) {
        clientSelect.addEventListener('change', function() {
            updateEquipmentOptions(this.value);
        });
        
        // Initial load of equipment for selected client
        if (clientSelect.value) {
            updateEquipmentOptions(clientSelect.value);
        }
    }

    // Equipment multi-select functionality
    setupEquipmentMultiSelect();

    // Client document formatting (CPF/CNPJ)
    const documentInput = document.getElementById('document');
    if (documentInput) {
        documentInput.addEventListener('input', function(e) {
            const doc = this.value.replace(/\D/g, '');
            
            if (doc.length <= 11) { // CPF
                this.value = formatCPF(doc);
            } else { // CNPJ
                this.value = formatCNPJ(doc);
            }
        });
    }

    // Date picker for financial entries
    const dateInput = document.getElementById('date');
    if (dateInput) {
        // Set default date to today if empty
        if (!dateInput.value) {
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            dateInput.value = `${year}-${month}-${day}`;
        }
    }

    // Search functionality
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            // Remove empty fields from form before submitting
            const inputs = this.querySelectorAll('input, select');
            inputs.forEach(input => {
                if (!input.value) {
                    input.name = '';
                }
            });
        });
    }

    // Confirmation dialogs
    document.querySelectorAll('.confirm-action').forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm(this.getAttribute('data-confirm-message') || 'Tem certeza que deseja realizar esta ação?')) {
                e.preventDefault();
            }
        });
    });
});

// Function to update equipment options when client changes
function updateEquipmentOptions(clientId) {
    if (!clientId) return;
    
    const equipmentSelect = document.getElementById('equipment_ids');
    if (!equipmentSelect) return;
    
    // Clear current selection
    document.querySelectorAll('.equipment-item').forEach(item => {
        item.remove();
    });
    
    // Fetch equipment for selected client
    fetch(`/api/cliente/${clientId}/equipamentos`)
        .then(response => response.json())
        .then(data => {
            const equipmentContainer = document.getElementById('equipment-container');
            
            if (data.length === 0) {
                equipmentContainer.innerHTML = '<p>Nenhum equipamento cadastrado para este cliente.</p>';
                return;
            }
            
            // Create equipment checkboxes
            let html = '<div class="list-group mt-2">';
            data.forEach(equipment => {
                const equipmentInfo = `${equipment.type} ${equipment.brand ? '- ' + equipment.brand : ''} ${equipment.model ? '- ' + equipment.model : ''} ${equipment.serial_number ? '(' + equipment.serial_number + ')' : ''}`;
                html += `
                <div class="list-group-item equipment-item">
                    <div class="form-check">
                        <input class="form-check-input equipment-checkbox" type="checkbox" value="${equipment.id}" id="equipment-${equipment.id}">
                        <label class="form-check-label" for="equipment-${equipment.id}">
                            ${equipmentInfo}
                        </label>
                    </div>
                </div>`;
            });
            html += '</div>';
            
            equipmentContainer.innerHTML = html;
            
            // Setup event handlers for newly created checkboxes
            document.querySelectorAll('.equipment-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', updateEquipmentSelection);
            });
            
            // If editing, restore previously selected equipment
            if (equipmentSelect.value) {
                const selectedIds = equipmentSelect.value.split(',');
                selectedIds.forEach(id => {
                    const checkbox = document.getElementById(`equipment-${id}`);
                    if (checkbox) checkbox.checked = true;
                });
            }
            
            updateEquipmentSelection();
        })
        .catch(error => {
            console.error('Error fetching equipment:', error);
        });
}

// Update the hidden equipment_ids field based on checkbox selection
function updateEquipmentSelection() {
    const selectedEquipment = [];
    document.querySelectorAll('.equipment-checkbox:checked').forEach(checkbox => {
        selectedEquipment.push(checkbox.value);
    });
    
    const equipmentSelect = document.getElementById('equipment_ids');
    equipmentSelect.value = selectedEquipment.join(',');
}

// Setup the UI elements for equipment multi-select
function setupEquipmentMultiSelect() {
    const equipmentContainer = document.getElementById('equipment-container');
    if (!equipmentContainer) return;
    
    // Update equipment list when the page loads
    const clientSelect = document.getElementById('client_id');
    if (clientSelect && clientSelect.value) {
        updateEquipmentOptions(clientSelect.value);
    }
}

// Format CPF (Brazilian individual taxpayer registry)
function formatCPF(cpf) {
    cpf = cpf.slice(0, 11);
    
    if (cpf.length <= 3) {
        return cpf;
    } else if (cpf.length <= 6) {
        return cpf.slice(0, 3) + '.' + cpf.slice(3);
    } else if (cpf.length <= 9) {
        return cpf.slice(0, 3) + '.' + cpf.slice(3, 6) + '.' + cpf.slice(6);
    } else {
        return cpf.slice(0, 3) + '.' + cpf.slice(3, 6) + '.' + cpf.slice(6, 9) + '-' + cpf.slice(9);
    }
}

// Format CNPJ (Brazilian company taxpayer registry)
function formatCNPJ(cnpj) {
    cnpj = cnpj.slice(0, 14);
    
    if (cnpj.length <= 2) {
        return cnpj;
    } else if (cnpj.length <= 5) {
        return cnpj.slice(0, 2) + '.' + cnpj.slice(2);
    } else if (cnpj.length <= 8) {
        return cnpj.slice(0, 2) + '.' + cnpj.slice(2, 5) + '.' + cnpj.slice(5);
    } else if (cnpj.length <= 12) {
        return cnpj.slice(0, 2) + '.' + cnpj.slice(2, 5) + '.' + cnpj.slice(5, 8) + '/' + cnpj.slice(8);
    } else {
        return cnpj.slice(0, 2) + '.' + cnpj.slice(2, 5) + '.' + cnpj.slice(5, 8) + '/' + cnpj.slice(8, 12) + '-' + cnpj.slice(12);
    }
}
