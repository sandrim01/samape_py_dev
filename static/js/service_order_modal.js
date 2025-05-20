// Funcionalidade para o modal de visualização rápida de Ordens de Serviço
document.addEventListener('DOMContentLoaded', function() {
    // Adicionar event listener para os botões de visualização de OS modal
    document.querySelectorAll('.view-order-modal').forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Obter o ID da OS do atributo data-id
            var orderId = this.getAttribute('data-id');
            
            // Referência ao modal e criação da instância Bootstrap
            var modalElement = document.getElementById('viewOrderModal');
            var bsModal = new bootstrap.Modal(modalElement);
            
            // Atualizar título
            modalElement.querySelector('.modal-title').textContent = 'Detalhes da OS #' + orderId;
            
            // Mostrar loading
            modalElement.querySelector('.modal-body').innerHTML = `
                <div class="text-center p-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Carregando...</span>
                    </div>
                    <p class="mt-2">Carregando informações da OS #${orderId}...</p>
                </div>
            `;
            
            // Mostrar o modal
            bsModal.show();
            
            // Buscar os detalhes da OS via AJAX
            fetch(`/os/${orderId}/basico`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Erro ao carregar dados');
                    }
                    return response.text();
                })
                .then(html => {
                    // Parse o HTML retornado
                    var parser = new DOMParser();
                    var doc = parser.parseFromString(html, 'text/html');
                    
                    // Extrair informações que precisamos
                    var content = doc.querySelector('.container');
                    
                    // Se não conseguir encontrar o container, use o body
                    if (!content) {
                        content = doc.body;
                    }
                    
                    // Procurar elementos com classes específicas
                    var clientName = content.querySelector('.client-name') ? 
                        content.querySelector('.client-name').textContent : 'Não definido';
                    
                    var responsibleName = content.querySelector('.responsible-name') ? 
                        content.querySelector('.responsible-name').textContent : 'Não definido';
                    
                    var statusBadge = content.querySelector('.status-badge') ? 
                        content.querySelector('.status-badge').textContent : 'Não definido';
                    
                    var createdDate = content.querySelector('.created-date') ? 
                        content.querySelector('.created-date').textContent : 'Não definida';
                    
                    var closedDate = content.querySelector('.closed-date') ? 
                        content.querySelector('.closed-date').textContent : 'Não finalizada';
                    
                    var serviceDesc = content.querySelector('.service-description') ? 
                        content.querySelector('.service-description').textContent : 'Sem descrição';
                    
                    var equipmentList = content.querySelector('.equipment-list') ? 
                        content.querySelector('.equipment-list').innerHTML : '<p>Nenhum equipamento associado</p>';
                    
                    // Criar conteúdo formatado para o modal
                    var modalContent = `
                        <div class="service-order-details">
                            <div class="row mb-4">
                                <div class="col-md-6">
                                    <h5>Informações Gerais</h5>
                                    <div class="card">
                                        <div class="card-body">
                                            <p><strong>Cliente:</strong> ${clientName}</p>
                                            <p><strong>Responsável:</strong> ${responsibleName}</p>
                                            <p><strong>Status:</strong> ${statusBadge}</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <h5>Datas</h5>
                                    <div class="card">
                                        <div class="card-body">
                                            <p><strong>Abertura:</strong> ${createdDate}</p>
                                            <p><strong>Fechamento:</strong> ${closedDate}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row mb-4">
                                <div class="col-12">
                                    <h5>Descrição</h5>
                                    <div class="card">
                                        <div class="card-body">
                                            <p>${serviceDesc}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row mb-4">
                                <div class="col-12">
                                    <h5>Equipamentos</h5>
                                    <div class="card">
                                        <div class="card-body">
                                            ${equipmentList}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row">
                                <div class="col-12 text-end">
                                    <a href="/os/${orderId}" class="btn btn-primary">Ver Detalhes Completos</a>
                                    <a href="/os/${orderId}/editar" class="btn btn-secondary">Editar OS</a>
                                    <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Fechar</button>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    // Atualizar o conteúdo do modal
                    modalElement.querySelector('.modal-body').innerHTML = modalContent;
                })
                .catch(error => {
                    console.error('Erro:', error);
                    // Em caso de erro, mostrar mensagem simplificada
                    modalElement.querySelector('.modal-body').innerHTML = `
                        <div class="alert alert-danger">
                            <p><i class="fas fa-exclamation-triangle me-2"></i> Não foi possível carregar os detalhes da OS #${orderId}.</p>
                            <p>Tente acessar a <a href="/os/${orderId}/basico" class="alert-link">página completa</a>.</p>
                            <div class="text-end mt-3">
                                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Fechar</button>
                            </div>
                        </div>
                    `;
                });
        });
    });
});