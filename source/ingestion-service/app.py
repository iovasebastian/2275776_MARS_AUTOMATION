from fastapi import FastAPI
import json
import asyncio
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()


WS_URLs = []

topic_list = ["mars/telemetry/solar_array", 
              "mars/telemetry/radiation",
              "mars/telemetry/life_support",
              "mars/telemetry/thermal_loop",
              "mars/telemetry/power_bus",
              "mars/telemetry/power_consumption",
              "mars/telemetry/airlock"
            ]
for topic in topic_list:
    WS_URLs.append(f"ws://localhost:8080/api/telemetry/ws?topic={topic}")

class Event(BaseModel): #every topic has topic and event_time
    name : str
    topic : str
    event_time: datetime

class PowerEvent(Event): #solar_array, power_bus, power_consumption
    subsystem : str
    power_kw : float
    voltage_v : float
    current_a : float
    cumulative_kwh : float

class MeasurementEvent(Event): #radiation, life_support
    source : dict[str,str]
    measurements: list
    status: str

class ThermalLoopEvent(Event): #thermal_loop
    loop: str
    temperature_c : float
    flow_l_min : float
    status : str

class AirlockEvent(Event): #airlock
    airlock_id : str
    cycles_per_hour : float
    last_state : str

EVENT_CLASS_MAP = {
    topic_list[0]: PowerEvent,
    topic_list[4]: PowerEvent,
    topic_list[5]: PowerEvent,

    topic_list[1]: MeasurementEvent,
    topic_list[2]: MeasurementEvent,

    topic_list[3]: ThermalLoopEvent,

    topic_list[6]: AirlockEvent,
}


async def websocket_listener(WS_URL : str):
    while True:
        try:
            async with websockets.connect(WS_URL) as websocket:
                print(f"Connected to WS, {WS_URL}")
                while True:
                    raw_message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    data = json.loads(raw_message)
                    topic = data["topic"]
                    event_class = EVENT_CLASS_MAP.get(topic)
                    event_object = event_class(name = topic.split('/')[-1], **data)
                    print(event_object.model_dump_json(indent=4))
        except asyncio.TimeoutError:
            print("No message received in 10 seconds")
        except ConnectionClosedOK:
            print(f"[{topic}] WebSocket closed normally")
            await asyncio.sleep(1)
        except Exception as e:
            print("Websocket error", e)
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    for WS_URL in WS_URLs:
        asyncio.create_task(websocket_listener(WS_URL))

@app.get("/")
async def root():
    return {"status": "Websocket listener working"}