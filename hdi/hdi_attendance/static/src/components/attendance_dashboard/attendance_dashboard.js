/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

export class AttendanceDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            employee: null,
            locations: [],
            selectedLocationId: null,
            isProcessing: false,
        });
        
        onWillStart(async () => {
            await this.loadEmployeeData();
        });
    }
    
    async loadEmployeeData() {
        try {
            const employees = await this.orm.searchRead(
                'hr.employee',
                [['user_id', '=', session.uid]],
                ['id', 'name', 'attendance_state', 'work_location_id', 'hours_today']
            );
            
            if (employees.length > 0) {
                this.state.employee = employees[0];
                
                const locations = await this.orm.call(
                    'hr.employee',
                    'get_working_locations',
                    [this.state.employee.id]
                );
                this.state.locations = locations || [];
                
                if (this.state.employee.work_location_id) {
                    this.state.selectedLocationId = this.state.employee.work_location_id[0];
                } else if (this.state.locations.length > 0) {
                    this.state.selectedLocationId = this.state.locations[0].id;
                }
            } else {
                this.state.employee = { name: 'No Employee', attendance_state: 'checked_out' };
            }
        } catch (error) {
            console.error('Error loading employee data:', error);
            this.state.employee = { name: 'Error Loading', attendance_state: 'checked_out' };
        }
    }
    
    get buttonText() {
        if (!this.state.employee) return 'Loading...';
        return this.state.employee.attendance_state === 'checked_in' ? 'CHECK OUT' : 'CHECK IN';
    }
    
    get buttonClass() {
        if (!this.state.employee) return 'btn-secondary';
        return this.state.employee.attendance_state === 'checked_in' ? 'btn-danger' : 'btn-success';
    }
    
    get statusText() {
        if (!this.state.employee) return '';
        if (this.state.employee.attendance_state === 'checked_in') {
            const hours = Math.floor(this.state.employee.hours_today || 0);
            const minutes = Math.round(((this.state.employee.hours_today || 0) - hours) * 60);
            return `Đã làm việc: ${hours}h ${minutes}m`;
        }
        return 'Chưa check in';
    }
    
    onLocationChange(ev) {
        this.state.selectedLocationId = parseInt(ev.target.value);
    }
    
    async onCheckInOut() {
        if (this.state.isProcessing || !this.state.employee) return;
        this.state.isProcessing = true;
        
        try {
            const position = await new Promise((resolve, reject) => {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(resolve, reject, {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    });
                } else {
                    reject(new Error('Trình duyệt không hỗ trợ định vị GPS'));
                }
            });
            
            const context = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
            };
            
            if (this.state.selectedLocationId) {
                context.en_location_id = this.state.selectedLocationId;
            }
            
            const result = await this.orm.call(
                'hr.employee',
                'attendance_manual',
                [[this.state.employee.id], 'hr_attendance.hr_attendance_action_my_attendances'],
                { context }
            );
            
            if (result.action) {
                this.notification.add('Chấm công thành công!', { type: 'success' });
                await this.loadEmployeeData();
            } else if (result.warning) {
                this.notification.add(result.warning, { type: 'warning' });
            }
        } catch (error) {
            this.notification.add(
                error.message || 'Không thể lấy vị trí GPS. Vui lòng bật GPS và thử lại.',
                { type: 'danger' }
            );
        } finally {
            this.state.isProcessing = false;
        }
    }
}

AttendanceDashboard.template = "hdi_attendance.AttendanceDashboard";

registry.category("actions").add("hdi_attendance.dashboard", AttendanceDashboard);
