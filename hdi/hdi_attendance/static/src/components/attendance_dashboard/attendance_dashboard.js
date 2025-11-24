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
            // Get current employee - try multiple methods
            let employees = await this.orm.searchRead(
                'hr.employee',
                [['user_id', '=', session.uid]],
                ['id', 'name', 'attendance_state', 'work_location_id', 'hours_today']
            );
            
            // If not found, try getting employee from context or default
            if (employees.length === 0) {
                // Get all employees accessible by current user
                employees = await this.orm.searchRead(
                    'hr.employee',
                    [],
                    ['id', 'name', 'attendance_state', 'work_location_id', 'hours_today'],
                    { limit: 1 }
                );
            }
            
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
        if (this.state.isProcessing || !this.state.employee || !this.state.employee.id) {
            console.warn('Cannot check in/out:', this.state.employee);
            this.notification.add('Không tìm thấy thông tin nhân viên', { type: 'warning' });
            return;
        }
        
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
            
            console.log('GPS Position:', position.coords);
            console.log('Employee ID:', this.state.employee.id);
            console.log('Location ID:', this.state.selectedLocationId);
            
            const context = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
            };
            
            if (this.state.selectedLocationId) {
                context.en_location_id = this.state.selectedLocationId;
            }
            
            const result = await this.orm.call(
                'hr.employee',
                'attendance_action_change',
                [[this.state.employee.id]],
                { context }
            );
            
            console.log('Check in/out result:', result);
            
            if (result.action) {
                this.notification.add('Chấm công thành công!', { type: 'success' });
                await this.loadEmployeeData();
            } else if (result.warning) {
                this.notification.add(result.warning, { type: 'warning' });
            } else {
                this.notification.add('Chấm công thành công!', { type: 'success' });
                await this.loadEmployeeData();
            }
        } catch (error) {
            console.error('Check in/out error:', error);
            this.notification.add(
                error.data?.message || error.message || 'Không thể chấm công. Vui lòng thử lại.',
                { type: 'danger' }
            );
        } finally {
            this.state.isProcessing = false;
        }
    }
}

AttendanceDashboard.template = "hdi_attendance.AttendanceDashboard";

registry.category("actions").add("hdi_attendance.dashboard", AttendanceDashboard);
