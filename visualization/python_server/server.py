import asyncio
import websockets
import json

class WebSocketServer:
    def __init__(self, simulation, port=8765):
        self.simulation = simulation
        self.port = port
        self.clients = set()  # Track connected clients

    async def handler(self, websocket):
        self.clients.add(websocket)
        try:
            await asyncio.Future()  # Keep connection open
        finally:
            self.clients.remove(websocket)

        # last_sent_time = -1  # Initialize with a sentinel value
        # while True:
        #     state = self.simulation.get_current_state()
        #     current_time = state['time']
        #
        #     if current_time != last_sent_time:
        #         last_sent_time = current_time
        #         print(
        #             f"[WebSocket] Sending state at sim time {current_time} with {len(state['aircrafts'])} aircraft(s)")
        #         message = json.dumps(state)
        #         await websocket.send(message)
        #
        #     await asyncio.sleep(0.05)  # Check frequently, but only send on change

    async def send_update(self, state):
        """Send the current state to all connected clients."""
        if self.clients:  # Only send if there are connected clients
            message = json.dumps(state)
            await asyncio.gather(*(client.send(message) for client in self.clients))
            
    async def run(self):
        async with websockets.serve(self.handler, "localhost", self.port):
            await asyncio.Future()  # Run forever
            