{
    "name": "Login Failed 2 Ban",
    "summary": """Khóa tài khoản sau một số lần đăng nhập thất bại""",
    "author": "Entrustlab",
    "website": "https://entrustlab.com/",
    "category": "Tools",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/res_users.xml",
    ],
    "installable": True,
}
