/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class WmsDashboard extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            warehouses: [],
            selectedWarehouse: null,
            dashboardData: null,
            loading: true,
        });

        onMounted(() => {
            this.loadWarehouses();
            this.autoRefreshInterval = setInterval(() => {
                if (this.state.selectedWarehouse) {
                    this.loadDashboardData();
                }
            }, 60000); // Auto-refresh every 60 seconds
        });

        onWillUnmount(() => {
            if (this.autoRefreshInterval) {
                clearInterval(this.autoRefreshInterval);
            }
        });
    }

    async loadWarehouses() {
        try {
            const warehouses = await this.rpc("/web/dataset/call_kw/wms.dashboard/get_warehouse_list", {
                model: "wms.dashboard",
                method: "get_warehouse_list",
                args: [[]],
                kwargs: {},
            });
            
            this.state.warehouses = warehouses;
            
            if (warehouses.length > 0) {
                this.state.selectedWarehouse = warehouses[0].id;
                this.loadDashboardData();
            }
        } catch (error) {
            console.error("Error loading warehouses:", error);
        }
    }

    async loadDashboardData() {
        this.state.loading = true;
        
        try {
            const data = await this.rpc("/web/dataset/call_kw/wms.dashboard/get_dashboard_data", {
                model: "wms.dashboard",
                method: "get_dashboard_data",
                args: [[]],
                kwargs: { warehouse_id: this.state.selectedWarehouse },
            });
            
            this.state.dashboardData = data;
            this.updateDashboard(data);
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    updateDashboard(data) {
        // Update KPI cards
        document.getElementById('total_stock').textContent = this.formatNumber(data.stock_overview.total_quantity);
        document.getElementById('product_count').textContent = `${data.stock_overview.product_count} products`;
        document.getElementById('available_stock').textContent = this.formatNumber(data.stock_overview.available_quantity);
        document.getElementById('stock_value').textContent = `Value: ${this.formatCurrency(data.stock_overview.total_value)}`;
        document.getElementById('reserved_stock').textContent = this.formatNumber(data.stock_overview.reserved_quantity);
        document.getElementById('capacity_percent').textContent = `${data.capacity_data.warehouse_percent.toFixed(1)}%`;
        document.getElementById('capacity_text').textContent = `${this.formatNumber(data.capacity_data.warehouse_used)}/${this.formatNumber(data.capacity_data.warehouse_capacity)}`;

        // Update operations
        document.getElementById('receipts_pending').textContent = data.operations_data.receipts.pending;
        document.getElementById('receipts_today').textContent = data.operations_data.receipts.completed_today;
        document.getElementById('deliveries_pending').textContent = data.operations_data.deliveries.pending;
        document.getElementById('deliveries_today').textContent = data.operations_data.deliveries.completed_today;
        document.getElementById('transfers_pending').textContent = data.operations_data.transfers.pending;
        document.getElementById('adjustments_pending').textContent = data.operations_data.adjustments.pending;

        // Update alerts
        this.updateAlerts(data.alerts);

        // Update top products
        this.updateTopProducts(data.top_products);

        // Update charts
        this.updateMovementChart(data.movement_trends);
        this.updateCapacityChart(data.capacity_data);

        // Update performance metrics
        document.getElementById('avg_receipt_time').textContent = `${data.performance_metrics.avg_receipt_time_hours}h`;
        document.getElementById('avg_delivery_time').textContent = `${data.performance_metrics.avg_delivery_time_hours}h`;
        document.getElementById('fulfillment_rate').textContent = `${data.performance_metrics.fulfillment_rate_percent}%`;
        document.getElementById('inventory_accuracy').textContent = `${data.performance_metrics.inventory_accuracy_percent}%`;
    }

    updateAlerts(alerts) {
        const alertsList = document.getElementById('alerts_list');
        const alertCount = document.getElementById('alert_count');
        
        alertCount.textContent = alerts.length;
        
        if (alerts.length === 0) {
            alertsList.innerHTML = '<p class="text-muted">No alerts</p>';
            return;
        }

        let html = '';
        alerts.forEach(alert => {
            const badgeClass = alert.severity === 'danger' ? 'bg-danger' : 'bg-warning';
            html += `
                <div class="alert alert-${alert.severity} alert-dismissible fade show" role="alert">
                    <span class="badge ${badgeClass} me-2">${alert.type}</span>
                    ${alert.message}
                </div>
            `;
        });
        
        alertsList.innerHTML = html;
    }

    updateTopProducts(products) {
        const tbody = document.querySelector('#top_products_table tbody');
        
        if (products.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-muted">No data</td></tr>';
            return;
        }

        let html = '';
        products.forEach((product, index) => {
            html += `
                <tr>
                    <td>
                        <span class="badge bg-primary me-1">${index + 1}</span>
                        ${product.product_code ? `[${product.product_code}] ` : ''}${product.product_name}
                    </td>
                    <td class="text-end">${product.movement_count}</td>
                    <td class="text-end">${this.formatNumber(product.total_qty)}</td>
                </tr>
            `;
        });
        
        tbody.innerHTML = html;
    }

    updateMovementChart(trends) {
        const ctx = document.getElementById('movement_chart');
        
        // Destroy existing chart if exists
        if (this.movementChart) {
            this.movementChart.destroy();
        }

        this.movementChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: trends.map(t => t.date),
                datasets: [
                    {
                        label: 'Receipts',
                        data: trends.map(t => t.receipts),
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    },
                    {
                        label: 'Deliveries',
                        data: trends.map(t => t.deliveries),
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1
                    },
                    {
                        label: 'Transfers',
                        data: trends.map(t => t.transfers),
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: false
                    }
                }
            }
        });
    }

    updateCapacityChart(capacityData) {
        const ctx = document.getElementById('capacity_chart');
        
        // Destroy existing chart if exists
        if (this.capacityChart) {
            this.capacityChart.destroy();
        }

        const zones = capacityData.zones || [];
        
        this.capacityChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: zones.map(z => z.name),
                datasets: [{
                    label: 'Capacity Utilization (%)',
                    data: zones.map(z => z.percent),
                    backgroundColor: zones.map(z => {
                        if (z.percent >= 90) return 'rgba(255, 99, 132, 0.8)'; // Red
                        if (z.percent >= 70) return 'rgba(255, 206, 86, 0.8)'; // Yellow
                        return 'rgba(75, 192, 192, 0.8)'; // Green
                    }),
                    borderColor: zones.map(z => {
                        if (z.percent >= 90) return 'rgb(255, 99, 132)';
                        if (z.percent >= 70) return 'rgb(255, 206, 86)';
                        return 'rgb(75, 192, 192)';
                    }),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    formatNumber(value) {
        return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
    }

    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', { 
            style: 'currency', 
            currency: 'USD',
            maximumFractionDigits: 0
        }).format(value);
    }

    onWarehouseChange(ev) {
        this.state.selectedWarehouse = parseInt(ev.target.value);
        this.loadDashboardData();
    }

    onRefresh() {
        this.loadDashboardData();
    }
}

WmsDashboard.template = "wms_dashboard.Dashboard";

// Register the component
registry.category("actions").add("wms_dashboard", WmsDashboard);
