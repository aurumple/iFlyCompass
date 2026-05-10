import re
import secrets
import os
from mitmproxy import http
from urllib.parse import urlparse, unquote

PROXY_PORT = 5003
_proxy_host = None


def get_proxy_host():
    global _proxy_host
    if _proxy_host is not None:
        return _proxy_host

    env_host = os.environ.get('PROXY_HOST', '')
    if env_host:
        _proxy_host = env_host
        return _proxy_host

    addon_dir = os.path.dirname(os.path.abspath(__file__))
    host_file = os.path.join(os.path.dirname(addon_dir), '.proxy_host')
    if os.path.isfile(host_file):
        try:
            with open(host_file, 'r') as f:
                saved = f.read().strip()
                if saved:
                    _proxy_host = saved
                    return _proxy_host
        except Exception:
            pass

    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        _proxy_host = ip
    except Exception:
        _proxy_host = '127.0.0.1'

    return _proxy_host


def set_proxy_host(host):
    global _proxy_host
    _proxy_host = host


_proxy_token = None


def get_proxy_token():
    global _proxy_token
    if _proxy_token is None:
        _proxy_token = secrets.token_hex(16)
    return _proxy_token


def get_hook_js():
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    hook_path = os.path.join(addon_dir, 'hook.js')
    try:
        with open(hook_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ''


class WebProxyAddon:

    def request(self, flow: http.HTTPFlow):
        url = flow.request.url
        parsed = urlparse(url)
        host = parsed.hostname or ''
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)

        flow._client_proxy_host = host

        if host and port == PROXY_PORT:
            set_proxy_host(host)

        ph = get_proxy_host()

        if not flow.request.headers.get('User-Agent'):
            flow.request.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

        proxy_token = get_proxy_token()
        client_token = flow.request.headers.get('X-Proxy-Token', '')
        client_base = flow.request.headers.get('X-Proxy-Base', '')

        referer = flow.request.headers.get('Referer', '')
        origin = flow.request.headers.get('Origin', '')

        if self._is_proxy_self(host, port):
            target_url = self._parse_target_any(flow.request.path)
            if target_url:
                target_parsed = urlparse(target_url)
                flow.request.scheme = target_parsed.scheme
                flow.request.host = target_parsed.hostname
                flow.request.port = target_parsed.port or (443 if target_parsed.scheme == 'https' else 80)
                flow.request.path = target_parsed.path or '/'
                if target_parsed.query:
                    flow.request.path = flow.request.path + '?' + target_parsed.query
                flow.request.http_version = 'HTTP/1.1'

                target_host = target_parsed.hostname + (':' + str(target_parsed.port) if target_parsed.port and target_parsed.port not in (80, 443) else '')
                if 'Host' in flow.request.headers:
                    flow.request.headers['Host'] = target_host

                if client_token and client_token == proxy_token and client_base:
                    base_parsed = urlparse(client_base)
                    origin_host = base_parsed.hostname
                    if base_parsed.port and base_parsed.port not in (80, 443):
                        origin_host += ':' + str(base_parsed.port)

                    if not flow.request.headers.get('Referer') or self._is_proxy_referer(flow.request.headers.get('Referer', '')):
                        flow.request.headers['Referer'] = client_base + '/'
                    if not flow.request.headers.get('Origin') or self._is_proxy_origin(flow.request.headers.get('Origin', '')):
                        flow.request.headers['Origin'] = base_parsed.scheme + '://' + origin_host
                else:
                    inferred_base = self._infer_base_from_referer(referer)
                    if inferred_base:
                        if not flow.request.headers.get('Referer') or self._is_proxy_referer(flow.request.headers.get('Referer', '')):
                            flow.request.headers['Referer'] = inferred_base + '/'
                        if not flow.request.headers.get('Origin') or self._is_proxy_origin(flow.request.headers.get('Origin', '')):
                            bp = urlparse(inferred_base)
                            oh = bp.hostname
                            if bp.port and bp.port not in (80, 444):
                                oh += ':' + str(bp.port)
                            flow.request.headers['Origin'] = bp.scheme + '://' + oh
                    else:
                        if not flow.request.headers.get('Referer') or self._is_proxy_referer(flow.request.headers.get('Referer', '')):
                            flow.request.headers['Referer'] = target_parsed.scheme + '://' + target_parsed.netloc + '/'
                        if not flow.request.headers.get('Origin') or self._is_proxy_origin(flow.request.headers.get('Origin', '')):
                            flow.request.headers['Origin'] = target_parsed.scheme + '://' + target_parsed.netloc

                if not flow.request.headers.get('Accept'):
                    flow.request.headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
                if not flow.request.headers.get('Accept-Language'):
                    flow.request.headers['Accept-Language'] = 'zh-CN,zh;q=0.9,en;q=0.8'
            else:
                flow.response = http.Response.make(
                    400,
                    b'<html><body><h1>400 - Invalid URL</h1></body></html>',
                    {'Content-Type': 'text/html; charset=utf-8'}
                )

    def response(self, flow: http.HTTPFlow):
        if not flow.response:
            return

        client_host = getattr(flow, '_client_proxy_host', None)
        if client_host:
            set_proxy_host(client_host)

        ph = get_proxy_host()

        if flow.response.status_code in (301, 302, 303, 307, 308):
            location = flow.response.headers.get('Location', '')
            if location and flow.request.url:
                flow.response.headers['Location'] = self._rewrite_location(location, flow.request.url)

        content_type = flow.response.headers.get('Content-Type', '')

        if 'text/html' in content_type:
            self._inject_hook(flow)
        elif 'text/css' in content_type:
            self._rewrite_css(flow)
        elif ('javascript' in content_type or 'application/js' in content_type or
              flow.request.url.endswith('.js')):
            self._rewrite_js(flow)

    def _is_proxy_self(self, host, port):
        return port == PROXY_PORT

    def _is_proxy_referer(self, referer):
        if not referer:
            return True
        ph = get_proxy_host()
        proxy_base = 'http://' + ph + ':' + str(PROXY_PORT)
        return referer.startswith(proxy_base)

    def _is_proxy_origin(self, origin):
        if not origin:
            return True
        ph = get_proxy_host()
        proxy_base = 'http://' + ph + ':' + str(PROXY_PORT)
        return origin.startswith(proxy_base) or origin in ('http://localhost', 'http://127.0.0.1')

    def _parse_target_any(self, path):
        path = unquote(path)
        if path.startswith('/'):
            path = path[1:]

        match = re.match(r'^(getassets)/(https?)/(.+)', path)
        if match:
            scheme = match.group(2)
            rest = match.group(3)
            return scheme + '://' + rest

        match = re.match(r'^(https?)/(.+)', path)
        if not match:
            return None
        scheme = match.group(1)
        rest = match.group(2)
        return scheme + '://' + rest

    def _rewrite_referer(self, referer):
        if not referer:
            return referer
        ph = get_proxy_host()
        proxy_prefix = 'http://' + ph + ':' + str(PROXY_PORT) + '/'
        if referer.startswith(proxy_prefix):
            path = referer[len(proxy_prefix):]
            match = re.match(r'^(https?)/(.+)', path)
            if match:
                return match.group(1) + '://' + match.group(2)
        return referer

    def _extract_real_url(self, proxy_url):
        if not proxy_url:
            return None
        ph = get_proxy_host()
        proxy_prefix = 'http://' + ph + ':' + str(PROXY_PORT) + '/'
        if proxy_url.startswith(proxy_prefix):
            path = proxy_url[len(proxy_prefix):]
            match = re.match(r'^(https?)/(.+)', path)
            if match:
                return match.group(1) + '://' + match.group(2)
        return proxy_url

    def _infer_base_from_referer(self, referer):
        if not referer:
            return None
        ph = get_proxy_host()
        proxy_prefix = 'http://' + ph + ':' + str(PROXY_PORT) + '/'
        if not referer.startswith(proxy_prefix):
            return None
        path = referer[len(proxy_prefix):]
        match = re.match(r'^(https?)/(.+)', path)
        if match:
            return match.group(1) + '://' + match.group(2)
        return None

    def _rewrite_location(self, location, base_url):
        if not location:
            return location
        ph = get_proxy_host()
        proxy_prefix = 'http://' + ph + ':' + str(PROXY_PORT) + '/'

        if location.startswith(proxy_prefix):
            return location

        real_base = self._extract_real_url(base_url) or base_url

        if location.startswith(('http://', 'https://')):
            try:
                parsed = urlparse(location)
                if parsed.scheme in ('http', 'https') and parsed.netloc and parsed.netloc != ph:
                    proxy_path = parsed.scheme + '/' + parsed.netloc + parsed.path
                    if parsed.query:
                        proxy_path += '?' + parsed.query
                    return proxy_prefix + proxy_path
            except Exception:
                pass
            return location

        if not real_base:
            return location

        base_parsed = urlparse(real_base)
        if location.startswith('/'):
            full_url = base_parsed.scheme + '://' + base_parsed.netloc + location
        elif location.startswith('//'):
            full_url = base_parsed.scheme + ':' + location
        else:
            from urllib.parse import urljoin
            full_url = urljoin(real_base, location)

        try:
            parsed = urlparse(full_url)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                proxy_path = parsed.scheme + '/' + parsed.netloc + parsed.path
                if parsed.query:
                    proxy_path += '?' + parsed.query
                return proxy_prefix + proxy_path
        except Exception:
            pass
        return location

    def _inject_hook(self, flow):
        try:
            content = flow.response.get_text()
        except Exception:
            return
        if not content:
            return

        ph = get_proxy_host()
        proxy_base = 'http://' + ph + ':' + str(PROXY_PORT)
        token = get_proxy_token()
        hook_js = get_hook_js()

        if not hook_js:
            return

        content = self._rewrite_html_attrs(content, flow.request.url)
        content = self._rewrite_inline_scripts(content, flow.request.url)

        inject = (
            '<script data-proxy-hook="true">'
            'window.__PROXY_BASE__="' + proxy_base + '";'
            'window.__PROXY_TOKEN__="' + token + '";'
            + hook_js +
            '</script>'
        )

        head_match = re.search(r'<head[^>]*>', content, re.IGNORECASE)
        if head_match:
            content = content[:head_match.end()] + inject + content[head_match.end():]
        else:
            html_match = re.search(r'<html[^>]*>', content, re.IGNORECASE)
            if html_match:
                content = content[:html_match.end()] + '<head>' + inject + '</head>' + content[html_match.end():]
            else:
                content = inject + content

        flow.response.set_text(content)

    def _rewrite_html_attrs(self, content, request_url):
        ph = get_proxy_host()
        proxy_prefix = 'http://' + ph + ':' + str(PROXY_PORT)

        parsed_url = urlparse(request_url)
        base_scheme = parsed_url.scheme or 'https'
        base_host = parsed_url.netloc or ''

        def to_proxy_url(url):
            if url.startswith(proxy_prefix):
                return url
            if url.startswith(('http://', 'https://')):
                try:
                    p = urlparse(url)
                    path = p.path or ''
                    result = f'{proxy_prefix}/{p.scheme}/{p.netloc}{path}'
                    if p.query:
                        result += '?' + p.query
                    return result
                except Exception:
                    return url
            if url.startswith('//'):
                return to_proxy_url(base_scheme + ':' + url)
            if url.startswith('/'):
                return f'{proxy_prefix}/{base_scheme}/{base_host}{url}'
            return url

        def replace_attr(match):
            attr_name = match.group(1).lower()
            quote = match.group(2)
            url = match.group(3)

            if attr_name not in ('href', 'src', 'action', 'data-src', 'data-href',
                                 'poster', 'background', 'srcset', 'content'):
                return match.group(0)

            if not url or len(url) < 3:
                return match.group(0)

            if url.startswith(('data:', 'javascript:', 'mailto:', 'blob:', '#', 'about:')):
                return match.group(0)

            if url.startswith(proxy_prefix):
                return match.group(0)

            if attr_name == 'content':
                if not url.startswith(('http://', 'https://')):
                    return match.group(0)

            new_url = to_proxy_url(url)
            if new_url == url:
                return match.group(0)

            return f'{attr_name}={quote}{new_url}{quote}'

        content = re.sub(
            r'(\w+)\s*=\s*(["\'])([^"\']+)\2',
            replace_attr,
            content
        )

        def replace_style_url(match):
            style_content = match.group(0)
            def replace_css_u(u_match):
                u = u_match.group(1)
                if u.startswith(('data:', 'javascript:', '#', 'about:')):
                    return u_match.group(0)
                if u.startswith(proxy_prefix):
                    return u_match.group(0)
                new_u = to_proxy_url(u)
                if new_u != u:
                    return f'url({new_u})'
                return u_match.group(0)

            return re.sub(r'url\(\s*["\']?([^"\'\)]+)["\']?\s*\)', replace_css_u, style_content)

        content = re.sub(
            r'style\s*=\s*(["\'][^"\']*["\'])',
            replace_style_url,
            content
        )

        return content

    def _rewrite_inline_scripts(self, content, request_url):
        ph = get_proxy_host()
        proxy_prefix = 'http://' + ph + ':' + str(PROXY_PORT)

        parsed_url = urlparse(request_url)
        base_scheme = parsed_url.scheme or 'https'
        base_host = parsed_url.netloc or ''

        def to_proxy_url(url):
            if url.startswith(('http://', 'https://')):
                try:
                    p = urlparse(url)
                    path = p.path or ''
                    result = f'{proxy_prefix}/{p.scheme}/{p.netloc}{path}'
                    if p.query:
                        result += '?' + p.query
                    return result
                except Exception:
                    return url
            if not url.startswith('/'):
                url = '/' + url
            return f'{proxy_prefix}/{base_scheme}/{base_host}{url}'

        def rewrite_script_content(match):
            prefix = match.group(1)
            script_body = match.group(2)
            suffix = match.group(3)

            if 'data-proxy-hook="true"' in prefix:
                return match.group(0)

            def replace_url_in_string(s_match):
                url = s_match.group(1)
                if not url or len(url) < 5:
                    return s_match.group(0)
                if url.startswith(('data:', 'javascript:', 'mailto:', 'blob:', '#', 'about:')):
                    return s_match.group(0)
                if url.startswith(proxy_prefix):
                    return s_match.group(0)
                if url.startswith('https://') or url.startswith('http://'):
                    if ph and (ph in url):
                        return s_match.group(0)
                    return '"' + to_proxy_url(url) + '"'
                return s_match.group(0)

            new_body = re.sub(r'"(https?://[^"]+)"', replace_url_in_string, script_body)

            return prefix + new_body + suffix

        content = re.sub(
            r'(<script[^>]*>)([\s\S]*?)(</script>)',
            rewrite_script_content,
            content
        )

        return content

    def _rewrite_js(self, flow):
        try:
            content = flow.response.get_text()
        except Exception:
            return
        if not content:
            return

        ph = get_proxy_host()
        proxy_prefix = 'http://' + ph + ':' + str(PROXY_PORT)

        parsed_url = urlparse(flow.request.url)
        base_scheme = parsed_url.scheme or 'https'
        base_host = parsed_url.netloc or ''

        content = self._rewrite_webpack_public_path(content, proxy_prefix, base_scheme, base_host)

        if 'self.__next_f.push' not in content and ':HL[' not in content:
            flow.response.set_text(content)
            return

        def to_proxy_url(url):
            if url.startswith(('http://', 'https://')):
                try:
                    p = urlparse(url)
                    return f'{proxy_prefix}/{p.scheme}/{p.netloc}{p.path}'
                except Exception:
                    return url
            return url

        def replace_next_push_urls(match):
            push_content = match.group(0)

            def replace_absolute_urls(s_match):
                url = s_match.group(1)
                if not url or len(url) < 5:
                    return s_match.group(0)
                if url.startswith(('data:', 'javascript:', 'mailto:', 'blob:', '#', 'about:')):
                    return s_match.group(0)
                if url.startswith(proxy_prefix):
                    return s_match.group(0)
                if ph and (ph in url):
                    return s_match.group(0)
                if url.startswith('https://') or url.startswith('http://'):
                    return '"' + to_proxy_url(url) + '"'
                return s_match.group(0)

            result = re.sub(r'"(https?://[^"]+)"', replace_absolute_urls, push_content)
            return result

        content = re.sub(r'self\.__next_f\.push\(\[[\s\S]*?\]\)', replace_next_push_urls, content)

        def replace_hl_links(match):
            hl_content = match.group(0)
            def replace_urls(u_match):
                u = u_match.group(1).strip().strip('`')
                if u.startswith('http://') or u.startswith('https://'):
                    return '`' + to_proxy_url(u) + '`'
                return u_match.group(0)
            result = re.sub(r'`([^`]+)`', replace_urls, hl_content)
            return result

        content = re.sub(r':HL\[.*?\]', replace_hl_links, content)
        flow.response.set_text(content)

    def _rewrite_webpack_public_path(self, content, proxy_prefix, base_scheme, base_host):
        pattern = re.compile(
            r'(__webpack_require__\s*\.\s*p\s*=\s*|__webpack_public_path__\s*=\s*|[a-zA-Z_$]\s*\.\s*p\s*=\s*)'
            r'(["\'])(https?://[^"\']+)(["\'])',
            re.IGNORECASE
        )

        def replace_public_path(match):
            assignment = match.group(1)
            open_quote = match.group(2)
            original_url = match.group(3)
            close_quote = match.group(4)

            try:
                p = urlparse(original_url)
                if p.scheme in ('http', 'https') and p.netloc:
                    proxy_url = f'{proxy_prefix}/{p.scheme}/{p.netloc}{p.path}'
                    if p.query:
                        proxy_url += '?' + p.query
                    return f'{assignment}{open_quote}{proxy_url}{close_quote}'
            except Exception:
                pass
            return match.group(0)

        content = pattern.sub(replace_public_path, content)
        return content

    def _rewrite_css(self, flow):
        try:
            content = flow.response.get_text()
        except Exception:
            return
        if not content:
            return

        ph = get_proxy_host()
        proxy_prefix = 'http://' + ph + ':' + str(PROXY_PORT) + '/'

        pattern = re.compile(r'(url\s*\(\s*["\']?)([^)"\'\s]+)(["\']?\s*\))', re.IGNORECASE)

        def replace_url(match):
            return match.group(1) + self._rewrite_asset_url(match.group(2), proxy_prefix) + match.group(3)

        content = pattern.sub(replace_url, content)

        import_pattern = re.compile(r'(@import\s+["\'])([^"\']+)(["\'])', re.IGNORECASE)

        def replace_import(match):
            return match.group(1) + self._rewrite_asset_url(match.group(2), proxy_prefix) + match.group(3)

        content = import_pattern.sub(replace_import, content)
        flow.response.set_text(content)

    def _rewrite_json(self, flow):
        try:
            content = flow.response.get_text()
        except Exception:
            return
        if not content:
            return

        ph = get_proxy_host()
        proxy_prefix = 'http://' + ph + ':' + str(PROXY_PORT) + '/'

        pattern = re.compile(r'(https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+)', re.IGNORECASE)

        def replace_url(match):
            url = match.group(1)
            if url.startswith(proxy_prefix):
                return url
            try:
                parsed = urlparse(url)
                if parsed.scheme in ('http', 'https') and parsed.netloc and parsed.netloc != ph:
                    proxy_path = 'getassets/' + parsed.scheme + '/' + parsed.netloc + parsed.path
                    if parsed.query:
                        proxy_path += '?' + parsed.query
                    return proxy_prefix + proxy_path
            except Exception:
                pass
            return url

        content = pattern.sub(replace_url, content)
        flow.response.set_text(content)

    def _rewrite_asset_url(self, url, proxy_prefix):
        if not url or not isinstance(url, str):
            return url
        if url.startswith(proxy_prefix):
            return url
        try:
            parsed = urlparse(url)
            if parsed.scheme in ('http', 'https') and parsed.netloc and parsed.netloc != get_proxy_host():
                proxy_path = 'getassets/' + parsed.scheme + '/' + parsed.netloc + parsed.path
                if parsed.query:
                    proxy_path += '?' + parsed.query
                return proxy_prefix + proxy_path
        except Exception:
            pass
        return url


addons = [WebProxyAddon()]