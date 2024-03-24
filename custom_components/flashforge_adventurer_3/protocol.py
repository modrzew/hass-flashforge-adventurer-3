import asyncio
from codecs import StreamReader, StreamWriter
import logging
import re
from typing import Optional, Tuple, TypedDict

logger = logging.getLogger(__name__)

BUFFER_SIZE = 1024
TIMEOUT_SECONDS = 5
STATUS_COMMAND = '~M119\r\n'
PRINT_JOB_INFO_COMMAND = '~M27\r\n'
TEMPERATURE_COMMAND = '~M105\r\n'

# Regular expressions for temperature and progress

TEMPERATURE_REGEX_5M_PRO = re.compile(r'T0:(\d+\.?\d*)/(\d+\.?\d*) .* B:(\d+\.?\d*)/(\d+\.?\d*)')
PROGRESS_REGEX_5M_PRO = re.compile(r'(\d+)/(\d+)\r')

TEMPERATURE_REGEX_ADVENTURER_4 = re.compile(r'CMD M105 Received.\r\nT0:(\d+)\W*/(\d+) B:(\d+)\W*/(\d+)\r\n(.*?)ok\r\n')
PROGRESS_REGEX_ADVENTURER_4 = re.compile(r'CMD M27 Received.\r\nSD printing byte (\d+)/100\r\n.*? (\d+)/(\d+)\r\nok')

TEMPERATURE_REGEX_ADVENTURER_3 = re.compile(r'CMD M105 Received.\r\nT0:(\d+)\W*/(\d+) B:(\d+)\W*/(\d+)\r\n(.*?)ok\r\n')
PROGRESS_REGEX_ADVENTURER_3 = re.compile(r'CMD M27 Received.\r\n\w+ printing byte (\d+)/(\d+)\r\n(.*?)ok\r\n')


class PrinterStatus(TypedDict):
    model: str
    online: bool
    printing: Optional[bool]
    progress: Optional[int]
    bed_temperature: Optional[float]
    desired_bed_temperature: Optional[float]
    nozzle_temperature: Optional[float]
    desired_nozzle_temperature: Optional[float]

async def send_msg(reader: StreamReader, writer: StreamWriter, payload: str):
    msg = f'{payload}\r\n'
    writer.write(msg.encode())
    logger.debug(f'Sent "{payload}" to the printer')
    await writer.drain()
    result = await reader.read(BUFFER_SIZE)
    logger.debug(f'Response from the printer: {result}')
    return result.decode()

async def collect_data(ip: str, port: int, model: str) -> Tuple[PrinterStatus, Optional[str], Optional[str]]:
    future = asyncio.open_connection(ip, port)
    try:
        reader, writer = await asyncio.wait_for(future, timeout=TIMEOUT_SECONDS)
    except (asyncio.TimeoutError, OSError):
        return {'online': False}, None, None
    response: PrinterStatus = {'online': True}
    print_job_info = await send_msg(reader, writer, PRINT_JOB_INFO_COMMAND)
    temperature_info = await send_msg(reader, writer, TEMPERATURE_COMMAND)
    writer.close()
    await writer.wait_closed()
    return response, print_job_info, temperature_info

def parse_data(model: str, print_job_info: str, temperature_info: str) -> PrinterStatus:
    response = {'model': model, 'online': True}
    logger.debug("Model: %s", model)

    if model in ['FlashForge Adventurer 5M Pro', 'FlashForge Adventurer 5M']:
        temp_match = TEMPERATURE_REGEX_5M_PRO.search(temperature_info)
        progress_match = PROGRESS_REGEX_5M_PRO.search(print_job_info)
    elif model == 'FlashForge Adventurer 4':
        temp_match = TEMPERATURE_REGEX_ADVENTURER_4.search(temperature_info)
        progress_match = PROGRESS_REGEX_ADVENTURER_4.search(print_job_info)
    else:  # Adventurer 3
        temp_match = TEMPERATURE_REGEX_ADVENTURER_3.search(temperature_info)
        progress_match = PROGRESS_REGEX_ADVENTURER_3.search(print_job_info)

    if temp_match:
        response['nozzle_temperature'] = float(temp_match.group(1))
        response['desired_nozzle_temperature'] = float(temp_match.group(2))
        response['bed_temperature'] = float(temp_match.group(3))
        response['desired_bed_temperature'] = float(temp_match.group(4))

    if progress_match:
        current = int(progress_match.group(1))
        total = int(progress_match.group(2))
        response['progress'] = int(current / total * 100) if total > 0 else 0

    return response


async def get_print_job_status(ip: str, port: int, model: str) -> PrinterStatus:
    response, print_job_info, temperature_info = await collect_data(ip, port, model)
    if response['online']:
        return parse_data(model, print_job_info, temperature_info)
    return response

if __name__ == '__main__':
    model = 'FlashForge Adventurer 5M Pro'  # Or 'FlashForge Adventurer 5M', 'FlashForge Adventurer 4', 'FlashForge Adventurer 3'
    status = asyncio.run(get_print_job_status(os.environ['PRINTER_IP'], 8899, model))
    print(status)