import os
import re
import socket
from typing import Optional, TypedDict


BUFFER_SIZE = 1024
TIMEOUT_SECONDS = 5
STATUS_COMMAND = '~M601 S1'
PRINT_JOB_INFO_COMMAND = '~M27'
TEMPERATURE_COMMAND = '~M105'

STATUS_REPLY_REGEX = re.compile('CMD M27 Received.\r\n\w+ printing byte (\d+)/100\r\nok\r\n')
TEMPERATURE_REPLY_REGEX = re.compile('CMD M105 Received.\r\nT0:(\d+)/(\d+) B:(\d+)/(\d+)\r\nok\r\n')

class PrinterStatus(TypedDict):
    online: bool
    printing: Optional[bool]
    progress: Optional[int]
    bed_temperature: Optional[int]
    desired_bed_temperature: Optional[int]
    nozzle_temperature: Optional[int]
    desired_nozzle_temperature: Optional[int]


def open_socket(ip_address: str, port: int):
    printer_socket = socket.socket()
    printer_socket.settimeout(TIMEOUT_SECONDS)
    printer_socket.connect((ip_address, port))
    return printer_socket


def send_msg(socket, payload):
    msg = f'{payload}\r\n'
    socket.send(msg.encode())
    result = socket.recv(BUFFER_SIZE)
    return result.decode()


def get_print_job_status(ip: str, port: int) -> PrinterStatus:
    try:
        printer_socket = open_socket(ip, port)
    except (socket.timeout, OSError):
        return { 'online': False }
    response: PrinterStatus = { 'online': True }
    send_msg(printer_socket, STATUS_COMMAND)
    print_job_info = send_msg(printer_socket, PRINT_JOB_INFO_COMMAND)
    temperature_info = send_msg(printer_socket, TEMPERATURE_COMMAND)
    print_job_info_match = STATUS_REPLY_REGEX.match(print_job_info)
    if print_job_info_match:
        response['progress'] = int(print_job_info_match.group(1))
    temperature_match = TEMPERATURE_REPLY_REGEX.match(temperature_info)
    if temperature_match:
        # Printer is printing if desired temperatures are greater than zero. If not, it's paused.
        desired_nozzle_temperature = int(temperature_match.group(2))
        desired_bed_temperature = int(temperature_match.group(4))
        response['printing'] = desired_nozzle_temperature and desired_bed_temperature
        response['nozzle_temperature'] = int(temperature_match.group(1))
        response['desired_nozzle_temperature'] = desired_nozzle_temperature
        response['bed_temperature'] = int(temperature_match.group(3))
        response['desired_bed_temperature'] = desired_bed_temperature
    return response


if __name__ == '__main__':
    status = get_print_job_status(os.environ['PRINTER_IP'], 8899)
    print(status)
