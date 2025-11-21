odoo.define('order_line_import.import_action',function (require) {
"use strict";

import { core } from 'web.core';
import { Model } from 'web.BasicModel';
var DataImport=require('base_import.import');
var Dialog=require('web.Dialog');

DataImport.DataImport.include({
    init:function (parent, action) {
        this._super.apply(this, arguments);
        this._target=action.target;
        this._dialog_height=action.params.height || '860px';
        this.show_required=action.params.show_required || false;
        this.import_field=action.params.import_field || false;
        this.res_id=action.params.res_id || false;
    },

    need_import:function(){
        return this._target=='new' && this.import_field;
    },

    exit:function(){
        if(!this.need_import()){
            return this._super.apply(this,arguments);
        }
        if(this.action_manager.actionService){
            this.action_manager.actionService.doAction({
                'type': 'ir.actions.client',
                'tag': 'reload',
            });
        }
    },

    import_options: function () {
        var options=this._super.apply(this,arguments);
        var is_import=this.need_import();
        var res_id=this.res_id;
        if(options && is_import && res_id){
            // var controller=this.getController();
            // var model=controller.model;
            // var order=model.get(controller.handle);
            _.extend(options, {
                import_order_line:is_import,
                import_field: this.import_field,
                order_id: res_id,
            });
        }
        return options;
    },

    getController:function(){
        return this.action_manager.getCurrentController().widget;
    },
	 
    renderButtons: function() {
    	this._super.apply(this,arguments);
    	if(this.need_import()){
            this.$el.find('.o_content').css("height",this._dialog_height);
    	}
    },
    onpreview_success: function (event, from, to, result) {
        this._super.apply(this,arguments);
    	if(this.need_import()){
            this.$el.find('.o_import_import.d-none').removeClass('d-none');
            this.$el.find('.o_import_validate.d-none').removeClass('d-none');
    	}
    }
});
});
