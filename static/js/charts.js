document.addEventListener('DOMContentLoaded', function() {
    setupCharts();
});

// Define chart colors to match the theme
const chartColors = {
    pink: '#f85d8e',
    green: '#37d09e',
    orange: '#ff9353',
    blue: '#4285f4',
    darkBg: '#1e1e1e',
    cardBg: '#242424',
    textColor: '#f0f0f0',
    mutedText: '#a0a0a0',
    gridColor: 'rgba(255, 255, 255, 0.05)'
};

function setupCharts() {
    // Setup default chart options to match dark theme
    Chart.defaults.color = chartColors.mutedText;
    Chart.defaults.borderColor = chartColors.gridColor;
    
    // Dashboard Charts
    if (document.getElementById('dashboard')) {
        setupDashboardCharts();
    }
    
    // Financial Charts
    if (document.getElementById('financial-charts')) {
        setupFinancialCharts();
    }
    
    // Setup the serviceOrdersDistribution chart from the dashboard.html
    const serviceOrdersDistribution = document.getElementById('serviceOrdersDistribution');
    if (serviceOrdersDistribution) {
        setupAreaChart();
    }
}

function setupAreaChart() {
    const ctx = document.getElementById('serviceOrdersDistribution').getContext('2d');
    
    // Create gradient background
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(66, 133, 244, 0.7)');   
    gradient.addColorStop(1, 'rgba(66, 133, 244, 0.1)');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
            datasets: [{
                label: 'Faturamento',
                data: [65, 59, 80, 81, 56, 55, 40, 56, 68, 75, 80, 90],
                backgroundColor: gradient,
                borderColor: chartColors.blue,
                borderWidth: 2,
                pointBackgroundColor: chartColors.blue,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: chartColors.gridColor
                    },
                    ticks: {
                        color: chartColors.mutedText
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: chartColors.mutedText
                    }
                }
            }
        }
    });
}

function setupDashboardCharts() {
    setupServiceOrderDistributionChart();
    setupMonthlyFinancialChart();
}

function setupServiceOrderDistributionChart() {
    const ctx = document.getElementById('serviceOrderDistributionChart');
    if (!ctx) return;
    
    // Get data from elements
    const aberta = parseInt(document.getElementById('os-aberta')?.dataset.count || 0);
    const emAndamento = parseInt(document.getElementById('os-em-andamento')?.dataset.count || 0);
    const fechada = parseInt(document.getElementById('os-fechada')?.dataset.count || 0);
    
    const data = {
        labels: ['Aberta', 'Em Andamento', 'Fechada'],
        datasets: [{
            data: [aberta, emAndamento, fechada],
            backgroundColor: [chartColors.pink, chartColors.orange, chartColors.green],
            borderWidth: 0,
            borderRadius: 4
        }]
    };
    
    const config = {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: chartColors.textColor,
                        padding: 15,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
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
    const income = parseFloat(document.getElementById('monthly-income')?.dataset.value || 0);
    const expenses = parseFloat(document.getElementById('monthly-expenses')?.dataset.value || 0);
    
    const data = {
        labels: ['Entradas', 'Saídas', 'Saldo'],
        datasets: [{
            label: 'Valor (R$)',
            data: [income, expenses, income - expenses],
            backgroundColor: [
                chartColors.green,
                chartColors.pink,
                chartColors.blue
            ],
            borderWidth: 0,
            borderRadius: 4
        }]
    };
    
    const config = {
        type: 'bar',
        data: data,
        options: {
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: chartColors.gridColor
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            responsive: true,
            plugins: {
                legend: {
                    display: false
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
    
    // Create gradient for the area under the line
    const gradientBlue = ctx.getContext('2d').createLinearGradient(0, 0, 0, 300);
    gradientBlue.addColorStop(0, 'rgba(66, 133, 244, 0.3)');   
    gradientBlue.addColorStop(1, 'rgba(66, 133, 244, 0.0)');
    
    // Prepare chart data
    const data = {
        labels: monthLabels,
        datasets: [
            {
                label: 'Entradas',
                data: monthlyData.map(d => d.income),
                backgroundColor: chartColors.green,
                borderColor: chartColors.green,
                borderWidth: 0,
                borderRadius: 4,
                type: 'bar'
            },
            {
                label: 'Saídas',
                data: monthlyData.map(d => d.expenses),
                backgroundColor: chartColors.pink,
                borderColor: chartColors.pink,
                borderWidth: 0,
                borderRadius: 4,
                type: 'bar'
            },
            {
                label: 'Saldo',
                data: monthlyData.map(d => d.balance),
                backgroundColor: gradientBlue,
                borderColor: chartColors.blue,
                borderWidth: 2,
                tension: 0.4,
                pointBackgroundColor: chartColors.blue,
                pointRadius: 4,
                pointHoverRadius: 6,
                type: 'line',
                yAxisID: 'y1',
                fill: true
            }
        ]
    };
    
    const config = {
        data: data,
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: false
                },
                tooltip: {
                    backgroundColor: chartColors.cardBg,
                    borderColor: chartColors.blue,
                    borderWidth: 1,
                    titleColor: chartColors.textColor,
                    bodyColor: chartColors.textColor,
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
                },
                legend: {
                    labels: {
                        color: chartColors.textColor,
                        padding: 15,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: chartColors.mutedText
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    grid: {
                        color: chartColors.gridColor
                    },
                    ticks: {
                        color: chartColors.mutedText
                    },
                    title: {
                        display: true,
                        text: 'Valor (R$)',
                        color: chartColors.mutedText
                    }
                },
                y1: {
                    position: 'right',
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false,
                        color: chartColors.gridColor
                    },
                    ticks: {
                        color: chartColors.mutedText
                    },
                    title: {
                        display: true,
                        text: 'Saldo (R$)',
                        color: chartColors.mutedText
                    }
                }
            }
        }
    };
    
    new Chart(ctx, config);
}