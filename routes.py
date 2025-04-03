from flask import render_template, redirect, url_for, Blueprint, send_from_directory

# 创建蓝图，提供唯一名称
mobo_routes = Blueprint('mobo_routes', __name__, template_folder='templates', url_prefix='/mobo')

@mobo_routes.route('/')
def index():
    """主页路由，重定向到登录页面"""
    return redirect(url_for('mobo_routes.login_page'))

@mobo_routes.route('/login')
def login_page():
    """登录页面路由"""
    return render_template('mobo/mobo登录页面.html')

@mobo_routes.route('/MOBO主页.html')
def mobo_home_page():
    """MOBO主页路由"""
    return render_template('MOBO主页.html')

@mobo_routes.route('/home')
def home():
    """MOBO主页路由 - 登录成功后跳转到这里"""
    return render_template('MOBO主页.html')

@mobo_routes.route('/助理.html')
def assistant_page():
    """助理页面路由"""
    return render_template('助理.html')

@mobo_routes.route('/专家.html')
def expert_page():
    """专家页面路由"""
    return render_template('专家.html')

@mobo_routes.route('/prompt.json')
def prompt_json():
    """提供prompt.json文件访问"""
    return send_from_directory('.', 'prompt.json') 