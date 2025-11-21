odoo.define('account_asset.AssetFormView', function(require) {
"use strict";

import { FormRenderer } from 'web.FormRenderer';
import { FormView } from 'web.FormView';
import { core } from 'web.core';
import { viewRegistry } from 'web.view_registry';

var _t = core._t;

var AccountAssetFormRenderer = FormRenderer.extend({
    events: _.extend({}, FormRenderer.prototype.events, {
        'click .add_original_move_line': '_onAddOriginalMoveLine',
    }),
    /*
     * Open the m2o item selection from another button
     */
    _onAddOriginalMoveLine: function(ev) {
        _.find(this.allFieldWidgets[this.state.id], x => x['name'] == 'original_move_line_ids').onAddRecordOpenDialog();
    },
});

var AssetFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Renderer: AccountAssetFormRenderer,
    }),
});

viewRegistry.add("asset_form", AssetFormView);
return AssetFormView;

});
