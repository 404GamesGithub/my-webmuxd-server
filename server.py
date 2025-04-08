import asyncio
import websockets
import json
import os
from construct import Struct, Int32ul, Bytes  # For parsing .tendies (example structure)

# Hypothetical .tendies file structure (adjust based on Nugget’s real format)
TendiesFormat = Struct(
    "magic" / Bytes(4),          # e.g., b"TEND" as a file identifier
    "width" / Int32ul,           # Wallpaper width
    "height" / Int32ul,          # Wallpaper height
    "data" / Bytes(lambda this: this.width * this.height * 4)  # RGBA pixel data
)

async def handle_connection(websocket, path):
    print("Client connected")
    try:
        async for message in websocket:
            print("Received message from client")
            data = json.loads(message)
            print("Message parsed:", data.get("type"))
            if data.get("type") == "file":
                file_data = bytes(data["data"])
                print("File received, size:", len(file_data))
                with open("temp.tendies", "wb") as f:
                    f.write(file_data)
                print("File saved as temp.tendies")
                await apply_posterboard("temp.tendies", websocket)
                await websocket.send(json.dumps({"status": "Wallpaper applied"}))
                print("Sent 'Wallpaper applied' status")
            else:
                print("Unknown message type")
    except Exception as e:
        await websocket.send(json.dumps({"status": f"Error: {str(e)}"}))
        print(f"Error in handle_connection: {e}")

async def apply_posterboard(tendies_file, websocket):
    try:
        print("Processing .tendies file:", tendies_file)
        # Read and parse the .tendies file
        with open(tendies_file, "rb") as f:
            raw_data = f.read()
        
        # Parse the file (example; adjust based on real .tendies format)
        parsed = TendiesFormat.parse(raw_data)
        print(f"Parsed .tendies: magic={parsed.magic}, width={parsed.width}, height={parsed.height}, data size={len(parsed.data)}")
        
        # Step 1: Send the raw wallpaper data to the device
        # Split into chunks if too large (USB max transfer size ~64KB)
        chunk_size = 16384  # Example chunk size (16KB)
        wallpaper_data = parsed.data
        for i in range(0, len(wallpaper_data), chunk_size):
            chunk = wallpaper_data[i:i + chunk_size]
            await websocket.send(json.dumps({
                "type": "transfer",
                "endpoint": 1,  # Bulk endpoint (adjust if needed)
                "data": list(chunk)  # Convert bytes to list for JSON
            }))
            print(f"Sent data chunk: {len(chunk)} bytes")
        
        # Step 2: Send a control transfer to apply the wallpaper
        # This mimics Nugget’s likely use of a vendor-specific command
        await websocket.send(json.dumps({
            "type": "control",
            "requestType": "vendor",
            "recipient": "device",
            "request": 0x40,  # Example: Set wallpaper command
            "value": 0x01,    # Example: Enable wallpaper
            "index": 0        # Target file or mode (e.g., HomeBackground)
        }))
        print("Sent control command to apply wallpaper")
        
    except Exception as e:
        print(f"Error in apply_posterboard: {e}")
        raise Exception(f"Failed to apply posterboard: {e}")

port = int(os.getenv("PORT", 8765))
print(f"Starting server on port {port}")
start_server = websockets.serve(handle_connection, "0.0.0.0", port)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()