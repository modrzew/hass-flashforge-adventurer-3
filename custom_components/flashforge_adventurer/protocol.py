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

STATUS_REPLY_REGEX = re.compile('CMD M27 Received.\r\n\w+ printing byte (\d+)/100\r\nLayer: (\d+)/(\d+)\r\nok\r\n')
TEMPERATURE_REPLY_REGEX = re.compile('CMD M105 Received.\r\nT0:(\d+)\W*/(\d+) B:(\d+)\W*/(\d+)\r\nok\r\n')

class PrinterStatus(TypedDict):
    online: bool
    printing: Optional[bool]
    progress: Optional[int]
    bed_temperature: Optional[int]
    desired_bed_temperature: Optional[int]
    nozzle_temperature: Optional[int]
    desired_nozzle_temperature: Optional[int]


async def send_msg(reader: StreamReader, writer: StreamWriter, payload: str):
    msg = f'{payload}\r\n'
    writer.write(msg.encode())
    logger.debug(f'Sent "{payload}" to the printer')
    await writer.drain()
    result = await reader.read(BUFFER_SIZE)
    logger.debug(f'Response from the printer: {result}')
    return result.decode()


async def collect_data(ip: str, port: int) -> Tuple[PrinterStatus, Optional[str], Optional[str]]:
    future = asyncio.open_connection(ip, port)
    try:
        reader, writer = await asyncio.wait_for(future, timeout=TIMEOUT_SECONDS)
    except (asyncio.TimeoutError, OSError):
        return { 'online': False }, None, None
    response: PrinterStatus = { 'online': True }
    await send_msg(reader, writer, STATUS_COMMAND)
    print_job_info = await send_msg(reader, writer, PRINT_JOB_INFO_COMMAND)
    temperature_info = await send_msg(reader, writer, TEMPERATURE_COMMAND)
    writer.close()
    await writer.wait_closed()
    return response, print_job_info, temperature_info


def parse_data(response: PrinterStatus, print_job_info: str, temperature_info: str) -> PrinterStatus:
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
    return response


async def get_print_job_status(ip: str, port: int) -> PrinterStatus:
    response, print_job_info, temperature_info = await collect_data(ip, port)
    if not response['online']:
        return response
    return parse_data(response, print_job_info, temperature_info)


if __name__ == '__main__':
    status = asyncio.run(get_print_job_status(os.environ['PRINTER_IP'], 8899))
    print(status)
