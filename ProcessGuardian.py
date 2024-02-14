import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import psutil
import subprocess
import requests
import time
import json
import os

# GUIで設定された値を使うためのグローバル変数
process_path = ''
app_path = ''
interval = 1800  # 監視間隔のデフォルト値（30分
settings = {}
settings_path = os.path.join(os.path.expanduser('~'), 'Documents', 'ProcessGuardian', 'settings.json')

line_token_entry = None
process_path_entry = None

def save_settings(settings):
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    with open(settings_path, 'w') as f:
        json.dump(settings, f)

def load_settings():
    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    return settings

def open_settings_window():
    global line_token_entry, process_path_entry

    settings_window = tk.Toplevel(root)
    settings_window.title("設定")

    tk.Label(settings_window, text="LINE Notifyのトークン:").pack()
    line_token_entry = tk.Entry(settings_window)
    line_token_entry.pack()
    line_token_entry.insert(0, settings.get('line_token', ''))

    tk.Label(settings_window, text="プロセスパス:").pack()
    process_path_entry = tk.Entry(settings_window)
    process_path_entry.pack()
    process_path_entry.insert(0, settings.get('process_path', ''))

    def select_and_process_app():
        """ファイルダイアログを開き、アプリケーションを選択し、プロセスパスを生成する"""
        global app_path, process_path
        app_path = filedialog.askopenfilename(initialdir="/Applications", title="アプリを選択")
        if app_path:  # アプリが選択された場合
            app_name = app_path.split('/')[-1].replace('.app', '')
            full_process_path = f'/Applications/{app_name}.app/Contents/MacOS/{app_name}'
            process_path = full_process_path
            process_path_entry.delete(0, tk.END)
            process_path_entry.insert(0, full_process_path)
    
    select_app_button= tk.Button(settings_window, text="アプリを選択", command=select_and_process_app)
    select_app_button.pack()

    def save_and_close():
        settings['line_token'] = line_token_entry.get()
        settings['process_path'] = process_path_entry.get()
        save_settings(settings)
        settings_window.destroy()

    tk.Button(settings_window, text="保存して閉じる", command=save_and_close).pack()

# GUIから呼び出される関数
def select_app():
    """ファイルダイアログを開き、アプリケーションを選択する"""
    global app_path
    app_path = filedialog.askopenfilename()
    app_selection.delete(0, tk.END)
    app_selection.insert(0, app_path)

def start_monitoring():
    """監視を開始する"""
    global interval, process_path, app_path
    try:
        interval = int(interval_entry.get())
    except ValueError:
        messagebox.showerror("エラー", "間隔は整数でなければなりません。")
        return
    interval = max(1, interval) * 60  # 分単位から秒単位に変換

    # テキスト欄からprocess_pathに格納
    # app_name = app_name_entry.get()
    # process_path = f'/Applications/{app_name}.app/Contents/MacOS/{app_name}'
    # app_path = app_selection.get()

    # 監視スレッドの開始
    monitoring_thread = threading.Thread(target=monitor_process, daemon=True)
    monitoring_thread.start()

def monitor_process():
    """プロセスを監視し、必要に応じて再起動する"""
    global process_path
    app_name = os.path.basename(process_path)
    while True:
        if not check_process(process_path):
            log_textbox.insert(tk.END, f'{app_name} が実行中ではありません。再起動します。\n')
            restart_process(app_path)
            send_line_notify(f'{app_name} を再起動しました。')
        else:
            log_textbox.insert(tk.END, f'{app_name} が実行中です。\n')
        time.sleep(interval)  # 指定された間隔で待機

# 以下は元の関数定義
def send_line_notify(message):
    token = settings.get('line_token', '')
    if not token:
        messagebox.showerror("エラー", "LINE Notifyのトークンが設定されていません。")
        return
    headers = {'Authorization': f'Bearer {token}'}
    data = {'message': message}
    response = requests.post('https://notify-api.line.me/api/notify', headers=headers, data=data)
    print(f"Status Code: {response.status_code}, Response: {response.text}")
    log_textbox.insert(f"Status Code: {response.status_code}, Response: {response.text} \n")
    return response.status_code

def check_process(path):
    """プロセスが実行中かどうかをチェックする"""
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if proc.info['exe'] == path:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def restart_process(app_path):
    """プロセスを再起動する"""
    subprocess.Popen(['open', app_path])

# GUIの構築と起動
root = tk.Tk()
root.title("ProcessGuardian")

settings = load_settings()

process_path = settings.get('process_path', '')

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

# 設定ボタンをメインウィンドウに追加
tk.Button(frame, text="設定", command=open_settings_window).grid(column=0, row=0, sticky=tk.W)

ttk.Label(frame, text="監視したいアプリケーションを選択してください。").grid(column=0, row=1, sticky=tk.W)
app_selection = ttk.Entry(frame, width=50)
app_selection.grid(column=0, row=2, sticky=(tk.W, tk.E))
ttk.Button(frame, text="アプリを選択", command=select_app).grid(column=1, row=2, sticky=tk.W, padx=5)

ttk.Label(frame, text="間隔（分）").grid(column=0, row=4, sticky=tk.W)
interval_entry = ttk.Entry(frame, width=10)
interval_entry.grid(column=0, row=6, sticky=(tk.W, tk.E))
interval_entry.insert(0, "30")  # デフォルト値として30をセット

ttk.Button(frame, text="監視を開始", command=start_monitoring).grid(column=0, row=7, sticky=tk.W, pady=5)

ttk.Label(frame, text="ログ").grid(column=0, row=8, sticky=tk.W)
log_textbox = tk.Text(frame, width=75, height=10)
log_textbox.grid(column=0, row=9, columnspan=2, pady=5)

root.mainloop()
