import asyncio
import websockets
import json
import os
from construct import Struct, Int32ul, Bytes

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
        with open(tendies_file, "rb") as f:
            raw_data = f.read()
        print(f"Raw file size: {len(raw_data)} bytes")
        print(f"First 16 bytes (hex): {raw_data[:16].hex()}")

        # Define TendiesFormat here, where raw_data is available
        TendiesFormat = Struct(
            "magic" / Bytes(4),          # e.g., b"TEND"
            "width" / Int32ul,           # Wallpaper width
            "height" / Int32ul,          # Wallpaper height
            "data" / Bytes(lambda this: len(raw_data) - 12)  # Rest of the file as data
        )

        # Parse the .tendies file
        parsed = TendiesFormat.parse(raw_data)
        print(f"Parsed .tendies: magic={parsed.magic}, width={parsed.width}, height={parsed.height}, data size={len(parsed.data)}")
        
        # Sanity check
        expected_data_size = parsed.width * parsed.height * 4
        if expected_data_size != len(parsed.data):
            print(f"Warning: Data size mismatch - expected {expected_data_size}, got {len(parsed.data)}")
        
        # Send data in chunks
        chunk_size = 16384  # 16KB chunks
        wallpaper_data = parsed.data
        for i in range(0, len(wallpaper_data), chunk_size):
            chunk = wallpaper_data[i:i + chunk_size]
            await websocket.send(json.dumps({
                "type": "transfer",
                "endpoint": 1,
                "data": list(chunk)
            }))
            print(f"Sent data chunk: {len(chunk)} bytes")
        
        # Send control command
        await websocket.send(json.dumps({
            "type": "control",
            "requestType": "vendor",
            "recipient": "device",
            "request": 0x40,
            "value": 0x01,
            "index": 0
        }))
        print("Sent control command to apply wallpaper")
        
        # Send completion signal
        await websocket.send(json.dumps({"type": "complete", "message": "Process finished"}))
        print("Sent completion signal")

    except Exception as e:
        print(f"Error in apply_posterboard: {e}")
        raise Exception(f"Failed to apply posterboard: {e}")

port = int(os.getenv("PORT", 8765))
print(f"Starting server on port {port}")
start_server = websockets.serve(handle_connection, "0.0.0.0", port)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()