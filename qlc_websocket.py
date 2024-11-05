from websockets.asyncio import client as ws
async def connect_qlc():
    return await ws.connect('ws://localhost:9999/qlcplusWS')
qlcsocket = await connect_qlc()
await qlcsocket.send("CH|{ch}|{v}".format(ch=10, v=5))
await qlcsocket.send("CH|{ch}|{v}".format(ch=5, v=10))
qlcsocket.close()