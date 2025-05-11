document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts if they exist on the page
    if (document.getElementById('serviceOrderChart')) {
        initServiceOrderChart();
    }
    
    if (document.getElementById('financialChart')) {
        initFinancialChart();
    }
});

function initServiceOrderChart() {
    // Get data from HTML data attributes
    const chartElement = document.getElementById('serviceOrderChart');
    const open = parseInt(chartElement.getAttribute('data-open'));
    const inProgress = parseInt(chartElement.getAttribute('data-in-progress'));
    const closed = parseInt(chartElement.getAttribute('data-closed'));
    
    // Create chart
    const ctx = chartElement.getContext('2d');
    const serviceOrderChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Abertas', 'Em Andamento', 'Fechadas'],
            datasets: [{
                data: [open, inProgress, closed],
                backgroundColor: ['#ffc107', '#17a2b8', '#28a745'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((acc, curr) => acc + curr, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function initFinancialChart() {
    // Get data from HTML data attributes
    const chartElement = document.getElementById('financialChart');
    const income = parseFloat(chartElement.getAttribute('data-income'));
    const expenses = parseFloat(chartElement.getAttribute('data-expenses'));
    
    // Create chart
    const ctx = chartElement.getContext('2d');
    const financialChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Receitas', 'Despesas', 'Saldo'],
            datasets: [{
                data: [income, expenses, income - expenses],
                backgroundColor: ['#28a745', '#dc3545', '#007bff'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'R$ ' + context.raw.toFixed(2).replace('.', ',');
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return 'R$ ' + value.toFixed(2).replace('.', ',');
                        }
                    }
                }
            }
        }
    });
}
