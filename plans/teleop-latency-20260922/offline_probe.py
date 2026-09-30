"""Read-only mechanism probe. Fake bus and OS pipe only; no robot device opens."""
import importlib.util
import json
import os
from pathlib import Path
import time

app_path = Path(__file__).resolve().parents[2] / 'mint_follower_demo/app.py'
spec = importlib.util.spec_from_file_location('so101_diagnostic_app', app_path)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
assert app.RUNTIME is None


class FakeSerial:
    def __init__(self, delay_ms):
        self.delay_ms = delay_ms
        self.transactions = 0

    def write(self, packet):
        self.motor_id = packet[2]
        self.transactions += 1

    def read(self, size):
        time.sleep(self.delay_ms / 1000)
        tail = [self.motor_id, 4, 0, 0, 8]
        return bytearray([255, 255] + tail + [(~sum(tail)) & 255])


for delay in (0, 5, 15):
    bus = app.NativeFeetechSTSBus({'read_timeout_ms': 150})
    bus.serial = FakeSerial(delay)
    start = time.perf_counter()
    positions = bus.read_present_positions(range(1, 7))
    elapsed = (time.perf_counter() - start) * 1000
    print(json.dumps({'synthetic_per_response_ms': delay, 'transactions': bus.serial.transactions,
                      'six_motor_read_ms': round(elapsed, 2), 'all_positions_valid': set(positions.values()) == {2048}}))

# Validate that configured 150ms timeout does not force 150ms for an already-ready read.
read_fd, write_fd = os.pipe()
try:
    serial = app.NativePosixSerial('UNOPENED_DIAGNOSTIC', 1000000, 150, 150)
    serial.fd = read_fd
    os.write(write_fd, b'12345678')
    start = time.perf_counter()
    result = serial.read(64)
    print(json.dumps({'os_pipe_ready_read_ms': round((time.perf_counter()-start)*1000, 3),
                      'bytes': len(result), 'configured_timeout_ms': 150}))
finally:
    os.close(read_fd)
    os.close(write_fd)

print('These are synthetic mechanism measurements, NOT robot latency measurements.')
