// Function to initialize charts on specific pages
function setupCharts() {
    if (window.location.pathname === '/dashboard') {
        setupDashboardCharts();
    } else if (window.location.pathname === '/financeiro') {
        setupFinancialCharts();
    }
}

// Dashboard charts
function setupDashboardCharts() {
    setupServiceOrderDistributionChart();
    setupMonthlyFinancialChart();
}

function setupServiceOrderDistributionChart() {
    const ctx = document.getElementById('serviceOrdersDistribution');
    
    if (!ctx) return;
    
    const labels = JSON.parse(ctx.getAttribute('data-labels'));
    const counts = JSON.parse(ctx.getAttribute('data-counts'));
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: [
                    '#ffc107', // Abertas
                    '#17a2b8', // Em andamento
                    '#28a745'  // Fechadas
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function setupMonthlyFinancialChart() {
    const ctx = document.getElementById('monthlyFinancial');
    
    if (!ctx) return;
    
    const income = parseFloat(ctx.getAttribute('data-income'));
    const expenses = parseFloat(ctx.getAttribute('data-expenses'));
    const balance = income - expenses;
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Receitas', 'Despesas', 'Saldo'],
            datasets: [{
                data: [income, expenses, balance],
                backgroundColor: [
                    '#28a745', // Receitas
                    '#dc3545', // Despesas
                    balance >= 0 ? '#17a2b8' : '#fd7e14' // Saldo
                ],
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
                            const value = context.parsed.y;
                            return 'R$ ' + value.toFixed(2).replace('.', ',');
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

// Financial page charts
function setupFinancialCharts() {
    setupMonthlyBalanceChart();
}

function setupMonthlyBalanceChart() {
    const ctx = document.getElementById('monthlyBalanceChart');
    
    if (!ctx) return;
    
    const income = parseFloat(ctx.getAttribute('data-income'));
    const expenses = parseFloat(ctx.getAttribute('data-expenses'));
    
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Receitas', 'Despesas'],
            datasets: [{
                data: [income, expenses],
                backgroundColor: ['#28a745', '#dc3545'],
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
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((acc, data) => acc + data, 0);
                            const percentage = Math.round((value * 100) / total);
                            return `R$ ${value.toFixed(2).replace('.', ',')} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', setupCharts);
