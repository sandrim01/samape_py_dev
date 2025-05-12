document.addEventListener('DOMContentLoaded', function() {
    // Inicialização de tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Inicialização de popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });

    // Inicializar elementos de data (datepicker)
    setupDateInputs();

    // Para telas pequenas, controle do sidebar
    const sidebarToggle = document.querySelector('.navbar-toggler');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('show');
        });
    }

    // CPF/CNPJ formatting
    const documentInputs = document.querySelectorAll('.document-input');
    documentInputs.forEach(input => {
        input.addEventListener('input', function() {
            formatDocument(this);
        });
    });

    // Multi-select para equipamentos
    setupEquipmentMultiSelect();

    // Exibir/ocultar campos condicionais
    const conditionalToggles = document.querySelectorAll('.conditional-toggle');
    conditionalToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            const targetId = this.dataset.target;
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.style.display = this.checked ? 'block' : 'none';
            }
        });
    });

    // Atualizar campo de equipamentos quando o cliente mudar
    const clientSelects = document.querySelectorAll('.client-select');
    clientSelects.forEach(select => {
        select.addEventListener('change', function() {
            const clientId = this.value;
            if (clientId) {
                updateEquipmentOptions(clientId);
            }
        });
    });

    // Inicializar contadores de caracteres
    const textareas = document.querySelectorAll('.textarea-counter');
    textareas.forEach(textarea => {
        const counter = document.querySelector(`[data-counter-for="${textarea.id}"]`);
        if (counter) {
            textarea.addEventListener('input', function() {
                counter.textContent = this.value.length;
            });
            // Trigger para definir valor inicial
            counter.textContent = textarea.value.length;
        }
    });

    // Inicializar previewers de tema
    setupThemePreviews();
});

function formatDocument(input) {
    let value = input.value.replace(/\D/g, '');
    
    if (value.length <= 11) {
        // CPF
        if (value.length > 9) {
            value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{0,2})/, '$1.$2.$3-$4');
        } else if (value.length > 6) {
            value = value.replace(/(\d{3})(\d{3})(\d{0,3})/, '$1.$2.$3');
        } else if (value.length > 3) {
            value = value.replace(/(\d{3})(\d{0,3})/, '$1.$2');
        }
    } else {
        // CNPJ
        if (value.length > 12) {
            value = value.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{0,2})/, '$1.$2.$3/$4-$5');
        } else if (value.length > 8) {
            value = value.replace(/(\d{2})(\d{3})(\d{3})(\d{0,4})/, '$1.$2.$3/$4');
        } else if (value.length > 5) {
            value = value.replace(/(\d{2})(\d{3})(\d{0,3})/, '$1.$2.$3');
        } else if (value.length > 2) {
            value = value.replace(/(\d{2})(\d{0,3})/, '$1.$2');
        }
    }
    
    input.value = value;
}

function setupEquipmentMultiSelect() {
    const equipmentSelect = document.getElementById('equipment_select');
    const equipmentIdsInput = document.getElementById('equipment_ids');
    
    if (equipmentSelect && equipmentIdsInput) {
        // Inicializar com valores existentes
        updateEquipmentSelection();
        
        // Adicionar ouvinte de clique para as opções
        equipmentSelect.addEventListener('change', function() {
            updateEquipmentSelection();
        });
    }
}

function updateEquipmentSelection() {
    const equipmentSelect = document.getElementById('equipment_select');
    const equipmentIdsInput = document.getElementById('equipment_ids');
    const selectedEquipment = document.getElementById('selected_equipment');
    
    if (equipmentSelect && equipmentIdsInput && selectedEquipment) {
        // Obter IDs selecionados
        const selectedOptions = Array.from(equipmentSelect.selectedOptions).map(option => option.value);
        
        // Atualizar campo hidden
        equipmentIdsInput.value = selectedOptions.join(',');
        
        // Atualizar lista visual de equipamentos selecionados
        selectedEquipment.innerHTML = '';
        
        if (selectedOptions.length > 0) {
            selectedEquipment.parentElement.style.display = 'block';
            
            selectedOptions.forEach(optionValue => {
                const option = equipmentSelect.querySelector(`option[value="${optionValue}"]`);
                if (option) {
                    const badge = document.createElement('span');
                    badge.className = 'badge bg-primary me-1 mb-1';
                    badge.textContent = option.textContent;
                    selectedEquipment.appendChild(badge);
                }
            });
        } else {
            selectedEquipment.parentElement.style.display = 'none';
        }
    }
}

function updateEquipmentOptions(clientId) {
    // Obter select de equipamentos
    const equipmentSelect = document.getElementById('equipment_select');
    if (!equipmentSelect) return;
    
    // Mostrar o select e esconder a mensagem de aviso
    equipmentSelect.style.display = 'block';
    const equipmentContainer = document.getElementById('equipment-container');
    if (equipmentContainer) {
        const warningMessage = equipmentContainer.querySelector('p.text-muted');
        if (warningMessage) {
            warningMessage.style.display = 'none';
        }
    }
    
    // Fazer requisição AJAX para obter equipamentos do cliente usando a URL em português
    fetch(`/api/cliente/${clientId}/equipamentos`)
        .then(response => response.json())
        .then(data => {
            // Limpar opções atuais
            equipmentSelect.innerHTML = '';
            
            if (data.length === 0) {
                // Se não houver equipamentos, mostrar uma mensagem
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'Nenhum equipamento cadastrado para este cliente';
                option.disabled = true;
                equipmentSelect.appendChild(option);
            } else {
                // Adicionar novas opções
                data.forEach(equipment => {
                    const option = document.createElement('option');
                    option.value = equipment.id;
                    option.textContent = `${equipment.type} - ${equipment.brand || ''} ${equipment.model || ''} ${equipment.serial_number ? `(${equipment.serial_number})` : ''}`;
                    equipmentSelect.appendChild(option);
                });
            }
            
            // Atualizar seleção
            updateEquipmentSelection();
        })
        .catch(error => {
            console.error('Erro ao carregar equipamentos:', error);
            // Em caso de erro, mostrar uma mensagem no select
            equipmentSelect.innerHTML = '';
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'Erro ao carregar equipamentos';
            option.disabled = true;
            equipmentSelect.appendChild(option);
        });
}

function setupDateInputs() {
    // Data picker simples para inputs de data
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (!input.value && input.hasAttribute('data-default-today')) {
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            input.value = `${year}-${month}-${day}`;
        }
    });
}

function setupThemePreviews() {
    // Atualizar previews de tema quando a seleção mudar
    const themeSelect = document.getElementById('theme');
    if (themeSelect) {
        // Criar os previews
        const previewContainer = document.createElement('div');
        previewContainer.className = 'mb-3';
        
        const lightPreview = document.createElement('div');
        lightPreview.className = 'theme-preview light';
        lightPreview.innerHTML = '<div class="p-2 text-dark">Tema Claro</div>';
        
        const darkPreview = document.createElement('div');
        darkPreview.className = 'theme-preview dark';
        darkPreview.innerHTML = '<div class="p-2 text-light">Tema Escuro</div>';
        
        const autoPreview = document.createElement('div');
        autoPreview.className = 'theme-preview auto';
        autoPreview.innerHTML = `
            <div class="row h-100">
                <div class="col-6 p-2 text-dark">Sistema</div>
                <div class="col-6 p-2 text-light">Claro/Escuro</div>
            </div>
        `;
        
        // Ocultar todos os previews inicialmente
        lightPreview.style.display = 'none';
        darkPreview.style.display = 'none';
        autoPreview.style.display = 'none';
        
        // Mostrar o preview correspondente à seleção atual
        const currentTheme = themeSelect.value;
        if (currentTheme === 'light') {
            lightPreview.style.display = 'block';
        } else if (currentTheme === 'dark') {
            darkPreview.style.display = 'block';
        } else if (currentTheme === 'auto') {
            autoPreview.style.display = 'block';
        }
        
        // Adicionar previews ao container
        previewContainer.appendChild(lightPreview);
        previewContainer.appendChild(darkPreview);
        previewContainer.appendChild(autoPreview);
        
        // Inserir container após o select
        themeSelect.parentNode.insertBefore(previewContainer, themeSelect.nextSibling);
        
        // Atualizar previews quando a seleção mudar
        themeSelect.addEventListener('change', function() {
            const selectedTheme = this.value;
            
            // Ocultar todos os previews
            lightPreview.style.display = 'none';
            darkPreview.style.display = 'none';
            autoPreview.style.display = 'none';
            
            // Mostrar o preview correspondente à seleção
            if (selectedTheme === 'light') {
                lightPreview.style.display = 'block';
            } else if (selectedTheme === 'dark') {
                darkPreview.style.display = 'block';
            } else if (selectedTheme === 'auto') {
                autoPreview.style.display = 'block';
            }
        });
    }
}