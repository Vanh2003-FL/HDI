/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MyAttendances } from "@hr_attendance/components/my_attendances/my_attendances";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted } from "@odoo/owl";

// Geolocation options
const GEO_OPTIONS = {
    enableHighAccuracy: true,
    timeout: 60000, // 60 seconds
    maximumAge: 0
};

// Prevent double-click
let pendingClick = false;

/**
 * Enhanced MyAttendances component
 * Kết hợp tính năng từ NGSD và NGSC
 */
patch(MyAttendances.prototype, {
    setup() {
        super.setup();
        
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        
        // State management
        this.state = useState({
            locations: [],
            selectedLocationId: null,
            allowDifferentLocation: true,
            isProcessing: false,
            settings: {
                geolocationEnabled: true,
                geolocationRequired: false,
                queueEnabled: true,
                offlineMode: true,
            }
        });
        
        // Load settings and locations
        onMounted(async () => {
            await this.loadSettings();
            await this.loadLocations();
            this.initOfflineSync();
        });
    },
    
    /**
     * Load system settings
     */
    async loadSettings() {
        try {
            const result = await this.rpc('/hr_attendance/check_settings');
            if (result.success) {
                Object.assign(this.state.settings, result);
            }
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    },
    
    /**
     * Load available work locations
     */
    async loadLocations() {
        try {
            const result = await this.rpc('/hr_attendance/get_locations');
            if (result.success) {
                this.state.locations = result.locations || [];
                this.state.selectedLocationId = result.default_id || null;
            }
        } catch (error) {
            console.error('Error loading locations:', error);
        }
    },
    
    /**
     * Initialize offline sync
     */
    initOfflineSync() {
        if (!this.state.settings.offlineMode) return;
        
        // Listen for online event
        window.addEventListener('online', () => {
            console.log('🌐 Online - syncing offline queue...');
            this.flushOfflineQueue();
        });
        
        // Try to flush on mount
        if (navigator.onLine) {
            this.flushOfflineQueue();
        }
    },
    
    /**
     * Override update_attendance để thêm geolocation + queue
     */
    async update_attendance() {
        // Prevent double-click
        if (pendingClick || this.state.isProcessing) {
            this.notification.add(
                this.env._t("Bạn đã bấm rồi, vui lòng chờ xử lý xong."),
                { type: "warning" }
            );
            return;
        }
        
        pendingClick = true;
        this.state.isProcessing = true;
        
        setTimeout(() => {
            pendingClick = false;
        }, 3000);
        
        try {
            // Get GPS if enabled
            let position = null;
            if (this.state.settings.geolocationEnabled) {
                try {
                    position = await this._getCurrentPosition();
                } catch (error) {
                    console.warn('Geolocation error:', error);
                    
                    if (this.state.settings.geolocationRequired) {
                        this.notification.add(
                            this.env._t("Không thể lấy vị trí GPS. Vui lòng bật GPS và thử lại."),
                            { type: "danger" }
                        );
                        this.state.isProcessing = false;
                        return;
                    }
                }
            }
            
            // Prepare payload
            const action = this.props.employee.attendance_state === "checked_in" 
                ? "check_out" : "check_in";
            
            const payload = {
                employee_id: this.props.employee.id,
                action: action,
                timestamp: this._formatDatetimeUTC(new Date()),
            };
            
            // Add GPS data
            if (position) {
                payload.latitude = position.coords.latitude;
                payload.longitude = position.coords.longitude;
            }
            
            // Add work location
            if (this.state.selectedLocationId) {
                payload.work_location_id = this.state.selectedLocationId;
            }
            
            // Send to server or save offline
            if (navigator.onLine) {
                await this._sendAttendanceLog(payload);
            } else {
                this._saveToOfflineQueue(payload);
            }
            
            // Call super to update UI
            await super.update_attendance();
            
        } catch (error) {
            console.error('Error in update_attendance:', error);
            this.notification.add(
                this.env._t("Lỗi: ") + error.message,
                { type: "danger" }
            );
        } finally {
            this.state.isProcessing = false;
            setTimeout(() => {
                pendingClick = false;
            }, 1000);
        }
    },
    
    /**
     * Get current GPS position
     */
    _getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Trình duyệt không hỗ trợ GPS'));
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                resolve,
                reject,
                GEO_OPTIONS
            );
        });
    },
    
    /**
     * Send attendance log to server
     */
    async _sendAttendanceLog(payload) {
        console.log('📤 Sending attendance log:', payload);
        
        try {
            const result = await this.rpc('/hr_attendance/log', payload);
            
            if (result.success) {
                console.log('✅ Attendance logged successfully:', result);
                this.notification.add(
                    result.message || this.env._t("Chấm công thành công!"),
                    { type: "success" }
                );
            } else {
                throw new Error(result.message || 'Unknown error');
            }
        } catch (error) {
            console.error('❌ Error sending log:', error);
            
            // Save to offline queue if offline mode enabled
            if (this.state.settings.offlineMode) {
                this._saveToOfflineQueue(payload);
            } else {
                throw error;
            }
        }
    },
    
    /**
     * Save to offline queue (localStorage)
     */
    _saveToOfflineQueue(payload) {
        if (!this.state.settings.offlineMode) return;
        
        try {
            const queue = JSON.parse(localStorage.getItem('attendance_offline_queue') || '[]');
            queue.push({
                ...payload,
                savedAt: new Date().toISOString()
            });
            localStorage.setItem('attendance_offline_queue', JSON.stringify(queue));
            
            console.warn('📥 Saved to offline queue:', payload);
            
            this.notification.add(
                this.env._t("Không có kết nối. Đã lưu tạm và sẽ gửi khi online."),
                { type: "info" }
            );
        } catch (error) {
            console.error('Error saving to offline queue:', error);
        }
    },
    
    /**
     * Flush offline queue when online
     */
    async flushOfflineQueue() {
        if (!this.state.settings.offlineMode) return;
        
        try {
            const queue = JSON.parse(localStorage.getItem('attendance_offline_queue') || '[]');
            if (queue.length === 0) return;
            
            console.log(`🔄 Flushing ${queue.length} offline logs...`);
            
            const newQueue = [];
            
            for (const payload of queue) {
                try {
                    await this.rpc('/hr_attendance/log', payload);
                    console.log('✅ Synced offline log:', payload);
                } catch (error) {
                    console.error('❌ Failed to sync:', error);
                    newQueue.push(payload);
                }
            }
            
            localStorage.setItem('attendance_offline_queue', JSON.stringify(newQueue));
            
            if (newQueue.length < queue.length) {
                this.notification.add(
                    this.env._t(`Đã đồng bộ ${queue.length - newQueue.length} bản ghi chấm công offline.`),
                    { type: "success" }
                );
            }
        } catch (error) {
            console.error('Error flushing offline queue:', error);
        }
    },
    
    /**
     * Format datetime to Odoo UTC format
     */
    _formatDatetimeUTC(date) {
        const pad = (n) => n < 10 ? '0' + n : n;
        
        return date.getUTCFullYear() + '-' +
            pad(date.getUTCMonth() + 1) + '-' +
            pad(date.getUTCDate()) + ' ' +
            pad(date.getUTCHours()) + ':' +
            pad(date.getUTCMinutes()) + ':' +
            pad(date.getUTCSeconds());
    },
    
    /**
     * Handle location change
     */
    onLocationChange(ev) {
        this.state.selectedLocationId = parseInt(ev.target.value);
    },
});
