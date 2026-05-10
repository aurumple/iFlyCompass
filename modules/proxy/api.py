from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from utils import get_settings
from . import proxy_bp
from .proxy_server import is_proxy_running, PROXY_PORT, start_proxy_server, stop_proxy_server


def _get_proxy_url_from_request():
    """使用用户当前访问的 Host 构建代理 URL，而非服务器自身 IP"""
    host = request.host.split(':')[0] if request.host else '127.0.0.1'
    return f'http://{host}:{PROXY_PORT}'


@proxy_bp.route('/tools/webproxy')
@login_required
def web_proxy_page():
    settings = get_settings()
    return render_template('web_proxy.html',
                         current_user=current_user,
                         sidebar_expanded=settings.get('sidebar_default_expanded', False))


@proxy_bp.route('/api/proxy/status')
@login_required
def proxy_status():
    running = is_proxy_running()
    return jsonify({
        'running': running,
        'proxy_url': _get_proxy_url_from_request() if running else None,
        'proxy_host': request.host.split(':')[0] if request.host else '127.0.0.1' if running else None,
        'proxy_port': PROXY_PORT
    })


@proxy_bp.route('/api/proxy/start', methods=['POST'])
@login_required
def proxy_start():
    if is_proxy_running():
        return jsonify({'success': True, 'proxy_url': _get_proxy_url_from_request()})

    success = start_proxy_server()
    if success:
        return jsonify({'success': True, 'proxy_url': _get_proxy_url_from_request()})
    else:
        return jsonify({'success': False, 'error': '代理服务器启动失败'}), 500


@proxy_bp.route('/api/proxy/stop', methods=['POST'])
@login_required
def proxy_stop():
    if not is_proxy_running():
        return jsonify({'success': True})

    stop_proxy_server()
    return jsonify({'success': True})
