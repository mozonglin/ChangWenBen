from flask import Flask

def register_routes(app):
    """注册蓝图到应用程序（仅当需要时）
    注意：在run.py中已经注册了主要蓝图，此处仅作为备用
    """
    try:
        from routes import mobo_routes
        from expert_api import register_expert_api
        
        # 仅当蓝图尚未注册时才注册
        if 'mobo_routes' not in app.blueprints:
            app.register_blueprint(mobo_routes)
            print("通过app_config注册了mobo_routes蓝图")
        
        # 仅当expert_api尚未注册时才注册
        if 'expert_api' not in app.blueprints:
            register_expert_api(app)
            print("通过app_config注册了expert_api蓝图")
            
    except ImportError as e:
        print(f"导入蓝图时出错: {str(e)}")
    except Exception as e:
        print(f"注册蓝图时出错: {str(e)}")

def configure_app(app):
    """配置应用程序设置"""
    # 设置全局编码为UTF-8
    app.json.ensure_ascii = False
    app.config['JSON_AS_ASCII'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
    
    # 注册所有路由（作为备用机制）
    register_routes(app) 