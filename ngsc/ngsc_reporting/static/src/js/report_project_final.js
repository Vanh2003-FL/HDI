odoo.define('ngsc_reporting.FinalProjectReport', function (require) {
    "use strict";

    const AbstractAction = require('web.AbstractAction');
    const rpc = require('web.rpc');
    const core = require('web.core');
    const qweb = core.qweb;
    const web_client = require('web.web_client');
    const ReportExportUtils = require('ngsc_reporting.ReportExportUtils');

    const QualityDashboard = AbstractAction.extend({
        contentTemplate: 'FinalProjectReport',
        currentFilters: null,

        events: {
            'click .btn-export-excel': '_onExportExcelClick',
            'click .quality-table th.sortable': '_onHeaderClick', // Thêm sự kiện click header
            'click .btn-export-pdf': '_onExportPDFClick',
            'click .btn-show-norm': '_onExportNorm',
        },

        _onExportPDFClick: function () {
            ReportExportUtils.exportElementToPDF(
                'quality_dashboard',
                'báo cáo chỉ tiêu chất lượng cuối dự án.pdf'
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

        /**
         * Khi người dùng click "Xuất Excel"
         */
        _onExportExcelClick: function () {
            const self = this;
            if (!this.currentFilters) {
                console.warn("Không có dữ liệu để xuất Excel");
                return;
            }

            this._rpc({
                model: 'project.completion.quality.report',
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

        /**
         * Xử lý khi click vào header để sắp xếp
         */
        _onHeaderClick: function (ev) {
            const $th = $(ev.currentTarget);
            const tableId = $th.closest('table').attr('id');
            const columnIndex = $th.index();
            const isAscending = !$th.hasClass('asc');

            // Clear all sort classes in this table
            $th.closest('table').find('th.sortable').removeClass('asc desc');
            // Set current sort direction
            $th.toggleClass('asc', isAscending).toggleClass('desc', !isAscending);

            // Sort the table
            this.sortTable(tableId, columnIndex, isAscending);
        },

        /**
         * Hàm sắp xếp bảng
         */
        sortTable: function (tableId, columnIndex, isAscending) {
            const $table = $('#' + tableId);
            const $tbody = $table.find('tbody');
            const $rows = $tbody.find('tr').get();

            $rows.sort((a, b) => {
                const aVal = $(a).find('td').eq(columnIndex).text().trim();
                const bVal = $(b).find('td').eq(columnIndex).text().trim();

                // === Nếu là cột Ngày đóng (dd/MM/yyyy) ===
                if (columnIndex === 4) {
                    function parseDMY(s) {
                        if (!s) return null;
                        const parts = s.split('/');
                        if (parts.length !== 3) return null;
                        const day = parseInt(parts[0], 10);
                        const month = parseInt(parts[1], 10) - 1; // JS month 0-11
                        const year = parseInt(parts[2], 10);
                        return new Date(year, month, day).getTime(); // ép sang timestamp số nguyên
                    }

                    const aDate = parseDMY(aVal);
                    const bDate = parseDMY(bVal);

                    // Nếu không parse được thì đẩy xuống cuối
                    if (aDate === null && bDate === null) return 0;
                    if (aDate === null) return 1;
                    if (bDate === null) return -1;

                    return isAscending ? aDate - bDate : bDate - aDate;
                }

                // === Nếu là số (phần trăm, tiền, ...) ===
                const aNum = parseFloat(aVal.replace('%', '').replace(',', ''));
                const bNum = parseFloat(bVal.replace('%', '').replace(',', ''));
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return isAscending ? aNum - bNum : bNum - aNum;
                }

                // === Text thường ===
                return isAscending
                    ? aVal.localeCompare(bVal)
                    : bVal.localeCompare(aVal);
            });

            // Rebuild the table
            $tbody.empty();
            $.each($rows, (index, row) => {
                $tbody.append(row);
            });
        },

        start: async function () {
            this._super.apply(this, arguments);
            // 👉 Gọi cập nhật dữ liệu
            // await rpc.query({
            //     model: 'project.completion.quality.report',
            //     method: 'generate_final_project_report',
            //     args: [],
            // });

            this.loadFilters();
            this.loadDashboard();

            this.$('#filter-month-from, #filter-month-to').on('change', () =>{
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

        loadFilters: function () {
            const fromMonth = $('#filter-month-from').val();
            const toMonth = $('#filter-month-to').val();
            let selectedMonths = [];
            if (fromMonth && toMonth && fromMonth <= toMonth) {
                selectedMonths = this.getMonthRange(fromMonth, toMonth);
            } else if (fromMonth) {
                selectedMonths = [fromMonth];
            } else {
                selectedMonths = [];
            }
            const filters = {
                khoi: $('#filter-khoi').val() || null,
                center: $('#filter-center').val() || null,
                type: $('#filter-type').val() || null,
                project: $('#filter-project').val() || null,
                months: selectedMonths,
            };

            rpc.query({
                model: 'project.completion.quality.report',
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
            } else if (toMonth) {
                selectedMonths = [toMonth];
            } else {
                selectedMonths = [];
            }

            // Lưu filters hiện tại
            this.currentFilters = {
                trung_tam: center === 'All' ? null : center,
                khoi: khoi === 'All' ? null : khoi,
                loai_du_an: type === 'All' ? null : type,
                du_an: project && project.length ? project : null,
                months: selectedMonths,
            };

            rpc.query({
                model: 'project.completion.quality.report',
                method: 'get_filter_report',
                args: [this.currentFilters]
            }).then(data => {
                const normMap = data.norm || {};
                const projects = data.projects || [];

                const getColorWithNorm = (val, norm) => {
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

                const charts = [
                    {
                        canvasId: 'scheduleAchievementChartV1',
                        instanceName: 'scheduleAchievementChartV1Instance',
                        label: '% Schedule Achievement v1.0',
                        field: 'schedule_achievement_v1',
                        normKey: '%SA1'
                    },
                    {
                        canvasId: 'scheduleAchievementChartV2',
                        instanceName: 'scheduleAchievementChartV2Instance',
                        label: '% Schedule Achievement v2.0',
                        field: 'schedule_achievement_v2',
                        normKey: '%SA2'
                    },
                    {
                        canvasId: 'scheduleAchievementChartLast',
                        instanceName: 'scheduleAchievementChartLastInstance',
                        label: '% Schedule Achievement v lastupdate',
                        field: 'schedule_achievement_last',
                        normKey: '%SAL'
                    },
                    {
                        canvasId: 'effortEfficiencyBMMFirstChart',
                        instanceName: 'effortEfficiencyBMMFirstInstance',
                        label: '% Effort Efficiency BMM đầu tiên',
                        field: 'effort_efficiency_bmm_first',
                        normKey: '%EEB1'
                    },
                    {
                        canvasId: 'effortEfficiencyBMMLastChart',
                        instanceName: 'effortEfficiencyBMMLastInstance',
                        label: '% Effort Efficiency BMM cuối cùng',
                        field: 'effort_efficiency_bmm_last',
                        normKey: '%EEBL'
                    },
                    {
                        canvasId: 'effortEfficiencyPlanV1Chart',
                        instanceName: 'effortEfficiencyPlanV1Instance',
                        label: '% Effort Efficiency Plan v1.0',
                        field: 'effort_efficiency_plan_v1',
                        normKey: '%EEP1'
                    },
                    {
                        canvasId: 'effortEfficiencyPlanV2Chart',
                        instanceName: 'effortEfficiencyPlanV2Instance',
                        label: '% Effort Efficiency Plan v2.0',
                        field: 'effort_efficiency_plan_v2',
                        normKey: '%EEP2'
                    },
                    {
                        canvasId: 'effortEfficiencyPlanLastChart',
                        instanceName: 'effortEfficiencyPlanLastInstance',
                        label: '% Effort Efficiency Plan v lastupdate',
                        field: 'effort_efficiency_plan_last',
                        normKey: '%EEPL'
                    }
                ];

                // Thêm class sortable vào các header khi render bảng
                this.renderTableRows(projects, normMap);

                charts.forEach(({canvasId, instanceName, label, field, normKey}) => {
                    const labels = [];
                    const data = [];
                    const colors = [];

                    projects.forEach(project => {
                        const labelText = truncate(project.project_code || '');
                        const val = project[field] || 0;
                        labels.push(labelText);
                        data.push(val);
                        colors.push(getColorWithNorm(val, normMap[normKey]));
                    });

                    this.renderVerticalChart(canvasId, instanceName, labels, data, label, normMap[normKey] || null, colors);
                });
            });
        },

        renderTableRows: function (projects, normMap) {
            const tbody = document.querySelector('#table-schedule tbody');
            if (!tbody) return;

            tbody.innerHTML = '';

            // Thêm class sortable vào các header
            const thead = document.querySelector('#table-schedule thead');
            if (thead) {
                thead.innerHTML = `
                    <tr>
                        <th class="sortable">Khối</th>
                        <th class="sortable">Trung tâm</th>
                        <th class="sortable">Loại dự án</th>
                        <th class="sortable">Dự án</th>
                        <th class="sortable">Ngày đóng</th>
                        <th class="sortable">% Schedule Achievement v1.0</th>
                        <th class="sortable">% Schedule Achievement v2.0</th>
                        <th class="sortable">% Schedule Achievement v lastupdate</th>
                        <th class="sortable">% Effort Efficiency BMM đầu tiên</th>
                        <th class="sortable">% Effort Efficiency BMM cuối cùng</th>
                        <th class="sortable">% Effort Efficiency Plan v1.0</th>
                        <th class="sortable">% Effort Efficiency Plan v2.0</th>
                        <th class="sortable">% Effort Efficiency Plan v lastupdate</th>
                    </tr>
                `;
            }

            projects.forEach(project => {
                const row = document.createElement('tr');

                const metrics = [
                    {value: project.schedule_achievement_v1, norm: normMap['%SA1']},
                    {value: project.schedule_achievement_v2, norm: normMap['%SA2']},
                    {value: project.schedule_achievement_last, norm: normMap['%SAL']},
                    {value: project.effort_efficiency_bmm_first, norm: normMap['%EEB1']},
                    {value: project.effort_efficiency_bmm_last, norm: normMap['%EEBL']},
                    {value: project.effort_efficiency_plan_v1, norm: normMap['%EEP1']},
                    {value: project.effort_efficiency_plan_v2, norm: normMap['%EEP2']},
                    {value: project.effort_efficiency_plan_last, norm: normMap['%EEPL']}
                ];

                const baseFields = [
                    project.unit_name,
                    project.center_name,
                    project.project_type,
                    project.project_code,
                    project.closing_date
                ];

                baseFields.forEach(val => {
                    const td = document.createElement('td');
                    td.textContent = val || '-';
                    row.appendChild(td);
                });

                metrics.forEach(({value, norm}) => {
                    const td = document.createElement('td');
                    if (value === 0 || value === null || value === undefined) {
                        td.textContent = 'N/A';
                        td.style.color = 'black';
                    } else {
                        td.textContent = `${value.toFixed(2)}%`;
                        td.style.color = getColorWithNorm(value, norm);
                        td.style.fontWeight = 'bold';
                    }
                    row.appendChild(td);
                });

                tbody.appendChild(row);
            });

            function getColorWithNorm(val, norm) {
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
            }
        },

        renderVerticalChart: function (canvasId, instanceName, labels, data, labelTitle, norm) {
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;
            if (!labels || labels.length === 0) {
                const container = canvas?.parentElement;
                if (container) container.style.height = '50px';
                canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
                if (window[instanceName]) window[instanceName].destroy();
                return;
            }
            const ctx = canvas.getContext('2d');
            if (window[instanceName]) window[instanceName].destroy();


            const heightPerLabel = 30;
            const chartHeight = Math.max(200, labels.length * heightPerLabel);
            canvas.parentElement.style.height = chartHeight + 'px';
            // canvas.parentElement.parentElement.style.maxHeight = '250px';
            // canvas.parentElement.parentElement.style.overflowY = 'auto';

            const originalData = data; // giữ nguyên để so sánh
            const displayedData = data.map(v => Math.min(v, 200)); // thanh bar hiển thị tối đa 200

            // 👉 Tạo thêm dataset ảo để hiển thị đường norm + tooltip
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
                    labels,
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
                                        position: 'start',
                                        rotation: 'auto',
                                    }
                                }
                            } : {}
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            max: 207,
                            title: {display: true, text: '%'},
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
                                ctx.fillText('∞', xPos, yCenter);
                                ctx.restore();
                            }
                        });
                    }
                }]
            });
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

    core.action_registry.add('project_completion_quality_report_template', QualityDashboard);
    return QualityDashboard;
});