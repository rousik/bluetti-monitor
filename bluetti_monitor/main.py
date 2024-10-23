import asyncio
import struct
from time import sleep

import crcmod.predefined
import hexdump
from bleak import BleakClient

modbus_crc = crcmod.predefined.mkCrcFun("modbus")


BLUETTI_UUID = "A8E84D1F-675E-0725-69CE-A716D62C3A91"
WRITE_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"


def read_fields_cmd(offset, n) -> bytearray:
    """Returns bt packet for reading n items (2n bytes) starting at offset."""
    packet = bytearray(8)  # 2 bytes for header, 2x2 bytes for payload, 2 bytes for crc
    struct.pack_into("!BBHH", packet, 0, 1, 3, offset, n)
    struct.pack_into("<H", packet, -2, modbus_crc(packet[:-2]))
    return packet


def bt_notify_callback(sender: int, data: bytearray):
    print(f"Got {len(data)} bytes response from the device")
    hexdump.hexdump(data)
    # TODO: Run CRC va"lidation and header checks...
    dc_in, ac_in, ac_out, dc_out = struct.unpack_from("!HHHH", data, 3)
    # note that kWh total at offset 41 doesn't seem to hold any value
    batt_pct = struct.unpack_from("!H", data, 3 + 2 * 7)  # 42 offset, starts at 36
    print(f"  DC (in: {dc_in}, out: {dc_out})")
    print(f"  AC (in: {ac_in}, out: {ac_out})")
    print(f"  Batt percent {batt_pct}")
    print("---")


async def main(address):
    stop_event = asyncio.Event()

    async with BleakClient(address) as client:
        # print(f"Services: {client.services}")
        # for i, chr in client.services.characteristics.items():
        #     print(f"* char {chr.uuid} (svc: {chr.service_uuid}): {chr.description}")
        #     for desc in chr.descriptors:
        #         print(f"  {desc.uuid}/{desc.handle}: {desc.description}")
        # Register hex-dumping listener

        await client.start_notify(
            NOTIFY_UUID,
            bt_notify_callback,
        )
        # Try reading registers
        while True:
            sleep(1)
            await client.write_gatt_char(
                WRITE_UUID, read_fields_cmd(36, 10), response=True
            )

        await stop_event.wait()
        # print(f"Got back {data}")
        # print(hexdump.hexdump(data))
        # Invoke data packet read

        # print(f"Services: {client.services}")
        # for i, chr in client.services.characteristics.items():
        #     print(f"* char {chr.uuid} (svc: {chr.service_uuid}): {chr.description}")
        #     for desc in chr.descriptors:
        #         print(f"  {desc.uuid}/{desc.handle}: {desc.description}")
        # # print(f"Characteristics: {client.services.characteristics}")
        # # print(f"Descriptors: {client.services.descriptors}")
        # for i, dsc in client.services.descriptors.items():
        #     print(f"* desc {dsc.uuid}/{dsc.handle}: {dsc.description}")
        # # model_number = await client.read_gatt_char(MODEL_NBR_UUID)
        # # print("Model Number: {0}".format("".join(map(chr, model_number))))


asyncio.run(main(BLUETTI_UUID))
