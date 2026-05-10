from flask import render_template, send_from_directory, jsonify, request
from flask_login import login_required, current_user
from utils import get_bing_wallpaper, get_poetry, get_settings, get_nav_items
from config import Config
from . import main_bp

@main_bp.route('/')
def index():
    wallpaper_url = get_bing_wallpaper()
    poetry = get_poetry()
    return render_template('index.html', wallpaper_url=wallpaper_url, poetry=poetry)

@main_bp.route('/board')
@login_required
def board():
    settings = get_settings()
    return render_template('board.html', 
                         current_user=current_user,
                         home_display=settings.get('home_display', 'nickname'),
                         sidebar_expanded=settings.get('sidebar_default_expanded', False))

@main_bp.route('/board/tools')
@login_required
def tools():
    settings = get_settings()
    return render_template('tools.html',
                         current_user=current_user,
                         sidebar_expanded=settings.get('sidebar_default_expanded', False),
                         card_layout=settings.get('card_layout', '1x4'),
                         category='tools')

@main_bp.route('/board/games')
@login_required
def games():
    settings = get_settings()
    return render_template('tools.html',
                         current_user=current_user,
                         sidebar_expanded=settings.get('sidebar_default_expanded', False),
                         card_layout=settings.get('card_layout', '1x4'),
                         category='games')

@main_bp.route('/board/swipe-test')
@login_required
def swipe_test():
    if not (current_user.is_admin or current_user.is_super_admin):
        return render_template('error.html', 
                             error_title='权限不足',
                             error_message='您没有权限访问此页面',
                             current_user=current_user), 403
    settings = get_settings()
    return render_template('swipe_test.html', 
                         current_user=current_user,
                         sidebar_expanded=settings.get('sidebar_default_expanded', False))

@main_bp.route('/board/announcements')
@login_required
def announcement_manage():
    if not (current_user.is_admin or current_user.is_super_admin):
        return render_template('error.html', 
                             error_title='权限不足',
                             error_message='您没有权限访问此页面',
                             current_user=current_user), 403
    settings = get_settings()
    return render_template('announcement_manage.html', 
                         current_user=current_user,
                         sidebar_expanded=settings.get('sidebar_default_expanded', False))

@main_bp.route('/temp/<path:filename>')
def serve_temp(filename):
    return send_from_directory(Config.TEMP_DIR, filename)

@main_bp.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(Config.ASSETS_DIR, filename)

@main_bp.route('/api/nav/items')
@login_required
def get_nav_items_api():
    category = request.args.get('category', 'tools')
    items = get_nav_items()
    filtered_items = [item for item in items if item.get('category') == category]
    return jsonify(filtered_items)
