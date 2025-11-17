/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

// HDI HR Dashboard Component
export class HdiHrDashboard extends Component {
    setup() {
        // Dashboard logic will be implemented here
    }
}

HdiHrDashboard.template = "hdi_hr.Dashboard";

registry.category("actions").add("hdi_hr_dashboard", HdiHrDashboard);
