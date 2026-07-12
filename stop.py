# -*- coding: utf-8 -*-
import os
import sys
import socket
import subprocess


def stop_server(port=9011):
    project_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(project_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_path = os.path.join(log_dir, 'launcher.log')
    log_file = open(log_path, 'a', encoding='utf-8')
    
    try:
        import urllib.request
        url = f'http://127.0.0.1:{port}'
        try:
            urllib.request.urlopen(url, timeout=2)
        except Exception:
            print('服务未运行', file=log_file)
            print('服务未运行')
            return
    except ImportError:
        pass
    
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        pids = []
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pids.append(parts[-1])
        
        if not pids:
            print('未找到占用端口的进程', file=log_file)
            print('未找到占用端口的进程')
            return
        
        for pid in pids:
            try:
                subprocess.run(
                    ['taskkill', '/PID', pid, '/F'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                print(f'已终止进程 PID: {pid}', file=log_file)
                print(f'已终止进程 PID: {pid}')
            except Exception as e:
                print(f'终止进程 {pid} 失败: {e}', file=log_file)
        
        print('服务已停止', file=log_file)
        print('服务已停止')
        
    except Exception as e:
        print(f'停止服务时出错: {e}', file=log_file)
        print(f'停止服务时出错: {e}')


if __name__ == '__main__':
    stop_server()