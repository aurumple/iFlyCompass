import os
import asyncio
import threading
import subprocess
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from config import Config

try:
    from bilibili_api import select_client
    select_client("curl_cffi")
except Exception as e:
    print(f'[Bili] 无法选择 curl_cffi: {e}')

BILI_DIR = os.path.join(Config.TEMP_DIR, 'bili') if Config.TEMP_DIR else os.path.join(os.path.dirname(__file__), '..', 'temp', 'bili')

FFMPEG_PATH = None
HAS_QSV = False  # 是否支持 Intel QSV 硬件加速

QUALITY_MAP = {
    16: '360P',
    32: '480P',
    64: '720P',
    74: '720P60',
    80: '1080P',
    112: '1080P+',
    116: '1080P60',
    120: '4K',
}

DEFAULT_QUALITY = 32
MAX_CONCURRENT_DOWNLOADS = 2

download_tasks = {}
download_lock = threading.Lock()
active_downloads = 0
download_semaphore = threading.Semaphore(MAX_CONCURRENT_DOWNLOADS)
download_queue = Queue()
executor = ThreadPoolExecutor(max_workers=5)


def check_ffmpeg():
    global FFMPEG_PATH
    from utils.ffmpeg import ensure_ffmpeg

    ffmpeg_path = ensure_ffmpeg()
    if ffmpeg_path:
        FFMPEG_PATH = ffmpeg_path
        return True

    FFMPEG_PATH = None
    return False


def check_qsv_support():
    """检测 FFmpeg 是否支持 Intel QSV 硬件编码器"""
    global HAS_QSV
    if not FFMPEG_PATH:
        return False
    try:
        # 运行 ffmpeg -encoders 并检查是否包含 h264_qsv
        creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        result = subprocess.run(
            [FFMPEG_PATH, '-encoders'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
            timeout=10
        )
        has_qsv = 'h264_qsv' in result.stdout
        print(f'[Bili] Intel QSV 硬件加速支持: {has_qsv}')
        return has_qsv
    except Exception as e:
        print(f'[Bili] 检测 Intel QSV 支持失败: {e}')
        return False


check_ffmpeg()
HAS_QSV = check_qsv_support()


def get_video_encoder_params(use_qsv=False):
    """
    根据是否使用 QSV 返回对应的视频编码参数
    软件编码时添加 -threads 0 启用多线程加速
    """
    if use_qsv:
        # Intel QSV 硬件编码，-global_quality 范围 0-51，类似 CRF
        return ['-c:v', 'h264_qsv', '-global_quality', '23', '-preset', 'veryfast']
    else:
        # 软件编码，-threads 0 让 x264 自动决定线程数（多线程）
        return ['-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-threads', '0']


def _is_qsv_error(error_lines):
    """检查FFmpeg错误输出是否由QSV硬件编码失败引起"""
    for line in error_lines:
        if 'MFX' in line or 'mfx' in line or 'h264_qsv' in line:
            return True
    return False


def safe_rename(src, dst):
    """跨平台安全重命名，Windows下目标存在时先删除"""
    if os.path.exists(dst):
        try:
            os.remove(dst)
        except OSError:
            pass
    os.rename(src, dst)


def ensure_bili_dir():
    if not os.path.exists(BILI_DIR):
        os.makedirs(BILI_DIR)


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def get_video_info_sync(bvid):
    from bilibili_api import video

    async def _get_info():
        v = video.Video(bvid=bvid)
        info = await v.get_info()
        cid = info.get('cid', 0)
        if not cid and info.get('pages'):
            cid = info['pages'][0].get('cid', 0)
        return info, cid

    return run_async(_get_info())


def get_download_streams_sync(bvid, cid):
    from bilibili_api import video
    from bilibili_api.video import VideoDownloadURLDataDetecter, VideoQuality

    async def _get_streams():
        v = video.Video(bvid=bvid)
        url_data = await v.get_download_url(cid=cid)

        detecter = VideoDownloadURLDataDetecter(url_data)
        streams = detecter.detect_best_streams(
            video_max_quality=VideoQuality._480P,
            video_min_quality=VideoQuality._360P
        )
        return streams

    return run_async(_get_streams())


def get_video_cache_path(bvid):
    ensure_bili_dir()
    return os.path.join(BILI_DIR, f'{bvid}.mp4')


def is_video_cached(bvid):
    path = get_video_cache_path(bvid)
    return os.path.exists(path)


def get_cached_videos():
    ensure_bili_dir()
    videos = []
    try:
        for filename in os.listdir(BILI_DIR):
            if filename.endswith('.mp4'):
                bvid = filename[:-4]
                filepath = os.path.join(BILI_DIR, filename)
                size = os.path.getsize(filepath)
                videos.append({
                    'bvid': bvid,
                    'size': size,
                    'size_display': format_size(size)
                })
    except Exception as e:
        print(f'[Bili] 扫描缓存目录失败: {e}')
    return videos


def format_size(size):
    if size < 1024:
        return f'{size} B'
    elif size < 1024 * 1024:
        return f'{size / 1024:.1f} KB'
    elif size < 1024 * 1024 * 1024:
        return f'{size / (1024 * 1024):.1f} MB'
    else:
        return f'{size / (1024 * 1024 * 1024):.2f} GB'


class DownloadTask:
    def __init__(self, bvid, title, cid):
        self.bvid = bvid
        self.title = title
        self.cid = cid
        self.status = 'pending'
        self.progress = 0
        self.downloaded = 0
        self.total = 0
        self.speed = 0
        self.error = None
        self.start_time = None
        self.last_update = None
        self.last_downloaded = 0
        self.converting_progress = 0
        self.queue_position = 0

    def to_dict(self):
        return {
            'bvid': self.bvid,
            'title': self.title,
            'status': self.status,
            'progress': self.progress,
            'downloaded': self.downloaded,
            'total': self.total,
            'downloaded_display': format_size(self.downloaded),
            'total_display': format_size(self.total),
            'speed': self.speed,
            'speed_display': format_size(self.speed) + '/s' if self.speed > 0 else '0 B/s',
            'error': self.error,
            'converting_progress': self.converting_progress,
            'queue_position': self.queue_position
        }


def download_file(url, filepath, task, headers=None):
    req_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/',
    }
    if headers:
        req_headers.update(headers)

    print(f'[Bili] 开始下载: {url[:100]}...')

    resp = requests.get(url, headers=req_headers, stream=True, timeout=30, allow_redirects=True)
    total_size = int(resp.headers.get('content-length', 0))
    task.total = total_size
    print(f'[Bili] 文件总大小: {format_size(total_size) if total_size > 0 else "未知"}')

    downloaded = 0
    last_check = time.time()
    last_downloaded = 0

    with open(filepath, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                task.downloaded = downloaded

                now = time.time()
                if now - last_check >= 0.3:
                    elapsed = now - last_check
                    task.speed = int((downloaded - last_downloaded) / elapsed) if elapsed > 0 else 0
                    if task.total > 0:
                        task.progress = int(task.downloaded / task.total * 100)
                    else:
                        task.progress = min(99, int(downloaded / (1024 * 1024) * 10))
                    last_check = now
                    last_downloaded = downloaded

                    print(f'[Bili] 下载进度: {task.progress}% ({format_size(downloaded)}) 速度: {format_size(task.speed)}/s')

    actual_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
    task.downloaded = actual_size
    task.total = actual_size if actual_size > total_size else total_size
    task.progress = 100
    print(f'[Bili] 下载完成: {filepath}, 实际大小: {format_size(actual_size)}')
    return actual_size


def convert_to_h264(input_path, output_path, task, force_software=False):
    if not FFMPEG_PATH or not os.path.exists(input_path):
        print(f'[Bili] FFmpeg未找到或输入文件不存在，跳过转换')
        if os.path.exists(input_path):
            safe_rename(input_path, output_path)
            return True
        return False

    input_size = os.path.getsize(input_path)
    print(f'[Bili] 开始转换视频为H264格式: {input_path} -> {output_path} ({format_size(input_size)})')

    try:
        use_qsv = HAS_QSV and not force_software
        encoder_params = get_video_encoder_params(use_qsv)
        cmd = [
            FFMPEG_PATH, '-y',
            '-i', input_path,
        ] + encoder_params + [
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            output_path
        ]

        print(f'[Bili] FFmpeg命令: {" ".join(cmd)}')

        creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            creationflags=creationflags
        )

        duration = None
        error_output = []
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break

            if line:
                error_output.append(line.strip())

                if 'Duration:' in line:
                    import re
                    match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                    if match:
                        h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                        duration = h * 3600 + m * 60 + s + ms / 100
                        print(f'[Bili] 视频时长: {duration}秒')

                if 'time=' in line and duration:
                    import re
                    match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                    if match:
                        h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                        current_time = h * 3600 + m * 60 + s + ms / 100
                        if duration > 0:
                            task.converting_progress = int((current_time / duration) * 100)
                            print(f'[Bili] 转换进度: {task.converting_progress}%')

                if 'Error' in line or 'error' in line:
                    print(f'[Bili] FFmpeg输出: {line.strip()}')

        process.wait()

        if process.returncode == 0:
            output_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            print(f'[Bili] 视频转换完成: {output_path} ({format_size(output_size)})')
            return True
        else:
            print(f'[Bili] FFmpeg转换失败，返回码: {process.returncode}')
            print(f'[Bili] 错误输出:')
            for line in error_output[-20:]:
                print(f'    {line}')

            if use_qsv and _is_qsv_error(error_output):
                print(f'[Bili] 检测到QSV硬件编码失败，回退到libx264软件编码重试')
                return convert_to_h264(input_path, output_path, task, force_software=True)

            return False

    except FileNotFoundError:
        print('[Bili] FFmpeg未找到，跳过转换')
        if os.path.exists(input_path):
            safe_rename(input_path, output_path)
            return True
        return False
    except Exception as e:
        print(f'[Bili] 转换异常: {e}')
        import traceback
        traceback.print_exc()
        return False


def merge_and_convert_video_audio(video_path, audio_path, output_path, task, force_software=False):
    if not FFMPEG_PATH:
        print('[Bili] FFmpeg未找到，跳过合并转换')
        return False

    video_exists = os.path.exists(video_path)
    audio_exists = os.path.exists(audio_path)
    video_size = os.path.getsize(video_path) if video_exists else 0
    audio_size = os.path.getsize(audio_path) if audio_exists else 0

    print(f'[Bili] 开始合并并转换视频: video={video_path}({format_size(video_size)}), audio={audio_path}({format_size(audio_size)}), output={output_path}')

    if not video_exists:
        print(f'[Bili] 视频文件不存在: {video_path}')
        return False

    try:
        use_qsv = HAS_QSV and not force_software
        encoder_params = get_video_encoder_params(use_qsv)
        cmd = [FFMPEG_PATH, '-y', '-i', video_path]
        if audio_exists:
            cmd.extend(['-i', audio_path])
        cmd.extend(encoder_params)
        if audio_exists:
            cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
        else:
            cmd.extend(['-an'])
        cmd.extend(['-movflags', '+faststart', output_path])

        print(f'[Bili] FFmpeg命令: {" ".join(cmd)}')

        creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            creationflags=creationflags
        )

        duration = None
        error_output = []
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break

            if line:
                error_output.append(line.strip())

                if 'Duration:' in line:
                    import re
                    match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                    if match:
                        h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                        duration = h * 3600 + m * 60 + s + ms / 100
                        print(f'[Bili] 视频时长: {duration}秒')

                if 'time=' in line and duration:
                    import re
                    match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                    if match:
                        h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
                        current_time = h * 3600 + m * 60 + s + ms / 100
                        if duration > 0:
                            task.converting_progress = int((current_time / duration) * 100)
                            print(f'[Bili] 合并进度: {task.converting_progress}%')

        process.wait()

        if process.returncode == 0:
            output_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            print(f'[Bili] 视频合并转换完成: {output_path} ({format_size(output_size)})')
            return True
        else:
            print(f'[Bili] FFmpeg合并转换失败，返回码: {process.returncode}')
            print(f'[Bili] 错误输出:')
            for line in error_output[-20:]:
                print(f'    {line}')

            if use_qsv and _is_qsv_error(error_output):
                print(f'[Bili] 检测到QSV硬件编码失败，回退到libx264软件编码重试')
                return merge_and_convert_video_audio(video_path, audio_path, output_path, task, force_software=True)

            return False

    except FileNotFoundError:
        print('[Bili] FFmpeg未找到，尝试直接复制')
        return False
    except Exception as e:
        print(f'[Bili] 合并转换异常: {e}')
        import traceback
        traceback.print_exc()
        return False


def download_video_task(task):
    from bilibili_api.video import VideoStreamDownloadURL, AudioStreamDownloadURL, FLVStreamDownloadURL, MP4StreamDownloadURL

    global active_downloads

    with download_semaphore:
        with download_lock:
            active_downloads += 1
            task.status = 'fetching'
            task.queue_position = 0

        try:
            task.start_time = time.time()
            task.last_update = time.time()

            print(f'[Bili] 开始获取视频信息: {task.bvid}')
            info, cid = get_video_info_sync(task.bvid)
            task.title = info.get('title', task.bvid)
            print(f'[Bili] 视频标题: {task.title}')

            print(f'[Bili] 开始获取下载流')
            streams = get_download_streams_sync(task.bvid, cid)

            if not streams:
                raise Exception('未找到可用的下载流')

            video_path = get_video_cache_path(task.bvid)
            temp_video_path = video_path + '.video'
            temp_audio_path = video_path + '.audio'
            temp_merged_path = video_path + '.merged.mp4'

            headers = {'Referer': 'https://www.bilibili.com/'}

            if len(streams) == 1 and isinstance(streams[0], (FLVStreamDownloadURL, MP4StreamDownloadURL)):
                print(f'[Bili] 单流模式下载')
                stream = streams[0]
                url = stream.url
                task.status = 'downloading'
                download_file(url, temp_merged_path, task, headers)

                merged_size = os.path.getsize(temp_merged_path) if os.path.exists(temp_merged_path) else 0

                if merged_size < 1024:
                    raise Exception(f'下载的文件太小({merged_size}B)，可能是无效文件')

                task.status = 'converting'
                task.converting_progress = 0
                print(f'[Bili] 开始转换为H264格式')
                success = convert_to_h264(temp_merged_path, video_path, task)

                if success:
                    try:
                        os.remove(temp_merged_path)
                    except:
                        pass
                    task.status = 'completed'
                    task.progress = 100
                    print(f'[Bili] 视频处理成功: {video_path}')
                else:
                    print(f'[Bili] 转换失败，保留原始文件')
                    if os.path.exists(temp_merged_path):
                        safe_rename(temp_merged_path, video_path)
                    task.status = 'completed'
                    task.progress = 100
                    task.error = '视频转换失败，保留原始格式'

            elif len(streams) >= 2:
                print(f'[Bili] 双流模式下载（音视频分离）')
                video_stream = None
                audio_stream = None

                for s in streams:
                    if isinstance(s, VideoStreamDownloadURL) and video_stream is None:
                        video_stream = s
                    elif isinstance(s, AudioStreamDownloadURL) and audio_stream is None:
                        audio_stream = s

                if not video_stream:
                    raise Exception('未找到视频流')

                video_url = video_stream.url
                audio_url = audio_stream.url if audio_stream else None

                print(f'[Bili] 视频流URL: {video_url[:100]}...')
                if audio_url:
                    print(f'[Bili] 音频流URL: {audio_url[:100]}...')

                task.status = 'downloading'

                print(f'[Bili] 开始下载视频流')
                download_file(video_url, temp_video_path, task, headers)

                video_size = os.path.getsize(temp_video_path) if os.path.exists(temp_video_path) else 0
                if video_size < 1024:
                    raise Exception(f'下载的视频文件太小({video_size}B)')

                if audio_url:
                    print(f'[Bili] 开始下载音频流')
                    download_file(audio_url, temp_audio_path, task, headers)

                    audio_size = os.path.getsize(temp_audio_path) if os.path.exists(temp_audio_path) else 0
                    if audio_size < 1024:
                        print(f'[Bili] 警告: 音频文件较小({audio_size}B)')

                task.status = 'converting'
                task.converting_progress = 0
                print(f'[Bili] 开始合并并转换为H264格式')

                if audio_url and os.path.exists(temp_audio_path) and os.path.exists(temp_video_path):
                    success = merge_and_convert_video_audio(temp_video_path, temp_audio_path, video_path, task)
                    if success:
                        try:
                            os.remove(temp_video_path)
                            os.remove(temp_audio_path)
                        except:
                            pass
                        print(f'[Bili] 视频合并转换成功: {video_path}')
                    else:
                        print(f'[Bili] 合并转换失败，尝试仅转换视频')
                        if os.path.exists(temp_video_path):
                            success2 = convert_to_h264(temp_video_path, video_path, task)
                            if success2:
                                try:
                                    os.remove(temp_video_path)
                                    if os.path.exists(temp_audio_path):
                                        os.remove(temp_audio_path)
                                except:
                                    pass
                                print(f'[Bili] 视频转换成功: {video_path}')
                            else:
                                print(f'[Bili] 转换失败，保留原始文件')
                                if os.path.exists(temp_video_path):
                                    safe_rename(temp_video_path, video_path)
                                task.error = '视频转换失败，保留原始格式'
                else:
                    if os.path.exists(temp_video_path):
                        success = convert_to_h264(temp_video_path, video_path, task)
                        if success:
                            try:
                                os.remove(temp_video_path)
                            except:
                                pass
                            print(f'[Bili] 视频转换成功: {video_path}')
                        else:
                            print(f'[Bili] 转换失败，保留原始文件')
                            safe_rename(temp_video_path, video_path)
                            task.error = '视频转换失败，保留原始格式'

                task.status = 'completed'
                task.progress = 100
                print(f'[Bili] 下载完成: {video_path}')
            else:
                raise Exception('未找到可用的下载地址')

        except Exception as e:
            task.status = 'error'
            task.error = str(e)
            print(f'[Bili] 下载失败 {task.bvid}: {e}')
            import traceback
            traceback.print_exc()
        finally:
            with download_lock:
                active_downloads -= 1


def update_queue_positions():
    with download_lock:
        pending_tasks = [t for t in download_tasks.values() if t.status == 'pending']
        for i, task in enumerate(pending_tasks):
            task.queue_position = i + 1


def start_download(bvid):
    with download_lock:
        if bvid in download_tasks:
            task = download_tasks[bvid]
            if task.status in ['pending', 'downloading', 'fetching', 'merging', 'converting']:
                return task

        if is_video_cached(bvid):
            return None

        try:
            info, cid = get_video_info_sync(bvid)
            title = info.get('title', bvid)

            task = DownloadTask(bvid, title, cid)
            download_tasks[bvid] = task

            pending_count = len([t for t in download_tasks.values() if t.status == 'pending'])
            active_count = len([t for t in download_tasks.values() if t.status in ['downloading', 'fetching', 'converting']])

            if active_count >= MAX_CONCURRENT_DOWNLOADS:
                task.status = 'pending'
                task.queue_position = pending_count + 1
                print(f'[Bili] 下载任务排队中: {bvid}, 队列位置: {task.queue_position}')
            else:
                task.queue_position = 0
                executor.submit(download_video_task, task)

            return task
        except Exception as e:
            raise Exception(f'启动下载失败: {e}')


def get_download_progress(bvid):
    with download_lock:
        if bvid in download_tasks:
            return download_tasks[bvid].to_dict()
    return None


def get_all_downloads():
    with download_lock:
        return [task.to_dict() for task in download_tasks.values()]


def delete_cached_video(bvid):
    path = get_video_cache_path(bvid)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def get_video_info(bvid):
    info, cid = get_video_info_sync(bvid)
    return info
