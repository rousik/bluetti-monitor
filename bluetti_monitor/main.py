import asyncio
import struct
from time import sleep

import crcmod.predefined
from bleak import BleakClient
from prometheus_client import Gauge, start_http_server

modbus_crc = crcmod.predefined.mkCrcFun("modbus")

PROMETHEUS_PORT = 8000
POLL_PERIOD = 1  # Seconds
BLUETTI_UUID = "A8E84D1F-675E-0725-69CE-A716D62C3A91"
WRITE_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"

DC_IN = Gauge("dc_in", "DC power input (Watts)")
DC_OUT = Gauge("dc_out", "DC power output (Watts)")
AC_IN = Gauge("ac_in", "AC power input (Watts)")
AC_OUT = Gauge("ac_out", "AC power output (Watts)")
BATTERY_PERCENT = Gauge("battery_percent", "Battery charge level (Percent)")


def read_fields_cmd(offset, n) -> bytearray:
    """Returns bt packet for reading n items (2n bytes) starting at offset."""
    packet = bytearray(8)  # 2 bytes for header, 2x2 bytes for payload, 2 bytes for crc
    struct.pack_into("!BBHH", packet, 0, 1, 3, offset, n)
    struct.pack_into("<H", packet, -2, modbus_crc(packet[:-2]))
    return packet


def bt_notify_callback(sender: int, data: bytearray):
    print(f"Got {len(data)} bytes response from the device")
    # hexdump.hexdump(data)
    # print("----")
    # TODO: Run CRC validation and header checks...

    # 36, 37, 38, 39, 40 (null), 41 (null), 42 (batt_pct)
    # note that kWh total at offset 41 doesn't seem to hold any value
    dc_in, ac_in, ac_out, dc_out, _, _, batt_pct = struct.unpack_from(
        "!HHHHHHH", data, 3
    )
    DC_IN.set(dc_in)
    DC_OUT.set(dc_out)
    AC_IN.set(ac_in)
    AC_OUT.set(ac_out)
    BATTERY_PERCENT.set(batt_pct)

    # TODO(rousik): publish values to prometheus & mqtt
    # print(f"  DC (in: {dc_in}, out: {dc_out})")
    # print(f"  AC (in: {ac_in}, out: {ac_out})")
    # print(f"  Batt percent {batt_pct}")
    # print("---")


async def async_run(address):
    start_http_server(PROMETHEUS_PORT)
    stop_event = asyncio.Event()

    async with BleakClient(address) as client:
        print(f"Connected to bluetti battery at {address}")
        await client.start_notify(
            NOTIFY_UUID,
            bt_notify_callback,
        )
        # Try reading registers
        while True:
            sleep(POLL_PERIOD)
            await client.write_gatt_char(
                WRITE_UUID, read_fields_cmd(36, 10), response=True
            )

        await stop_event.wait()


def main():
    asyncio.run(async_run(BLUETTI_UUID))


if __name__ == "__main__":
    main()