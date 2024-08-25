import asyncio
from codecs import StreamReader, StreamWriter
import logging
import os
import re
from typing import Optional, Tuple, TypedDict

logger = logging.getLogger(__name__)

BUFFER_SIZE = 1024
TIMEOUT_SECONDS = 5
STATUS_COMMAND = '~M601 S1'
PRINT_JOB_INFO_COMMAND = '~M27'
TEMPERATURE_COMMAND = '~M105'
PRINTER_INFO_COMMAND = '~M115'

STATUS_REPLY_REGEX = re.compile(r'CMD M27 Received.\r\n\w+ printing byte (\d+)/100\r\nLayer: (\d+)/(\d+)\r\nok\r\n')
TEMPERATURE_REPLY_REGEX = re.compile(r'CMD M105 Received.\r\nT0:(\d+)\W*/(\d+) B:(\d+)\W*/(\d+)\r\nok\r\n')
PRINTER_INFO_REGEX = re.compile(r'CMD M115 Received.\r\nMachine Type: (.*?)\r\nMachine Name: (.*?)\r\nFirmware: (.*?)\r\nSN: (.*?)\r\nX: (\d+) Y: (\d+) Z: (\d+)\r\nTool Count: (\d+)\r\nMac Address:(.*?)\n \r\nok\r\n')

class PrinterStatus(TypedDict):
    online: bool
    printing: Optional[bool]
    progress: Optional[int]
    bed_temperature: Optional[int]
    desired_bed_temperature: Optional[int]
    nozzle_temperature: Optional[int]
    desired_nozzle_temperature: Optional[int]
    type: Optional[str]
    name: Optional[str]
    fw: Optional[str]
    sn: Optional[str]
    max_x: Optional[int]
    max_y: Optional[int]
    max_z: Optional[int]
    extruder_count: Optional[str]
    mac: Optional[str]

async def send_msg(reader: StreamReader, writer: StreamWriter, payload: str):
    msg = f'{payload}\r\n'
    writer.write(msg.encode())
    logger.debug(f'Sent "{payload}" to the printer')
    await writer.drain()
    result = await reader.read(BUFFER_SIZE)
    logger.debug(f'Response from the printer: {result}')
    return result.decode()

async def collect_data(ip: str, port: int) -> Tuple[PrinterStatus, Optional[str], Optional[str], Optional[str]]:
    future = asyncio.open_connection(ip, port)
    try:
        reader, writer = await asyncio.wait_for(future, timeout=TIMEOUT_SECONDS)
    except (asyncio.TimeoutError, OSError):
        return { 'online': False }, None, None
    response: PrinterStatus = { 'online': True }
    await send_msg(reader, writer, STATUS_COMMAND)
    print_job_info = await send_msg(reader, writer, PRINT_JOB_INFO_COMMAND)
    temperature_info = await send_msg(reader, writer, TEMPERATURE_COMMAND)
    printer_info = await send_msg(reader, writer, PRINTER_INFO_COMMAND)
    writer.close()
    await writer.wait_closed()
    return response, print_job_info, temperature_info, printer_info

def parse_data(response: PrinterStatus, print_job_info: str, temperature_info: str, printer_info: str) -> PrinterStatus:
    print_job_info_match = STATUS_REPLY_REGEX.match(print_job_info)
    if print_job_info_match:
        response['progress'] = int(print_job_info_match.group(1))
        response['printing_layer'] = int(print_job_info_match.group(2))
        response['total_layers'] = int(print_job_info_match.group(3))

    temperature_match = TEMPERATURE_REPLY_REGEX.match(temperature_info)
    if temperature_match:
        # Printer is printing if desired temperatures are greater than zero. If not, it's paused.
        desired_nozzle_temperature = int(temperature_match.group(2))
        desired_bed_temperature = int(temperature_match.group(4))
        response['printing'] = bool(desired_nozzle_temperature and desired_bed_temperature)
        response['nozzle_temperature'] = int(temperature_match.group(1))
        response['desired_nozzle_temperature'] = desired_nozzle_temperature
        response['bed_temperature'] = int(temperature_match.group(3))
        response['desired_bed_temperature'] = desired_bed_temperature

    printer_info_match = PRINTER_INFO_REGEX.match(printer_info)
    if printer_info_match:
        response['type'] = str(printer_info_match.group(1))
        response['name'] = str(printer_info_match.group(2))
        response['fw'] = str(printer_info_match.group(3))
        response['sn'] = str(printer_info_match.group(4))
        response['max_x'] = int(printer_info_match.group(5))
        response['max_y'] = int(printer_info_match.group(6))
        response['max_z'] = int(printer_info_match.group(7))
        response['extruder_count'] = str(printer_info_match.group(8))
        response['mac'] = str(printer_info_match.group(9))

    return response

async def get_print_job_status(ip: str, port: int) -> PrinterStatus:
    response, print_job_info, temperature_info, printer_info = await collect_data(ip, port)
    if not response['online']:
        return response
    return parse_data(response, print_job_info, temperature_info, printer_info)

if __name__ == '__main__':
    status = asyncio.run(get_print_job_status(os.environ['PRINTER_IP'], 8899))
    print(status)
