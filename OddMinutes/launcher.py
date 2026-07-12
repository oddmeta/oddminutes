# -*- coding: utf-8 -*-
import os
import sys
import time
import subprocess
import webbrowser
import socket
import argparse
import importlib.util
import threading
import shutil
import appdirs


def setup_logging(project_dir):
    log_dir = os.path.join(project_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'launcher.log')
    
    log_file = open(log_path, 'a', encoding='utf-8')
    sys.stdout = log_file
    sys.stderr = log_file
    
    print(f'\n=== 启动器日志 {time.strftime("%Y-%m-%d %H:%M:%S")} ===')


def check_dependencies(project_dir):
    critical_packages = {
        'django': 'django',
        'daphne': 'daphne',
        'channels': 'channels',
        'rest_framework': 'rest_framework',
        'dotenv': 'dotenv',
        'corsheaders': 'corsheaders',
        'pystray': 'pystray',
        'PIL': 'PIL',
        'requests': 'requests',
    }
    
    missing = []
    for display_name, module_name in critical_packages.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(display_name)
    
    if missing:
        print(f'缺少以下依赖: {", ".join(missing)}')
        print('正在自动安装依赖...')
        
        requirements_path = os.path.join(project_dir, 'requirements.txt')
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', requirements_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            if result.returncode == 0:
                print('依赖安装成功')
            else:
                print(f'依赖安装失败: {result.stderr}')
                print('请手动运行: pip install -r requirements.txt')
                sys.exit(1)
                
        except Exception as e:
            print(f'安装依赖时出错: {e}')
            sys.exit(1)
    else:
        print('所有依赖已安装')


def check_port_in_use(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0
    except Exception:
        return False


def wait_for_server(url, timeout=30):
    import requests
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def start_server(project_dir, port):
    os.chdir(project_dir)
    
    env = os.environ.copy()
    env['DJANGO_SETTINGS_MODULE'] = 'meeting_minutes.settings'
    
    log_dir = os.path.join(project_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'daphne.log')
    
    print('初始化数据库...')
    try:
        migrate_result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate'],
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        if migrate_result.returncode == 0:
            print('数据库初始化成功')
        else:
            print(f'数据库初始化失败: {migrate_result.stderr}')
    except Exception as e:
        print(f'数据库初始化异常: {e}')
    
    server_cmd = [
        sys.executable, '-m', 'daphne',
        'meeting_minutes.asgi:application',
        '--port', str(port),
        '--bind', '127.0.0.1'
    ]
    
    log_file = open(log_path, 'a', encoding='utf-8')
    
    process = subprocess.Popen(
        server_cmd,
        env=env,
        stdout=log_file,
        stderr=log_file,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    )
    return process


def get_package_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bootstrap_user_data_dir():
    package_dir = get_package_dir()
    user_data_dir = appdirs.user_data_dir('OddMinutes', 'OddMeta')
    
    os.makedirs(user_data_dir, exist_ok=True)
    
    required_files = ['manage.py', '.env.example']
    required_dirs = ['meeting_minutes', 'templates', 'static', 'core', 'meetings', 'recording', 'transcription', 'summary', 'system_app']
    
    for filename in required_files:
        src = os.path.join(package_dir, filename)
        dst = os.path.join(user_data_dir, filename)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
    
    for dirname in required_dirs:
        src = os.path.join(package_dir, dirname)
        dst = os.path.join(user_data_dir, dirname)
        if os.path.isdir(src) and not os.path.exists(dst):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif os.path.isdir(src) and os.path.isdir(dst):
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                if os.path.isdir(s) and not os.path.exists(d):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                elif os.path.isfile(s) and not os.path.exists(d):
                    shutil.copy2(s, d)
    
    env_path = os.path.join(user_data_dir, '.env')
    env_example_path = os.path.join(user_data_dir, '.env.example')
    if not os.path.exists(env_path) and os.path.exists(env_example_path):
        shutil.copy2(env_example_path, env_path)
    
    media_dir = os.path.join(user_data_dir, 'media')
    os.makedirs(media_dir, exist_ok=True)
    
    return user_data_dir


def find_project_dir():
    candidates = []
    
    candidates.append(os.getcwd())
    
    candidates.append(os.environ.get('ODDMINUTES_PROJECT_DIR'))
    
    script_dir = get_package_dir()
    candidates.append(script_dir)
    
    for candidate in candidates:
        if candidate and os.path.isfile(os.path.join(candidate, 'manage.py')):
            return candidate
    
    print(f'未找到项目目录，正在从包安装位置引导...')
    user_data_dir = bootstrap_user_data_dir()
    print(f'项目目录已引导至: {user_data_dir}')
    return user_data_dir


def main():
    parser = argparse.ArgumentParser(description='小奥会议纪要启动器')
    parser.add_argument('--port', type=int, default=9011, help='服务端口')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    parser.add_argument('--debug', action='store_true', help='显示控制台窗口')
    parser.add_argument('--project-dir', type=str, help='项目目录')
    args = parser.parse_args()
    
    if args.project_dir:
        project_dir = args.project_dir
    else:
        project_dir = find_project_dir()
    
    url = f'http://127.0.0.1:{args.port}'
    
    if not args.debug:
        setup_logging(project_dir)
    
    check_dependencies(project_dir)
    
    if check_port_in_use(args.port):
        print(f'端口 {args.port} 已被占用，直接打开浏览器')
        if not args.no_browser:
            webbrowser.open(url)
        return
    
    print(f'启动小奥会议纪要...')
    print(f'项目目录: {project_dir}')
    
    process = start_server(project_dir, args.port)
    
    print(f'等待服务器启动...')
    if wait_for_server(url):
        print(f'服务器已启动: {url}')
        if not args.no_browser:
            webbrowser.open(url)
        print('服务已启动，日志文件: logs/launcher.log')
        
        sys.path.insert(0, project_dir)
        try:
            from system_app.tray_icon import get_tray_manager
            import requests
            
            tray_manager = get_tray_manager()
            
            recording_status = {'recording': False, 'paused': False, 'meeting_id': None}
            
            def fetch_recording_status():
                try:
                    status_url = f'{url}/api/recording/status/'
                    resp = requests.get(status_url, timeout=5)
                    data = resp.json()
                    is_recording = data.get('recording', False)
                    recording_status['recording'] = is_recording
                    recording_status['meeting_id'] = data.get('meeting_id')
                    if is_recording:
                        tray_manager.update_tooltip('正在录音...')
                    else:
                        tray_manager.update_tooltip('小奥会议纪要')
                    tray_manager.update_recording_state(is_recording, recording_status.get('paused', False))
                except Exception as e:
                    print(f'获取录音状态失败: {e}')
            
            fetch_recording_status()
            
            def status_polling_thread():
                while True:
                    try:
                        fetch_recording_status()
                        time.sleep(3)
                    except Exception as e:
                        print(f'状态轮询异常: {e}')
                        time.sleep(5)
            
            polling_thread = threading.Thread(target=status_polling_thread, daemon=True)
            polling_thread.start()
            
            def on_exit():
                if recording_status['recording']:
                    stop_recording(url, recording_status)
                process.terminate()
                print('服务已停止')
                sys.exit(0)
            
            def on_show_window():
                webbrowser.open(url)
            
            def on_new_meeting():
                try:
                    create_meeting_url = f'{url}/api/meetings/'
                    create_data = {
                        'title': f'新会议 {time.strftime("%Y-%m-%d %H:%M:%S")}',
                    }
                    resp = requests.post(create_meeting_url, json=create_data, timeout=10)
                    result = resp.json()
                    
                    if resp.status_code == 409:
                        error_msg = result.get('error', '创建会议失败')
                        print(f'创建会议失败: {error_msg}')
                        tray_manager.update_tooltip(error_msg)
                        return
                    
                    meeting_id = result.get('id')
                    if meeting_id:
                        print(f'新会议已创建: {meeting_id}')
                        recording_status['meeting_id'] = meeting_id
                        tray_manager.update_tooltip('新会议已创建')
                    else:
                        print(f'创建会议失败: {result}')
                except Exception as e:
                    print(f'创建新会议失败: {e}')
            
            def on_start_recording():
                try:
                    status_url = f'{url}/api/recording/status/'
                    status_resp = requests.get(status_url, timeout=5)
                    status_data = status_resp.json()
                    if status_data.get('recording'):
                        print('已有会议正在录音中，无法启动新录音')
                        tray_manager.update_tooltip('已有会议正在录音中')
                        return
                    
                    meeting_id = recording_status.get('meeting_id')
                    
                    if not meeting_id:
                        create_meeting_url = f'{url}/api/meetings/'
                        create_data = {
                            'title': f'快速录音 {time.strftime("%Y-%m-%d %H:%M:%S")}',
                        }
                        resp = requests.post(create_meeting_url, json=create_data, timeout=10)
                        result = resp.json()
                        meeting_id = result.get('id')
                        if meeting_id:
                            recording_status['meeting_id'] = meeting_id
                        else:
                            print('创建会议失败')
                            return
                    
                    start_recording_url = f'{url}/api/recording/start/'
                    start_data = {
                        'meeting_id': meeting_id,
                    }
                    start_resp = requests.post(start_recording_url, json=start_data, timeout=10)
                    start_result = start_resp.json()
                    if start_resp.ok and start_result.get('status') == 'recording':
                        recording_status['recording'] = True
                        recording_status['paused'] = False
                        tray_manager.update_tooltip('正在录音...')
                        tray_manager.update_recording_state(True, False)
                        print('录音已开始')
                    else:
                        print(f'启动录音失败: {start_result}')
                        if 'error' in start_result:
                            tray_manager.update_tooltip(start_result['error'])
                except Exception as e:
                    print(f'开始录音失败: {e}')
            
            def on_stop_recording():
                stop_recording(url, recording_status)
                tray_manager.update_recording_state(False, False)
            
            def on_pause_recording():
                if recording_status['meeting_id']:
                    try:
                        pause_url = f'{url}/api/recording/pause/'
                        pause_data = {
                            'meeting_id': recording_status['meeting_id'],
                        }
                        resp = requests.post(pause_url, json=pause_data, timeout=10)
                        result = resp.json()
                        if resp.ok:
                            recording_status['paused'] = True
                            tray_manager.update_tooltip('录音已暂停')
                            tray_manager.update_recording_state(True, True)
                            print('录音已暂停')
                        else:
                            print(f'暂停录音失败: {result}')
                    except Exception as e:
                        print(f'暂停录音失败: {e}')
            
            def on_resume_recording():
                if recording_status['meeting_id']:
                    try:
                        resume_url = f'{url}/api/recording/resume/'
                        resume_data = {
                            'meeting_id': recording_status['meeting_id'],
                        }
                        resp = requests.post(resume_url, json=resume_data, timeout=10)
                        result = resp.json()
                        if resp.ok:
                            recording_status['paused'] = False
                            tray_manager.update_tooltip('正在录音...')
                            tray_manager.update_recording_state(True, False)
                            print('录音已继续')
                        else:
                            print(f'继续录音失败: {result}')
                    except Exception as e:
                        print(f'继续录音失败: {e}')
            
            def stop_recording(base_url, status):
                if status['meeting_id']:
                    try:
                        stop_url = f'{base_url}/api/recording/stop/'
                        stop_data = {
                            'meeting_id': status['meeting_id'],
                        }
                        resp = requests.post(stop_url, json=stop_data, timeout=10)
                        result = resp.json()
                        print(f'录音已停止: {result}')
                    except Exception as e:
                        print(f'停止录音失败: {e}')
                
                status['recording'] = False
                status['paused'] = False
                status['meeting_id'] = None
                tray_manager.update_tooltip('小奥会议纪要')
            
            tray_manager.set_callbacks(
                on_new_meeting=on_new_meeting,
                on_start_recording=on_start_recording,
                on_stop_recording=on_stop_recording,
                on_pause_recording=on_pause_recording,
                on_resume_recording=on_resume_recording,
                on_show_window=on_show_window,
                on_exit=on_exit
            )
            tray_manager.start()
            print('系统托盘图标已启动')
        except Exception as e:
            print(f'启动系统托盘图标失败: {e}')
        
        try:
            process.wait()
        except KeyboardInterrupt:
            process.terminate()
            print('服务已停止')
    else:
        print('服务器启动超时')
        process.terminate()


if __name__ == '__main__':
    main()
