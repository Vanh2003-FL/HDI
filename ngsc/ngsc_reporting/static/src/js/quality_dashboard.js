odoo.define('ngsc_reporting.QualityDashboardTemplate', function (require) {
    "use strict";

    const AbstractAction = require('web.AbstractAction');
    const rpc = require('web.rpc');
    const core = require('web.core');
    var qweb = core.qweb;
    var web_client = require('web.web_client');
    const ReportExportUtils = require('ngsc_reporting.ReportExportUtils');

    const QualityDashboard = AbstractAction.extend({
        contentTemplate: 'QualityDashboardTemplate',
        currentFilters: null,

        events: {
            'click .btn-export-excel': '_onExportExcelClick',
            'click .quality-table th.sortable': '_onHeaderClick',
            'click .btn-export-pdf': '_onExportPDFClick',
            'click .btn-show-norm': '_onExportNorm',
        },

        _onExportPDFClick: function () {
            ReportExportUtils.exportElementToPDF(
                'quality_dashboard',
                'báo cáo chỉ tiêu chất lượng dự án hàng tháng.pdf'
            );
        },

        _onExportNorm: function () {
            var self = this;
            this._rpc({
                model: 'reporting.norm.setting',
                method: 'get_norm_popup_data',
                args: [],
            }).then(function (records) {
                var html = qweb.render('NormSetting', {records: records});

                // Xóa modal cũ nếu có
                $('#normModal').remove();
                $('body').append(html);
                $('#normModal').modal('show');
            });
        },

        _onExportExcelClick: function () {
            const self = this;
            if (!this.currentFilters) {
                console.warn("Không có dữ liệu để xuất Excel");
                return;
            }

            this._rpc({
                model: 'project.quality.monthly.report',
                method: 'export_excel_report',
                args: [this.currentFilters],
            }).then(function (res) {
                const link = document.createElement('a');
                link.href = 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,' + res.file_data;
                link.download = res.file_name;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }).catch(function (err) {
                console.error("Lỗi xuất Excel:", err);
            });
        },
        // sort a-->z
        _onHeaderClick: function (ev) {
            const $th = $(ev.currentTarget);
            const tableId = $th.closest('table').attr('id');
            const columnIndex = $th.index();
            const isAscending = !$th.hasClass('asc');

            $th.closest('table').find('th.sortable').removeClass('asc desc');
            $th.toggleClass('asc', isAscending).toggleClass('desc', !isAscending);

            this.sortTable(tableId, columnIndex, isAscending);
        },

        sortTable: function (tableId, columnIndex, isAscending) {
            const $table = $('#' + tableId);
            const $tbody = $table.find('tbody');
            const $rows = $tbody.find('tr').get();

            $rows.sort((a, b) => {
                const aVal = $(a).find('td').eq(columnIndex).text().trim().toLowerCase();
                const bVal = $(b).find('td').eq(columnIndex).text().trim().toLowerCase();

                const aNum = parseFloat(aVal.replace('%', ''));
                const bNum = parseFloat(bVal.replace('%', ''));
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return isAscending ? aNum - bNum : bNum - aNum;
                }

                return isAscending
                    ? aVal.localeCompare(bVal)
                    : bVal.localeCompare(aVal);
            });

            $tbody.empty();
            $.each($rows, (index, row) => {
                $tbody.append(row);
            });
        },

        start: function () {
            this._super.apply(this, arguments);

            const currentDate = new Date();
            currentDate.setMonth(currentDate.getMonth() - 1); // Giảm 1 tháng

            const year = currentDate.getFullYear();
            const month = String(currentDate.getMonth() + 1).padStart(2, '0');
            const defaultMonth = `${year}-${month}`;

            // Thiết lập giá trị mặc định
            this.$('#filter-month-from').val(defaultMonth);
            this.$('#filter-month-to').val(defaultMonth);

            // Giới hạn không được chọn tháng hiện tại trở đi
            this.$('#filter-month-from').attr('max', defaultMonth);
            this.$('#filter-month-to').attr('max', defaultMonth);

            this.loadFilters();

            this.loadDashboard();

            this.$('#filter-month-from, #filter-month-to').on('change', () => {
                this._validateMonthRange();
                this.loadDashboard();
                this.loadFilters();
            });
        },
        _validateMonthRange: function () {
            const fromMonth = this.$('#filter-month-from').val();
            const toMonth = this.$('#filter-month-to').val();

            if (fromMonth && toMonth && fromMonth > toMonth) {
                this._showWarningDialog("Tháng kết thúc phải lớn hơn hoặc bằng tháng bắt đầu");
                this.$('#filter-month-to').val('');
            }
        },

        _showWarningDialog: function (message) {
            const Dialog = require('web.Dialog');
            Dialog.alert(this, message, {
                title: "Error"
            });
        },

        loadFilters: function () {
            const fromMonth = $('#filter-month-from').val();
            const toMonth = $('#filter-month-to').val();

            let selectedMonths = [];
            if (fromMonth && toMonth && fromMonth <= toMonth) {
                selectedMonths = this.getMonthRange(fromMonth, toMonth);
            } else if (fromMonth) {
                selectedMonths = [fromMonth];
            } else {
                selectedMonths = [this.getCurrentMonth()];
            }
            const filters = {
                khoi: $('#filter-khoi').val() || null,
                center: $('#filter-center').val() || null,
                type: $('#filter-type').val() || null,
                project: $('#filter-project').val() || null,
                months: selectedMonths,
            };

            rpc.query({
                model: 'project.quality.monthly.report',
                method: 'get_filter_values',
                args: [filters],
            }).then(data => {
                this.fillSelect('filter-khoi', data.unit_name);
                this.fillSelect('filter-center', data.centers);
                this.fillSelect('filter-type', data.project_types);
                this.fillSelect('filter-project', data.projects, true);
            });
        },

        fillSelect: function (selectId, values, isMultiple = false) {
            const select = document.getElementById(selectId);
            if (!select) return;

            const currentVal = $(select).val(); // giữ lại giá trị cũ
            select.innerHTML = '';

            if (!isMultiple) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'All';
                select.appendChild(opt);
            }

            values?.forEach(val => {
                const opt = document.createElement('option');
                if (typeof val === 'object' && val.code && val.name) {
                    opt.value = val.code;
                    opt.textContent = `${val.code} - ${val.name}`;
                } else {
                    opt.value = val;
                    opt.textContent = val;
                }
                select.appendChild(opt);
            });

            // ✅ Gán lại giá trị đã chọn (nếu còn)
            if (isMultiple) {
                if (Array.isArray(currentVal)) {
                    const validValues = currentVal.filter(val =>
                        values.some(v => (typeof v === 'object' ? v.code === val : v === val))
                    );
                    $(select).val(validValues.length ? validValues : []);
                } else {
                    $(select).val([]);
                }
            } else {
                const isValid = values.some(v => (typeof v === 'object' ? v.code === currentVal : v === currentVal));
                $(select).val(isValid ? currentVal : '');
            }

            // 🛠️ Gắn lại sự kiện
            if (selectId === 'filter-project') {
                $(select).off('change').on('change', () => {
                    this.loadDashboard();
                });
            } else {
                $(select).off('change').on('change', () => {
                    this.loadFilters();
                    this.loadDashboard();
                });
            }

            // destroy select2 trước khi init lại
            if ($(select).hasClass('select2-hidden-accessible')) {
                $(select).select2('destroy');
            }
            if ($(select).hasClass('select2')) {
                $(select).select2({
                    placeholder: "Chọn dự án",
                    allowClear: true,
                    width: '100%'
                });
            }
        },

        loadDashboard: function () {
            const center = $('#filter-center').val();
            const khoi = $('#filter-khoi').val();
            const type = $('#filter-type').val();
            const project = $('#filter-project').val();
            const fromMonth = $('#filter-month-from').val();
            const toMonth = $('#filter-month-to').val();
            let selectedMonths = [];

            if (fromMonth && toMonth && fromMonth <= toMonth) {
                selectedMonths = this.getMonthRange(fromMonth, toMonth);
            } else if (fromMonth) {
                selectedMonths = [fromMonth];
            } else {
                selectedMonths = [this.getCurrentMonth()];
            }

            this.currentFilters = {
                trung_tam: center === 'All' ? null : center,
                khoi: khoi === 'All' ? null : khoi,
                loai_du_an: type === 'All' ? null : type,
                du_an: project && project.length ? project : null,
                months: selectedMonths
            };

            rpc.query({
                model: 'project.quality.monthly.report',
                method: 'get_filtered_reports',
                args: [this.currentFilters]
            }).then(data => {
                    const normMap = data.norm || {};
                    let projects = data.projects || [];
                    const months = data.months || [];

                     // Lọc bỏ project mà cả 3 chỉ tiêu đều toàn 0 trong tất cả các tháng đã chọn
                    projects = projects.filter(project => {
                        const allMonthlyZero = months.every(m => !project.values[m]?.effort_efficiency_monthly);
                        const allPlanZero = months.every(m => !project.values[m]?.effort_efficiency_plan_last);
                        const allScheduleZero = months.every(m => !project.values[m]?.schedule_achievement_last);
                        return !(allMonthlyZero && allPlanZero && allScheduleZero);
                    });

                    const getColorWithNorm = (val, fieldName) => {
                        let normKey = '';
                        if (fieldName === 'schedule') normKey = '%SAL';
                        else if (fieldName === 'effortMonthly') normKey = '%EEM';
                        else if (fieldName === 'effortPlan') normKey = '%EEPL';
                        const norm = normMap[normKey];
                        if (!norm) return '';
                        val = val / 100;
                        const normVal = norm.value / 100;
                        const stdDev = norm.std_dev / 100;
                        const direction = norm.direction;

                        if (direction === 'le') {
                            if (val <= (normVal - stdDev)) return norm.color_good;
                            if (val <= normVal) return norm.color_pass;
                            if (val <= (normVal + stdDev)) return norm.color_fail;
                            return norm.color_bad;
                        } else {
                            if (val >= (normVal + stdDev)) return norm.color_good;
                            if (val >= normVal) return norm.color_pass;
                            if (val >= (normVal - stdDev)) return norm.color_fail;
                            return norm.color_bad;
                        }
                    };

                    const truncate = (text, maxLength = 30) => text.length > maxLength ? text.slice(0, maxLength) + '…' : text;

                    // Schedule Table
                    const $theadSchedule = $('#table-schedule thead tr');
                    $theadSchedule.html(`
                        <th class="sortable">Khối</th>
                        <th class="sortable">Trung tâm</th>
                        <th class="sortable">Loại dự án</th>
                        <th class="sortable">Dự án</th>
                        ${months.map(month => `<th class="sortable">${month}</th>`).join('')}
                    `);
                    const $tbodySchedule = $('#table-schedule tbody');
                    $tbodySchedule.empty();

                    const scheduleLabels = [], scheduleData = [], scheduleColors = [];

                    projects.forEach(project => {
                        const row = $('<tr></tr>');
                        row.append(`<td>${project.unit_name}</td>`);
                        row.append(`<td>${project.center_name}</td>`);
                        row.append(`<td>${project.project_type}</td>`);
                        row.append(`<td>${project.project_code}</td>`);
                        months.forEach(month => {
                            const val = project.values[month]?.schedule_achievement_last;
                            let color, displayValue, fontWeight;

                            if (val === 0 || val === null || val === undefined) {
                                displayValue = 'N/A';
                                color = 'black';
                                fontWeight = 'normal';
                            } else {
                                displayValue = `${val}%`;
                                color = getColorWithNorm(val, 'effortMonthly');
                                fontWeight = 'bold';
                            }
                            row.append(`<td style="color: ${color}; font-weight: ${fontWeight}">${displayValue}</td>`);
                            scheduleLabels.push(`${truncate(project.project_code)} (${month})`);
                            scheduleData.push(val);
                            scheduleColors.push(color);
                        });
                        $tbodySchedule.append(row);
                    });

                    // Effort Monthly Table
                    const $theadEffortMonthly = $('#table-effort-monthly thead tr');
                    $theadEffortMonthly.html(`
                        <th class="sortable">Khối</th>
                        <th class="sortable">Trung tâm</th>
                        <th class="sortable">Loại dự án</th>
                        <th class="sortable">Dự án</th>
                        ${months.map(month => `<th class="sortable">${month}</th>`).join('')}
                    `);
                    const $tbodyEffortMonthly = $('#table-effort-monthly tbody');
                    $tbodyEffortMonthly.empty();

                    const effortMonthlyLabels = [], effortMonthlyData = [], effortMonthlyColors = [];

                    projects.forEach(project => {
                        const row = $('<tr></tr>');
                        row.append(`<td>${project.unit_name}</td>`);
                        row.append(`<td>${project.center_name}</td>`);
                        row.append(`<td>${project.project_type}</td>`);
                        row.append(`<td>${project.project_code}</td>`);

                        months.forEach(month => {
                            const valMonthly = project.values[month]?.effort_efficiency_monthly;
                            let colorMonthly, displayValue, fontWeight;

                            if (valMonthly === 0 || valMonthly === null || valMonthly === undefined) {
                                displayValue = 'N/A';
                                colorMonthly = 'black';
                                fontWeight = 'normal';
                            } else {
                                displayValue = `${valMonthly}%`;
                                colorMonthly = getColorWithNorm(valMonthly, 'effortMonthly');
                                fontWeight = 'bold';
                            }

                            row.append(`<td style="color: ${colorMonthly}; font-weight: ${fontWeight}">${displayValue}</td>`);
                            effortMonthlyLabels.push(`${truncate(project.project_code)} (${month})`);
                            effortMonthlyData.push(valMonthly || null);
                            effortMonthlyColors.push(colorMonthly);
                        });

                        $tbodyEffortMonthly.append(row);
                    });

                    // Effort Plan Table
                    const $theadEffortPlan = $('#table-effort-plan thead tr');
                    $theadEffortPlan.html(`
                        <th class="sortable">Khối</th>
                        <th class="sortable">Trung tâm</th>
                        <th class="sortable">Loại dự án</th>
                        <th class="sortable">Dự án</th>
                        ${months.map(month => `<th class="sortable">${month}</th>`).join('')}
                    `);
                    const $tbodyEffortPlan = $('#table-effort-plan tbody');
                    $tbodyEffortPlan.empty();

                    const effortPlanLabels = [], effortPlanData = [], effortPlanColors = [];

                    projects.forEach(project => {
                        const row = $('<tr></tr>');
                        row.append(`<td>${project.unit_name}</td>`);
                        row.append(`<td>${project.center_name}</td>`);
                        row.append(`<td>${project.project_type}</td>`);
                        row.append(`<td>${project.project_code}</td>`);

                        months.forEach(month => {
                            const valPlan = project.values[month]?.effort_efficiency_plan_last;
                            let colorPlan, displayValue, fontWeight;

                            if (valPlan === 0 || valPlan === null || valPlan === undefined) {
                                displayValue = 'N/A';
                                colorPlan = 'black';
                                fontWeight = 'normal';
                            } else {
                                displayValue = `${valPlan}%`;
                                colorPlan = getColorWithNorm(valPlan, 'effortMonthly');
                                fontWeight = 'bold';
                            }
                            row.append(`<td style="color: ${colorPlan}; font-weight: ${fontWeight}">${displayValue}</td>`);
                            effortPlanLabels.push(`${truncate(project.project_code)} (${month})`);
                            effortPlanData.push(valPlan);
                            effortPlanColors.push(colorPlan);
                        });

                        $tbodyEffortPlan.append(row);
                    });

                    const isLineChart = selectedMonths.length > 1;
                    if (isLineChart === false) {
                        function renderVerticalChart(canvasId, instanceName, labels, data, colors, labelTitle, norm) {
                            const canvas = document.getElementById(canvasId);
                            if (!canvas) return;

                            const ctx = canvas.getContext('2d');
                            if (window[instanceName]) window[instanceName].destroy();

                            const heightPerLabel = 30;
                            const chartHeight = Math.max(200, labels.length * heightPerLabel);
                            canvas.parentElement.style.height = chartHeight + 'px';

                            const originalData = data; // giữ nguyên để so sánh
                            const displayedData = data.map(v => Math.min(v, 200)); // thanh bar hiển thị tối đa 200

                            const datasets = [
                                {
                                    label: labelTitle,
                                    data: displayedData,
                                    backgroundColor: '#2196F3'
                                }
                            ];

                            if (norm) {
                                datasets.push({
                                    label: `Norm: ${norm.value}%`,
                                    data: new Array(labels.length).fill(norm.value),
                                    type: 'line',
                                    borderColor: 'gold',
                                    borderWidth: 2,
                                    pointRadius: 1,
                                    pointHoverRadius: 0,
                                    hitRadius: 3,
                                    borderDash: [4, 4],
                                    tension: 0,
                                    fill: false
                                });
                            }

                            window[instanceName] = new Chart(ctx, {
                                type: 'bar',
                                data: {
                                    labels: labels,
                                    datasets: datasets
                                },
                                options: {
                                    indexAxis: 'y',
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {
                                        legend: {
                                            display: true,
                                            position: 'top',
                                            labels: {
                                                boxWidth: 12,
                                                font: {size: 10}
                                            }
                                        },
                                        tooltip: {
                                            enabled: true,
                                            callbacks: {
                                                label: function (context) {
                                                    if (context.dataset.label?.startsWith('Norm')) {
                                                        return `Norm: ${norm.value}%`;
                                                    }
                                                    const realValue = originalData[context.dataIndex];
                                                    return `${context.dataset.label}: ${realValue > 200 ? realValue + ' ∞' : realValue}%`;
                                                }
                                            }
                                        },
                                        annotation: {
                                            annotations: norm ? {
                                                normLine: {
                                                    type: 'line',
                                                    xMin: norm.value,
                                                    xMax: norm.value,
                                                    borderColor: 'gold',
                                                    borderWidth: 2,
                                                    label: {
                                                        display: true,
                                                        content: `Norm ${norm.value}%`,
                                                        backgroundColor: 'gold',
                                                        color: '#000',
                                                        font: {size: 10},
                                                        position: 'start'
                                                    }
                                                }
                                            } : {}
                                        }
                                    },
                                    scales: {
                                        x: {
                                            beginAtZero: true,
                                            max: 207,
                                            title: {
                                                display: true,
                                                text: '%'
                                            },
                                            ticks: {
                                                callback: function (value) {
                                                    // Ẩn  tick 207
                                                    return value === 207 ? '' : value;
                                                }
                                            }
                                        },
                                        y: {
                                            ticks: {autoSkip: false},
                                            grid: {display: false}
                                        }
                                    }
                                },
                                plugins: [{
                                    id: 'drawInfinitySigns',
                                    afterDatasetsDraw(chart, args, options) {
                                        const {ctx, scales: {x}} = chart;
                                        const meta = chart.getDatasetMeta(0);
                                        if (!meta || !meta.data) return;

                                        originalData.forEach((value, index) => {
                                            if (value > 200) {
                                                const bar = meta.data[index];
                                                if (!bar) return;

                                                const yCenter = bar.y;
                                                const xPos = x.getPixelForValue(200) + 8;
                                                ctx.save();
                                                ctx.font = 'bold 18px Segoe UI Symbol, Arial';
                                                ctx.fillStyle = 'red';
                                                ctx.textBaseline = 'middle';
                                                ctx.fillText('∞', xPos, yCenter);
                                                ctx.restore();
                                            }
                                        });
                                    }
                                }]
                            });
                        }

                        renderVerticalChart('scheduleChart',
                            'scheduleChartInstance',
                            scheduleLabels, scheduleData, scheduleColors,
                            '% Schedule Achievement', normMap['%SAL']);
                        renderVerticalChart('effortMonthlyChart',
                            'effortMonthlyChartInstance',
                            effortMonthlyLabels, effortMonthlyData, effortMonthlyColors,
                            '% Effort Efficiency Monthly', normMap['%EEM']);
                        renderVerticalChart('effortPlanChart',
                            'effortPlanChartInstance',
                            effortPlanLabels, effortPlanData, effortPlanColors,
                            '% Effort Efficiency v lastupdate', normMap['%EEPL']);

                    } else {
                        function renderLineChart(canvasId, instanceName, labelTitle, field, norm) {
                            const canvas = document.getElementById(canvasId);
                            if (!canvas) return;

                            if (window[instanceName]) {
                                window[instanceName].destroy();
                            }

                            const formatMonth = m => {
                                const [year, month] = m.split('-');
                                return new Date(year, month - 1).toLocaleString('default', {
                                    month: 'long',
                                    year: 'numeric'
                                });
                            };

                            const labels = months.map(formatMonth);
                            let allValues = [];

                            // Filter ra các project có dữ liệu không phải toàn 0
                            const datasets = projects.map(project => {
                                const data = months.map(month => project.values[month]?.[field] || 0);
                                // const isAllZero = data.every(v => v === 0);
                                // if (isAllZero) return null;

                                allValues.push(...data);

                                const color = get_random_color();
                                return {
                                    label: project.project_code,
                                    data: data,
                                    borderColor: color,
                                    backgroundColor: color,
                                    fill: false,
                                    tension: 0,
                                    pointRadius: 4,
                                    pointHoverRadius: 6
                                };
                            });

                            // Luôn thêm đường Norm
                            if (norm) {
                                const normData = new Array(labels.length).fill(norm.value);
                                datasets.push({
                                    label: `Norm: ${norm.value}%`,
                                    data: normData,
                                    type: 'line',
                                    borderColor: 'gold',
                                    borderWidth: 2,
                                    pointRadius: 1,
                                    pointHoverRadius: 0,
                                    hitRadius: 3,
                                    fill: false,
                                    tension: 0,
                                    spanGaps: true,
                                });
                                allValues.push(norm.value);
                            }

                            const isAllZero = allValues.every(v => v === 0);
                            canvas.parentElement.style.height = isAllZero ? '100px' : '';

                            const maxValue = Math.max(...allValues, 100);
                            const suggestedMax = Math.ceil(maxValue / 50) * 50;

                            window[instanceName] = new Chart(canvas.getContext('2d'), {
                                type: 'line',
                                data: {
                                    labels: labels,
                                    datasets: datasets
                                },
                                options: {
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {
                                        title: {
                                            display: true,
                                            text: labelTitle,
                                            font: {size: 10}
                                        },
                                        legend: {
                                            position: 'bottom',
                                            labels: {
                                                usePointStyle: true,
                                                pointStyle: 'circle',
                                                boxWidth: 8,
                                                boxHeight: 8,
                                                padding: 10
                                            }
                                        },
                                        tooltip: {
                                            callbacks: {
                                                label: function (context) {
                                                    const label = context.dataset.label || '';
                                                    if (label.startsWith('Norm')) {
                                                        return `Norm: ${norm.value}%`;
                                                    }
                                                    return context.raw === 0 ? label : `${label}: ${context.formattedValue}%`;
                                                }
                                            }
                                        }
                                    },
                                    scales: {
                                        y: {
                                            beginAtZero: true,
                                            suggestedMax: suggestedMax,
                                            // max: 200,
                                            title: {
                                                display: true,
                                                text: '%'
                                            },
                                            ticks: {
                                                stepSize: 50
                                            }
                                        },
                                        x: {
                                            ticks: {
                                                maxRotation: 45,
                                                minRotation: 30
                                            }
                                        }
                                    }
                                }
                            });
                        }

                        renderLineChart('scheduleChart',
                            'scheduleChartInstance',
                            '% Schedule Achievement v lastupdate',
                            'schedule_achievement_last', normMap['%SAL']);
                        renderLineChart('effortMonthlyChart',
                            'effortMonthlyChartInstance',
                            '% Effort Efficiency Monthly',
                            'effort_efficiency_monthly', normMap['%EEM']);
                        renderLineChart('effortPlanChart',
                            'effortPlanChartInstance',
                            '% Effort Efficiency v lastupdate',
                            'effort_efficiency_plan_last', normMap['%EEPL']);
                    }

                    function get_random_color() {
                        var r = function () {
                            return Math.floor(Math.random() * 256)
                        };
                        return "rgb(" + r() + "," + r() + "," + r() + ")";
                    }
                }
            );
        },

        getCurrentMonth: function () {
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth()).padStart(2, '0');
            return `${year}-${month}`;
        },

        getMonthRange: function (startMonth, endMonth) {
            const result = [];
            let [startY, startM] = startMonth.split('-').map(Number);
            let [endY, endM] = endMonth.split('-').map(Number);

            while (startY < endY || (startY === endY && startM <= endM)) {
                const formatted = `${startY}-${String(startM).padStart(2, '0')}`;
                result.push(formatted);
                startM++;
                if (startM > 12) {
                    startM = 1;
                    startY++;
                }
            }
            return result;
        },
    });

    core.action_registry.add('project_quality_monthly_template', QualityDashboard);
    return QualityDashboard;
});