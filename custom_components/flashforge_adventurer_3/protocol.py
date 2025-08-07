import asyncio
from codecs import StreamReader, StreamWriter
import logging
import os
import re
from typing import Optional, Tuple, TypedDict

logger = logging.getLogger(__name__)

BUFFER_SIZE = 1024
TIMEOUT_SECONDS = 5
STATUS_COMMAND = "~M601 S1"
PRINT_JOB_INFO_COMMAND = "~M27"
TEMPERATURE_COMMAND = "~M105"

STATUS_REPLY_REGEX = re.compile(
    "CMD M27 Received.\r\n\\w+ printing byte (\\d+)/(\\d+)\r\n(.*?)ok\r\n"
)
TEMPERATURE_REPLY_REGEX = re.compile(
    "CMD M105 Received.\r\nT0:(\\d+)\\W*/(\\d+) B:(\\d+)\\W*/(\\d+)\r\n(.*?)ok\r\n"
)


class PrinterStatus(TypedDict):
    online: bool
    printing: Optional[bool]
    progress: Optional[int]
    bed_temperature: Optional[int]
    desired_bed_temperature: Optional[int]
    nozzle_temperature: Optional[int]
    desired_nozzle_temperature: Optional[int]


async def send_msg(
    reader: StreamReader, writer: StreamWriter, payload: str
) -> Optional[str]:
    """Send a payload to the printer and wait for a response.

    Returns ``None`` if the printer does not respond within ``TIMEOUT_SECONDS``
    or the coroutine is cancelled.
    """

    msg = f"{payload}\r\n"
    writer.write(msg.encode())
    logger.debug('Sent "%s" to the printer', payload)
    await writer.drain()
    try:
        result = await asyncio.wait_for(
            reader.read(BUFFER_SIZE), timeout=TIMEOUT_SECONDS
        )
    except (asyncio.TimeoutError, asyncio.CancelledError):
        logger.warning("Timeout waiting for response to %s", payload)
        return None
    logger.debug("Response from the printer: %s", result)
    return result.decode()


async def collect_data(
    ip: str, port: int
) -> Tuple[PrinterStatus, Optional[str], Optional[str]]:
    future = asyncio.open_connection(ip, port)
    try:
        reader, writer = await asyncio.wait_for(future, timeout=TIMEOUT_SECONDS)
    except (asyncio.TimeoutError, OSError):
        return {"online": False}, None, None

    try:
        response: PrinterStatus = {"online": True}
        status_reply = await send_msg(reader, writer, STATUS_COMMAND)
        if status_reply is None:
            return {"online": False}, None, None

        print_job_info = await send_msg(reader, writer, PRINT_JOB_INFO_COMMAND)
        if print_job_info is None:
            return {"online": False}, None, None

        temperature_info = await send_msg(reader, writer, TEMPERATURE_COMMAND)
        if temperature_info is None:
            return {"online": False}, None, None

        return response, print_job_info, temperature_info
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # pragma: no cover - close failures are non-fatal
            pass


def parse_data(
    response: PrinterStatus, print_job_info: str, temperature_info: str
) -> PrinterStatus:
    print_job_info_match = STATUS_REPLY_REGEX.match(print_job_info)
    if print_job_info_match:
        current = int(print_job_info_match.group(1))
        total = int(print_job_info_match.group(2))
        response["progress"] = int(current / total * 100)
    temperature_match = TEMPERATURE_REPLY_REGEX.match(temperature_info)
    if temperature_match:
        # Printer is printing if desired temperatures are greater than zero. If not, it's paused.
        desired_nozzle_temperature = int(temperature_match.group(2))
        desired_bed_temperature = int(temperature_match.group(4))
        response["printing"] = bool(
            desired_nozzle_temperature and desired_bed_temperature
        )
        response["nozzle_temperature"] = int(temperature_match.group(1))
        response["desired_nozzle_temperature"] = desired_nozzle_temperature
        response["bed_temperature"] = int(temperature_match.group(3))
        response["desired_bed_temperature"] = desired_bed_temperature
    return response


async def get_print_job_status(ip: str, port: int) -> PrinterStatus:
    response, print_job_info, temperature_info = await collect_data(ip, port)
    if not response["online"]:
        return response
    return parse_data(response, print_job_info, temperature_info)


if __name__ == "__main__":
    status = asyncio.run(get_print_job_status(os.environ["PRINTER_IP"], 8899))
    print(status)
