import json
import asyncio
import httpx
import websockets

SNIPER_GUILD_ID = "1183557950065881108"
URL_SNIPER_SELF_TOKEN = "MTA4NzA1NzQ2Mjg4MTk2MDA4Nw.GalKGY.tG5gyFwlItahzpjTpJtCIV7ysC0axaMPo7CHqw"
SNIPER_SELF_TOKEN = "MTA4NzA1NzQ2Mjg4MTk2MDA4Nw.GalKGY.tG5gyFwlItahzpjTpJtCIV7ysC0axaMPo7CHqw"
SUCCESS_WEBHOOK_URL = "https://discord.com/api/webhooks/1185527582834315295/39YSEPE7oW3lfTqMeclD_cl6XZdQRoWoiYb4MXPth_cvewE9Q9CqmzM3rPKpeZS_gcYs"
ERROR_WEBHOOK_URL = "https://discord.com/api/webhooks/1185288163527245885/hUfNJArcgdlHwzyv9aAHTeDjkgSujkX6Or_wm7rCU7mtyZTOxe6q2VlnoaLyvUxbs0pr"

class Sniper:
    def __init__(self):
        self.opcodes = {
            "DISPATCH": 0,
            "HEARTBEAT": 1,
            "IDENTIFY": 2,
            "RECONNECT": 7,
            "HELLO": 10,
            "HEARTBEAT_ACK": 11,
        }
        self.interval = None
        self.guilds = {}

    def create_payload(self, data):
        return json.dumps(data)

    async def heartbeat(self, socket):
        payload = self.create_payload({
            "op": 1,
            "d": {},
            "s": None,
            "t": "heartbeat",
        })
        await socket.send(payload)

    async def on_message(self, message):
        data = json.loads(message)
        if data["op"] == self.opcodes["DISPATCH"]:
            if data["t"] == "GUILD_UPDATE":
                guild_id = data["d"]["guild_id"]
                vanity_url_code = "return"
                if isinstance(self.guilds.get(guild_id), dict) and self.guilds[guild_id]["vanity_url_code"] != vanity_url_code:
                    url = f"https://discord.com/api/v10/guilds/{SNIPER_GUILD_ID}/vanity-url"
                    headers = {
                        "Authorization": URL_SNIPER_SELF_TOKEN,
                        "Content-Type": "application/json",
                    }
                    payload = self.create_payload({"code": self.guilds[guild_id]["vanity_url_code"]})
                    async with httpx.AsyncClient() as client:
                        response = await client.patch(url, headers=headers, content=payload)
                        response2 = await client.get(f'https://discord.com/api/v10/guilds/{SNIPER_GUILD_ID}', headers=headers)
                        van = response2.json()["vanity_url_code"]
                        if response.status_code == 200:
                            payload = {
                            "content": f"URL: https://discord.gg/{van} successfully received. ||@everyone||."
                            }
                            httpx.post(SUCCESS_WEBHOOK_URL, json=payload)
                        else:
                            error = response.json()
                            payload = {
                            "content": f"Error while sniping url: {vanity_url_code}"
                            }
                            httpx.post(ERROR_WEBHOOK_URL, json=payload)
                            payload2 = {"content": json.dumps(error, indent=4)}
                            httpx.post(ERROR_WEBHOOK_URL, json=payload2)
                    del self.guilds[guild_id]
            else:
                if data["t"] == "READY":
                    for guild in data["d"]["guilds"]:
                        if isinstance(guild.get("vanity_url_code"), str):
                            self.guilds[guild["id"]] = {"vanity_url_code": guild["vanity_url_code"]}
                            payload = {
                            "content": f"started sniping: {len(self.guilds)} guilds:" + "\n" + ", ".join([f"`{value['vanity_url_code']}`" for value in self.guilds.values()])
                            }
                            httpx.post(SUCCESS_WEBHOOK_URL, json=payload)
                elif data["t"] == "GUILD_CREATE":
                    self.guilds[data["d"]["id"]] = {"vanity_url_code": data["d"].get("vanity_url_code", None)}
                elif data["t"] == "GUILD_DELETE":
                    guild_id = data["d"]["id"]
                    find = self.guilds.get(guild_id)
                    if isinstance(find.get("vanity_url_code"), str):
                        url = f"https://discord.com/api/v10/guilds/{SNIPER_GUILD_ID}/vanity-url"
                        headers = {
                            "Authorization": URL_SNIPER_SELF_TOKEN,
                            "Content-Type": "application/json",
                        }
                        payload = self.create_payload({"code": "return"})
                        async with httpx.AsyncClient() as client:
                            response = await client.patch(url, headers=headers, content=payload)
                            response2 = await client.get(f'https://discord.com/api/v10/guilds/{SNIPER_GUILD_ID}', headers=headers)
                            van = response2.json()["vanity_url_code"]
                            if response.status_code == 200:
                                payload = {
                                "content": f"URL: https://discord.gg/{van} successfully received. ||@everyone||."
                                }
                                httpx.post(SUCCESS_WEBHOOK_URL, json=payload)
                            else:
                                error = response.json()
                                payload = {
                                "content": f"Error while sniping url: {find['vanity_url_code']}"
                                }
                                httpx.post(ERROR_WEBHOOK_URL, json=payload)
                                payload2 = {"content": json.dumps(error, indent=4)}
                                httpx.post(ERROR_WEBHOOK_URL, json=payload2)
                        del self.guilds[guild_id]

        elif data["op"] == self.opcodes["RECONNECT"]:
            return await asyncio.get_event_loop().shutdown_asyncgens()

    async def on_open(self, socket):
        print("Discord Websocket Connection Opened.")
        payload = {
            "op": self.opcodes["IDENTIFY"],
            "d": {
                "token": SNIPER_SELF_TOKEN,
                "intents": 1,
                "properties": {
                    "os": "macos",
                    "browser": "Safari",
                    "device": "MacBook Air",
                },
            },
        }
        await socket.send(self.create_payload(payload))

    async def on_close(self, socket, reason):
        print(f"Websocket connection closed by discord: {reason}")
        await asyncio.get_event_loop().shutdown_asyncgens()

    async def on_error(self, socket, error):
        print(error)
        await asyncio.get_event_loop().shutdown_asyncgens()

    async def start(self):
        try:
            async with websockets.connect("wss://gateway.discord.gg/?v=10&encoding=json") as socket:
                self.socket = socket
                await self.on_open(socket)

                while True:
                    message = await socket.recv()
                    await self.on_message(message)

        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    sniper = Sniper()
    asyncio.run(sniper.start())