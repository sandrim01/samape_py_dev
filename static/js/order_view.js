// Código para o modal de visualização de ordens de serviço
document.addEventListener('DOMContentLoaded', function() {
    // Evento de clique para todos os botões de visualização
    document.querySelectorAll('.view-order-modal').forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Obter o ID da OS
            var orderId = this.getAttribute('data-id');
            console.log("Visualizando OS #" + orderId);
            
            // Redirecionar para a página de visualização básica
            window.location.href = '/os/' + orderId + '/basico';
        });
    });
});