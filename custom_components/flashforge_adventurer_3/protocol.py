import asyncio
from codecs import StreamReader, StreamWriter
import logging
import re
from typing import Optional, Tuple, TypedDict

from .const import (
    PrinterModel, BUFFER_SIZE, TIMEOUT_SECONDS
)

logger = logging.getLogger(__name__)

PRINT_JOB_INFO_COMMAND = '~M27'
TEMPERATURE_COMMAND = '~M105'

TEMPERATURE_REGEX_5M = re.compile(r'T0:(\d+\.?\d*)/(\d+\.?\d*) .* B:(\d+\.?\d*)/(\d+\.?\d*)')
PROGRESS_REGEX_5M = re.compile(r'(\d+)/(\d+)\r')

TEMPERATURE_REGEX_ADVENTURER = re.compile(r'CMD M105 Received.\r\nT0:(\d+)\W*/(\d+) B:(\d+)\W*/(\d+)\r\n(.*?)ok\r\n')
PROGRESS_REGEX_ADVENTURER = re.compile(r'CMD M27 Received.\r\n\w+ printing byte (\d+)/(\d+)\r\n(.*?)ok\r\n')

class PrinterStatus(TypedDict):
    model: PrinterModel
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


async def collect_data(ip: str, port: int, model: PrinterModel) -> Tuple[PrinterStatus, Optional[str], Optional[str]]:
    future = asyncio.open_connection(ip, port)
    try:
        reader, writer = await asyncio.wait_for(future, timeout=TIMEOUT_SECONDS)
    except (asyncio.TimeoutError, OSError):
        return {'model': model, 'online': False}, None, None
    response: PrinterStatus = {'model': model, 'online': True}
    print_job_info = await send_msg(reader, writer, PRINT_JOB_INFO_COMMAND)
    temperature_info = await send_msg(reader, writer, TEMPERATURE_COMMAND)
    writer.close()
    await writer.wait_closed()
    return response, print_job_info, temperature_info


def parse_data(model: PrinterModel, print_job_info: str, temperature_info: str) -> PrinterStatus:
    response = {'model': model, 'online': True}
    logger.debug("Model: %s", model)

    if model in [PrinterModel.ADVENTURER_5M_PRO, PrinterModel.ADVENTURER_5M]:
        temperature_match  = TEMPERATURE_REGEX_5M.search(temperature_info)
        progress_match = PROGRESS_REGEX_5M.search(print_job_info)
    else:
        temperature_match  = TEMPERATURE_REGEX_ADVENTURER.search(temperature_info)
        progress_match = PROGRESS_REGEX_ADVENTURER.search(print_job_info)

    if temperature_match:
        # Printer is printing if desired temperatures are greater than zero. If not, it's paused.
        desired_nozzle_temperature = float(temperature_match.group(2)) # As int, I received this error "invalid literal for int() with base 10: '220.0'" so I casted it to float. Alternatively could try Decimal. 
        desired_bed_temperature = float(temperature_match.group(4))
        response['printing'] = bool(desired_nozzle_temperature and desired_bed_temperature)
        response['nozzle_temperature'] = float(temperature_match.group(1))
        response['desired_nozzle_temperature'] = desired_nozzle_temperature
        response['bed_temperature'] = float(temperature_match.group(3))
        response['desired_bed_temperature'] = desired_bed_temperature

    if progress_match:
        current = int(progress_match.group(1))
        total = int(progress_match.group(2))
        response['progress'] = int(current / total * 100) if total > 0 else 0

    return response


async def get_print_job_status(ip: str, port: int, model: PrinterModel) -> PrinterStatus:
    response, print_job_info, temperature_info = await collect_data(ip, port, model)
    if not response['online']:
        return response
    return parse_data(model, print_job_info, temperature_info)


if __name__ == '__main__':
    model = PrinterModel.ADVENTURER_5M_PRO
    status = asyncio.run(get_print_job_status(os.environ['PRINTER_IP'], 8899, model))
    print(status)