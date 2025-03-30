from flask import Flask

def register_routes(app):
    """注册蓝图到应用程序"""
    from routes import mobo_routes
    from expert_api import register_expert_api
    
    # 检查蓝图是否已注册，避免重复注册
    if 'mobo_routes' not in app.blueprints:
        app.register_blueprint(mobo_routes)
    
    # 注册专家API蓝图
    register_expert_api(app)

def configure_app(app):
    """配置应用程序设置"""
    # 设置全局编码为UTF-8
    app.json.ensure_ascii = False
    app.config['JSON_AS_ASCII'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
    
    # 注册所有路由
    register_routes(app) 