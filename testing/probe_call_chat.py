#!/usr/bin/env python3
"""Check rendered call/chat open, close and resize on a private X11 display.

Needs Xvfb, xdotool, ImageMagick, Pillow and bun. Uses fake Discord, without
joining voice or using the desktop's account. Headless Slint geometry alone
does not reproduce the closed column's layout constraint propagation.
"""
import argparse
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import urllib.request

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--exe', type=Path, default=ROOT / 'target/fast/yapfast')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
processes = []


def start(command, log, **kwargs):
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=True, **kwargs)
    processes.append(process)
    return process


def until(check):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(.1)
    raise RuntimeError('Private UI did not become ready; inspect the output logs')


with tempfile.TemporaryDirectory(prefix='yapfast-call-chat-') as directory:
    data = Path(directory)
    try:
        display_file = data / 'display'
        with display_file.open('wb') as display, (args.output / 'xvfb.log').open('wb') as log:
            process = subprocess.Popen(['Xvfb', '-displayfd', '1', '-screen', '0',
                                        '1600x1000x24', '-nolisten', 'tcp'],
                                       stdout=display, stderr=log, start_new_session=True)
            processes.append(process)
            number = until(lambda: display_file.read_text().strip())
        environment = dict(os.environ, DISPLAY=f':{number}', WINIT_UNIX_BACKEND='x11',
                           PULSE_SERVER=f'unix:{data}/no-pulse')
        environment.pop('WAYLAND_DISPLAY', None)
        alsa = data / 'asound.conf'
        alsa.write_text('pcm.!default { type null }\n')
        environment['ALSA_CONFIG_PATH'] = str(alsa)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        server = f'http://127.0.0.1:{port}'
        with (args.output / 'fake.log').open('wb') as log:
            start(['bun', str(ROOT / 'testing/fake_discord.ts'), '--port', str(port)], log)

        def healthy():
            try:
                with urllib.request.urlopen(server + '/_control/health', timeout=1):
                    return True
            except OSError:
                return False

        until(healthy)
        environment['YAPFAST_DISCORD_TEST_SERVER'] = server
        with (args.output / 'app.log').open('wb') as log:
            start(['dbus-run-session', '--', str(args.exe.resolve()), '--renderer', 'software',
                   '--data-dir', str(data / 'profile')], log, env=environment)

        def xdo(*command):
            return subprocess.run(['xdotool', *map(str, command)], env=environment,
                                  capture_output=True, text=True, timeout=10)

        window = until(lambda: xdo('search', '--class', 'yapfast').stdout.strip()).splitlines()[0]

        def click(x, y):
            xdo('mousemove', '--window', window, x, y).check_returncode()
            xdo('click', '1').check_returncode()
            time.sleep(.25)

        def check_call(name, width, chat_width):
            path = args.output / f'{name}.png'
            subprocess.run(['import', '-window', window, str(path)], env=environment,
                           check=True, timeout=10)
            with Image.open(path) as picture:
                picture = picture.convert('RGB')
                pixels = picture.load()
                right = round(width - chat_width)
                # The yellow Join voice button must remain in the call stage,
                # centred in the available area rather than hidden or clipped.
                points = [x for y in range(150, 800) for x in range(320, right - 8)
                          if (colour := pixels[x, y])[0] > 210
                          and 140 < colour[1] < 230 and colour[2] < 130]
            assert len(points) > 1500, f'Call area is blank or clipped: {path}'
            centre = (312 + right) / 2
            assert abs(sum(points) / len(points) - centre) < 12, f'Call did not fit its pane: {path}'

        xdo('windowsize', window, 1600, 900).check_returncode()
        time.sleep(1)
        click(36, 155)  # Fake server.
        preferred = 420
        for width in (1600, 943):
            xdo('windowsize', window, width, 900).check_returncode()
            time.sleep(.5)
            chat_width = min(preferred, min(800, max(160, width - 312 - 240)))
            for cycle in range(3):
                click(284, 258)  # The voice channel's chat bubble.
                check_call(f'{width}-open-{cycle}', width, chat_width)
                if width == 1600 and cycle == 0:
                    edge = width - chat_width
                    xdo('mousemove', '--window', window, edge, 400, 'mousedown', '1',
                        'mousemove', '--window', window, 1000, 400, 'mouseup', '1').check_returncode()
                    time.sleep(.25)
                    preferred = chat_width = 600
                    check_call('1600-resized', width, chat_width)
                click(width - 22, 68)  # The actual side-chat close button.
                check_call(f'{width}-closed-{cycle}', width, 0)
        print('Rendered call remains visible through six open/close cycles, resize and narrow windows.')
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(5)
