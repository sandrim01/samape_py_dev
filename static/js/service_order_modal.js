// Funcionalidade para o modal de visualização rápida de Ordens de Serviço
$(document).ready(function() {
    // Adicionar event listener para os botões de visualização de OS modal
    $('.view-order-modal').click(function(e) {
        e.preventDefault();
        let orderId = $(this).data('id');
        
        // Mostrar o modal Bootstrap
        var modal = $('#viewOrderModal');
        modal.modal('show');
        
        // Atualizar título e mostrar loading
        modal.find('.modal-title').text('Detalhes da OS #' + orderId);
        modal.find('.modal-body').html(`
            <div class="text-center p-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
                <p class="mt-2">Carregando informações da OS #${orderId}...</p>
            </div>
        `);
        
        // Buscar os detalhes da OS usando a rota view_service_order_basic
        $.ajax({
            url: `/os/${orderId}/basico`,
            type: 'GET',
            success: function(response) {
                // Extrair o conteúdo principal da página usando jQuery
                var content = $(response).find('.container');
                
                // Criar conteúdo formatado para o modal
                var modalContent = `
                    <div class="service-order-details">
                        <div class="row mb-4">
                            <div class="col-md-6">
                                <h5>Informações Gerais</h5>
                                <div class="card">
                                    <div class="card-body">
                                        <p><strong>Cliente:</strong> ${content.find('.client-name').text() || 'Não definido'}</p>
                                        <p><strong>Responsável:</strong> ${content.find('.responsible-name').text() || 'Não definido'}</p>
                                        <p><strong>Status:</strong> ${content.find('.status-badge').text() || 'Não definido'}</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <h5>Datas</h5>
                                <div class="card">
                                    <div class="card-body">
                                        <p><strong>Abertura:</strong> ${content.find('.created-date').text() || 'Não definida'}</p>
                                        <p><strong>Fechamento:</strong> ${content.find('.closed-date').text() || 'Não finalizada'}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mb-4">
                            <div class="col-12">
                                <h5>Descrição</h5>
                                <div class="card">
                                    <div class="card-body">
                                        <p>${content.find('.service-description').text() || 'Sem descrição'}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mb-4">
                            <div class="col-12">
                                <h5>Equipamentos</h5>
                                <div class="card">
                                    <div class="card-body">
                                        ${content.find('.equipment-list').html() || '<p>Nenhum equipamento associado</p>'}
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
                
                // Atualizar o conteúdo do modal com o HTML formatado
                modal.find('.modal-body').html(modalContent);
            },
            error: function() {
                // Em caso de erro, mostrar mensagem simplificada
                modal.find('.modal-body').html(`
                    <div class="alert alert-danger">
                        <p><i class="fas fa-exclamation-triangle me-2"></i> Não foi possível carregar os detalhes da OS #${orderId}.</p>
                        <p>Tente acessar a <a href="/os/${orderId}/basico" class="alert-link">página completa</a>.</p>
                        <div class="text-end mt-3">
                            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Fechar</button>
                        </div>
                    </div>
                `);
            }
        });
    });
});