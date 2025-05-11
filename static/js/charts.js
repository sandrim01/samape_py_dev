document.addEventListener('DOMContentLoaded', function() {
    setupCharts();
});

function setupCharts() {
    // Dashboard Charts
    if (document.getElementById('dashboard')) {
        setupDashboardCharts();
    }
    
    // Financial Charts
    if (document.getElementById('financial-charts')) {
        setupFinancialCharts();
    }
}

function setupDashboardCharts() {
    setupServiceOrderDistributionChart();
    setupMonthlyFinancialChart();
}

function setupServiceOrderDistributionChart() {
    const ctx = document.getElementById('serviceOrderDistributionChart');
    if (!ctx) return;
    
    // Get data from elements
    const aberta = parseInt(document.getElementById('os-aberta').dataset.count || 0);
    const emAndamento = parseInt(document.getElementById('os-em-andamento').dataset.count || 0);
    const fechada = parseInt(document.getElementById('os-fechada').dataset.count || 0);
    
    const data = {
        labels: ['Aberta', 'Em Andamento', 'Fechada'],
        datasets: [{
            data: [aberta, emAndamento, fechada],
            backgroundColor: ['#dc3545', '#ffc107', '#28a745'],
            borderWidth: 1
        }]
    };
    
    const config = {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                title: {
                    display: true,
                    text: 'Distribuição de Ordens de Serviço'
                }
            }
        },
    };
    
    new Chart(ctx, config);
}

function setupMonthlyFinancialChart() {
    const ctx = document.getElementById('monthlyFinancialChart');
    if (!ctx) return;
    
    // Get financial data
    const income = parseFloat(document.getElementById('monthly-income').dataset.value || 0);
    const expenses = parseFloat(document.getElementById('monthly-expenses').dataset.value || 0);
    
    const data = {
        labels: ['Entradas', 'Saídas', 'Saldo'],
        datasets: [{
            label: 'Valor (R$)',
            data: [income, expenses, income - expenses],
            backgroundColor: [
                'rgba(40, 167, 69, 0.7)',
                'rgba(220, 53, 69, 0.7)',
                'rgba(14, 30, 64, 0.7)'
            ],
            borderColor: [
                'rgb(40, 167, 69)',
                'rgb(220, 53, 69)',
                'rgb(14, 30, 64)'
            ],
            borderWidth: 1
        }]
    };
    
    const config = {
        type: 'bar',
        data: data,
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Resumo Financeiro do Mês'
                }
            }
        },
    };
    
    new Chart(ctx, config);
}

function setupFinancialCharts() {
    setupMonthlyBalanceChart();
}

function setupMonthlyBalanceChart() {
    const ctx = document.getElementById('monthlyBalanceChart');
    if (!ctx) return;
    
    // Get monthly data
    const monthlyData = [];
    const monthLabels = [];
    
    // Collect data from HTML
    document.querySelectorAll('.monthly-data').forEach(el => {
        const month = el.dataset.month;
        const income = parseFloat(el.dataset.income || 0);
        const expenses = parseFloat(el.dataset.expenses || 0);
        const balance = income - expenses;
        
        monthLabels.push(month);
        monthlyData.push({
            income: income,
            expenses: expenses,
            balance: balance
        });
    });
    
    // Prepare chart data
    const data = {
        labels: monthLabels,
        datasets: [
            {
                label: 'Entradas',
                data: monthlyData.map(d => d.income),
                backgroundColor: 'rgba(40, 167, 69, 0.5)',
                borderColor: 'rgb(40, 167, 69)',
                borderWidth: 1,
                type: 'bar'
            },
            {
                label: 'Saídas',
                data: monthlyData.map(d => d.expenses),
                backgroundColor: 'rgba(220, 53, 69, 0.5)',
                borderColor: 'rgb(220, 53, 69)',
                borderWidth: 1,
                type: 'bar'
            },
            {
                label: 'Saldo',
                data: monthlyData.map(d => d.balance),
                backgroundColor: 'rgba(14, 30, 64, 0.1)',
                borderColor: 'rgb(14, 30, 64)',
                borderWidth: 2,
                type: 'line',
                yAxisID: 'y1'
            }
        ]
    };
    
    const config = {
        data: data,
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Balanço Mensal'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Valor (R$)'
                    }
                },
                y1: {
                    position: 'right',
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false
                    },
                    title: {
                        display: true,
                        text: 'Saldo (R$)'
                    }
                }
            }
        }
    };
    
    new Chart(ctx, config);
}