odoo.define('ngsc_reporting.ReportWeeklyByProject', function(require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var QWeb = core.qweb;
    var rpc = require('web.rpc');
    var web_client = require('web.web_client');

    var renderReport = false

    var Report = AbstractAction.extend({
        contentTemplate: 'ReportWeeklyByProject',
        events: {
            'change #project_picker': 'onChangeProjectPicker',
            'change #start_date_picker': 'onChangeDatePicker',
            'change #date_picker': 'onChangeDatePicker'
        },

        init: function(parent, context) {
            this._super(parent, context);
        },
        willStart: function() {
            var self = this;
            self.detail = {}
            self.cumulativeIndex = {}
            self.tasksInWeek = []
            self.tasksNotCompleted = []
            self.tasksNextWeek = []
            self.docsCompleteInWeek = []
            self.docsPending = []
            self.docsNextWeek = []
            self.projectRisks = []
            self.projectProblems = []
            self.projectSurveys = []
            self.projectQaEvaluation = []
            return this._super()
        },
        start: function() {
            var self = this;
            return this._super().then(function() {
                self.get_all_projects();
                self.update_cp();
                self.render_dashboards();
                // self.render_graphs();
                self.$el.parent().addClass('oe_background_grey');
            });
        },

        render_dashboards: function() {
            var self = this;
            var templates = []
                templates = ['LoginUser', 'FilterSection'];
                _.each(templates, function(template) {
                    self.$('.o_report_weekly_by_project').append(QWeb.render(template, {widget: self}));
                });
            renderReport = false
        },

        update_cp: function() {
            var self = this;
        },

        get_all_projects: function() {
            var self = this;
            var prj = self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_all_projects'
            }).then(function (res) {
                self.fillSelect('project_picker', res);
            })
        },

        fillSelect: function (selectId, values, isMultiple = false) {
            const select = document.getElementById(selectId);
            if (!select) return;

            select.innerHTML = '';

            values?.forEach(val => {
                const opt = document.createElement('option');
                if (typeof val === 'object' && val.id && val.code) {
                    opt.value = val.id;
                    opt.textContent = `${val.code}`;
                } else {
                    opt.value = val;
                    opt.textContent = val;
                }
                select.appendChild(opt);
            });

            if ($(select).hasClass('select2')) {
                $(select).select2({
                    placeholder: "Chọn dự án",
                    allowClear: true,
                    width: '100%'
                });
            }
        },

        onChangeProjectPicker: function(e) {
            var self = this;
            e.stopPropagation();
            var $target = $(e.target);
            var valuePP = $target.val();

            var datePicker = $('#date_picker')
            var valueDP = datePicker.val()

            if (valuePP && valueDP) self.generateReport(valuePP, valueDP)
        },

        onChangeDatePicker: function (e) {
            var self = this;
            e.stopPropagation();
            var valueStartDate = $('#start_date_picker').val();
            var valueDate = $('#date_picker').val();
            var valueProject = $('#project_picker').val();
            var targetId = e.target.id;

            // Nếu có đủ project và date_picker thì gọi report
            if (valueProject && valueDate) {
                self.generateReport(valueProject, valueStartDate, valueDate);
            }
        },


        formatPercent: function (value) {
            if (value == null) return '0%';
            const percent = value * 100;
            return (percent % 1 === 0 ? percent.toString() : percent.toFixed(2)) + '%';
        },

        convertDocState: function(value) {
            switch (value){
                case 'new':
                    return "Chưa bàn giao"
                case 'done':
                    return "Đã bàn giao"
                default:
                    return "Huỷ bàn giao"
            }
        },

        generateReport: function (projectId, startDate, endDate) {
            var self = this;

            Promise.all([
                self.getProjectInfo(),
                self.getCumulativeIndex(startDate, endDate), // Truyền cả startDate và endDate
                self.getTasksInWeek(),
                self.getTasksNotCompleted(),
                self.getTasksNextWeek(),
                self.getDocsCompleteInWeek(),
                self.getDocsPending(),
                self.getDocsNextWeek(),
                self.getProjectRisks(),
                self.getProjectProblems(),
                self.getProjectSurveys(),
                self.getProjectQaEvaluation()
            ]).then(function () {
                self.renderTemplateReport();
            });
        },
        renderTemplateReport: function () {
            var self = this;
            var templateClass = [
                '.project-info', '.cumulative-index',
                '.tasks-in-week', '.tasks-not-completed',
                '.tasks-next-week', '.docs-complete-in-week',
                '.docs-pending', '.docs-next-week',
                '.project-risks', '.project-problems',
                '.project-surveys', '.project-qa-evaluation'
            ]
            _.each(templateClass, function (tmp) {
                self.$(`.o_report_weekly_by_project ${tmp}`).remove()
            })
            var templates = [
                'ProjectInfo', 'CumulativeIndex',
                'TasksInWeek', 'TasksNotCompleted',
                'TasksNextWeek', 'DocsCompleteInWeek',
                'DocsPending', 'DocsNextWeek',
                'ProjectRisks', 'ProjectProblems',
                'ProjectSurveys', 'ProjectQaEvaluation'
            ];
            _.each(templates, function(template) {
                self.$('.o_report_weekly_by_project').append(QWeb.render(template, {widget: self}));
            });
        },
        getProjectInfo: function () {
            var self = this;

            var projectPicker = $('#project_picker')
            var valuePP = projectPicker.val()
            var valueDP = $('#date_picker').val()

            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_detail_project',
                args: [valuePP, valueDP]
            }).then(function (rs) {
                self.detail = {
                    ...rs
                }
            })
        },
        getCumulativeIndex: function (startDate, endDate) {
            var self = this;
            var valuePP = $('#project_picker').val();

            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_cumulative_index',
                args: [valuePP, startDate, endDate] // Truyền cả startDate và endDate
            }).then(function (rs) {
                self.cumulativeIndex = rs;
            });
        },
        getTasksInWeek: function () {
            var self = this;
            var valuePP = $('#project_picker').val()
            var valueDP = $('#date_picker').val()
            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_tasks_in_week',
                args: [valuePP, valueDP]
            }).then(function (rs) {
                console.log(rs)
                self.tasksInWeek = JSON.parse(rs)
            })
        },
        getTasksNotCompleted: function() {
            var self = this;
            var valuePP = $('#project_picker').val()
            var valueDP = $('#date_picker').val()
            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_tasks_not_completed',
                args: [valuePP, valueDP]
            }).then(function (rs) {
                self.tasksNotCompleted = JSON.parse(rs)
            })
        },
        getTasksNextWeek: function() {
            var self = this;
            var valuePP = $('#project_picker').val()
            var valueDP = $('#date_picker').val()
            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_tasks_next_week',
                args: [valuePP, valueDP]
            }).then(function (rs) {
                self.tasksNextWeek = JSON.parse(rs)
            })
        },
        getDocsCompleteInWeek: function() {
            var self = this;
            var valuePP = $('#project_picker').val()
            var valueDP = $('#date_picker').val()
            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_docs_complete_in_week',
                args: [valuePP, valueDP]
            }).then(function (rs) {
                self.docsCompleteInWeek = JSON.parse(rs)
            })
        },
        getDocsPending: function() {
            var self = this;
            var valuePP = $('#project_picker').val()
            var valueDP = $('#date_picker').val()
            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_docs_pending',
                args: [valuePP, valueDP]
            }).then(function (rs) {
                self.docsPending = JSON.parse(rs)
            })
        },
        getDocsNextWeek: function() {
            var self = this;
            var valuePP = $('#project_picker').val()
            var valueDP = $('#date_picker').val()
            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_docs_next_week',
                args: [valuePP, valueDP]
            }).then(function (rs) {
                self.docsNextWeek = JSON.parse(rs)
            })
        },
        getProjectRisks: function() {
            var self = this;
            var valuePP = $('#project_picker').val()
            var valueDP = $('#date_picker').val()
            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_project_risks',
                args: [valuePP, valueDP]
            }).then(function (rs) {
                self.projectRisks = JSON.parse(rs)
            })
        },
        getProjectProblems: function() {
            var self = this;
            var valuePP = $('#project_picker').val()
            var valueDP = $('#date_picker').val()
            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_project_problems',
                args: [valuePP, valueDP]
            }).then(function (rs) {
                self.projectProblems = JSON.parse(rs)
            })
        },
        getProjectSurveys: function() {
            var self = this;
            var valuePP = $('#project_picker').val()
            var valueDP = $('#date_picker').val()
            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_project_surveys',
                args: [valuePP, valueDP]
            }).then(function (rs) {
                self.projectSurveys = JSON.parse(rs)
            })
        },
        getProjectQaEvaluation: function() {
            var self = this;
            var valuePP = $('#project_picker').val()
            var valueDP = $('#date_picker').val()
            return self._rpc({
                model: 'report.weekly.by.project',
                method: 'get_project_qa_evaluation',
                args: [valuePP, valueDP]
            }).then(function (rs) {
                self.projectQaEvaluation = JSON.parse(rs)
            })
        },
    })


    core.action_registry.add('report_weekly_by_project', Report);
    return Report;
})