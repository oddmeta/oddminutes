# -*- coding: utf-8 -*-
import os
import sys
import subprocess


def create_app_icon(project_dir):
    icon_path = os.path.join(project_dir, 'static', 'favicon.ico')
    if os.path.exists(icon_path):
        try:
            from PIL import Image
            img = Image.open(icon_path)
            if img.format == 'ICO':
                return icon_path
        except:
            pass
    
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print('PIL not installed, skipping icon generation')
        return None
    
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    
    images = []
    for size in sizes:
        img = Image.new('RGBA', size, (30, 41, 59, 0))
        draw = ImageDraw.Draw(img)
        
        padding = size[0] // 6
        inner_size = size[0] - padding * 2
        
        draw.ellipse(
            [padding, padding, padding + inner_size, padding + inner_size],
            fill=(59, 130, 246),
            outline=None
        )
        
        center_x = size[0] // 2
        center_y = size[1] // 2
        
        w = inner_size * 0.35
        h = inner_size * 0.5
        half_w = w / 2
        half_h = h / 2
        
        draw.polygon(
            [
                (center_x, center_y - half_h),
                (center_x - half_w, center_y + half_h * 0.6),
                (center_x, center_y + half_h * 0.2),
                (center_x + half_w, center_y + half_h * 0.6),
            ],
            fill=(255, 255, 255),
            outline=None
        )
        
        img = img.convert('RGBA')
        images.append(img)
    
    images[0].save(icon_path, format='ICO', append_images=images[1:], sizes=sizes)
    print(f'Icon created: {icon_path}')
    return icon_path


def create_shortcut():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    launcher_path = os.path.join(project_dir, 'launcher.py')
    
    python_dir = os.path.dirname(sys.executable)
    pythonw_exe = os.path.join(python_dir, 'pythonw.exe')
    if not os.path.exists(pythonw_exe):
        pythonw_exe = sys.executable
    
    python_exe = sys.executable
    
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    
    icon_path = create_app_icon(project_dir)
    
    powershell_script = f'''
$WshShell = New-Object -ComObject WScript.Shell

$shortcut1 = $WshShell.CreateShortcut("{os.path.join(desktop_path, '小奥会议纪要.lnk')}")
$shortcut1.TargetPath = "{pythonw_exe}"
$shortcut1.Arguments = 'launcher.py'
$shortcut1.WorkingDirectory = "{project_dir}"
$shortcut1.Description = "小奥会议纪要"
$shortcut1.IconLocation = "{icon_path if icon_path else pythonw_exe}"
$shortcut1.Save()

$shortcut2 = $WshShell.CreateShortcut("{os.path.join(desktop_path, '小奥会议纪要-Debug.lnk')}")
$shortcut2.TargetPath = "{python_exe}"
$shortcut2.Arguments = 'launcher.py --debug'
$shortcut2.WorkingDirectory = "{project_dir}"
$shortcut2.Description = "小奥会议纪要 (Debug Mode)"
$shortcut2.IconLocation = "{icon_path if icon_path else python_exe}"
$shortcut2.Save()
'''
    
    result = subprocess.run(
        ['powershell', '-Command', powershell_script],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    if result.returncode == 0:
        print(f'Shortcut created: {os.path.join(desktop_path, "小奥会议纪要.lnk")}')
        print(f'Debug shortcut created: {os.path.join(desktop_path, "小奥会议纪要-Debug.lnk")}')
        return True
    else:
        print(f'Failed to create shortcuts: {result.stderr}')
        return False


if __name__ == '__main__':
    create_shortcut()