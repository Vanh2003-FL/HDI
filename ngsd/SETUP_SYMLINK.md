# Setup Symlink for Odoo to Read Module

## Problem
Odoo is trying to read modules from:
```
/home/va/odoo18/ProjectOdoo/odoo/ngsd/
```

But we are editing files in:
```
/workspaces/HDI/ngsd/
```

## Solution
Create a symbolic link so Odoo can find the module:

```bash
# Create parent directory if needed
sudo mkdir -p /home/va/odoo18/ProjectOdoo/odoo

# Create symlink
sudo ln -sfn /workspaces/HDI/ngsd /home/va/odoo18/ProjectOdoo/odoo/ngsd

# Verify
ls -la /home/va/odoo18/ProjectOdoo/odoo/ngsd
```

## Alternative: Update Odoo Config
Edit your Odoo configuration file to point to the correct addons path:

```ini
[options]
addons_path = /workspaces/HDI/ngsd,/workspaces/HDI/ngsc,/home/va/odoo18/odoo-source/addons
```

## Verify Setup
After creating symlink or updating config, verify with:

```bash
# Check if Odoo can see the module
ls /home/va/odoo18/ProjectOdoo/odoo/ngsd/ngsd_base/__init__.py

# Should output: /home/va/odoo18/ProjectOdoo/odoo/ngsd/ngsd_base/__init__.py
```

Then restart Odoo.
