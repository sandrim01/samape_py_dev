// Funcionalidade do modal de visualização de OS
document.addEventListener('DOMContentLoaded', function() {
    // Adicionar listeners para todos os botões de visualização
    document.querySelectorAll('.view-order-modal').forEach(function(button) {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            
            // Obter o ID da OS
            var orderId = this.getAttribute('data-id');
            console.log("Visualizando OS ID: " + orderId);
            
            // Referência ao modal
            var modal = document.getElementById('viewOrderModal');
            var myModal = new bootstrap.Modal(modal);
            
            // Configurar título e loading
            modal.querySelector('.modal-title').textContent = 'Detalhes da OS #' + orderId;
            modal.querySelector('.modal-body').innerHTML = `
                <div class="text-center p-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Carregando...</span>
                    </div>
                    <p class="mt-2">Carregando detalhes da OS #${orderId}...</p>
                </div>
            `;
            
            // Mostrar o modal
            myModal.show();
            
            // Carregar os dados da OS
            fetch('/os/' + orderId + '/basico')
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Erro ao carregar dados');
                    }
                    return response.text();
                })
                .then(html => {
                    // Parsear o HTML
                    var parser = new DOMParser();
                    var doc = parser.parseFromString(html, 'text/html');
                    
                    // Extrair os dados
                    var clientName = doc.querySelector('.client-name') ? 
                        doc.querySelector('.client-name').textContent.trim() : 'Não especificado';
                    
                    var responsibleName = doc.querySelector('.responsible-name') ? 
                        doc.querySelector('.responsible-name').textContent.trim() : 'Não especificado';
                    
                    var statusText = doc.querySelector('.status-badge') ? 
                        doc.querySelector('.status-badge').textContent.trim() : 'Não especificado';
                    
                    var createdDate = doc.querySelector('.created-date') ? 
                        doc.querySelector('.created-date').textContent.trim() : 'Não especificada';
                    
                    var closedDate = doc.querySelector('.closed-date') ? 
                        doc.querySelector('.closed-date').textContent.trim() : 'Não finalizada';
                    
                    var description = doc.querySelector('.service-description') ? 
                        doc.querySelector('.service-description').textContent.trim() : 'Sem descrição';
                    
                    var equipmentList = doc.querySelector('.equipment-list') ? 
                        doc.querySelector('.equipment-list').innerHTML : '<p>Nenhum equipamento associado</p>';
                    
                    // Criar o conteúdo do modal
                    var modalContent = `
                        <div class="service-order-details">
                            <div class="row mb-4">
                                <div class="col-md-6">
                                    <h5>Informações Gerais</h5>
                                    <div class="card">
                                        <div class="card-body">
                                            <p><strong>Cliente:</strong> ${clientName}</p>
                                            <p><strong>Responsável:</strong> ${responsibleName}</p>
                                            <p><strong>Status:</strong> ${statusText}</p>
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
                                            <p>${description}</p>
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
                    
                    // Atualizar o modal
                    modal.querySelector('.modal-body').innerHTML = modalContent;
                })
                .catch(error => {
                    console.error('Erro:', error);
                    // Mostrar mensagem de erro
                    modal.querySelector('.modal-body').innerHTML = `
                        <div class="alert alert-danger">
                            <p><i class="fas fa-exclamation-triangle me-2"></i> Não foi possível carregar os detalhes da OS #${orderId}.</p>
                            <p>Tente acessar a <a href="/os/${orderId}" class="alert-link">página completa</a>.</p>
                        </div>
                        <div class="text-end mt-3">
                            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Fechar</button>
                        </div>
                    `;
                });
        });
    });
});