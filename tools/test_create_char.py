#!/usr/bin/env python3
"""Минимальный UO-клиент: логин, выбор сервера, вход на игровой порт, создание персонажа.

Использование:
    python3 tools/test_create_char.py [имя [аккаунт [пароль]]]

Аккаунт должен существовать (его создаёт scripts/include/testplayers.inc
при старте сервера) либо это admin/admin.
"""
import socket, struct, time, sys

HOST, PORT = "127.0.0.1", 2593
NAME = sys.argv[1] if len(sys.argv) > 1 else "TestHero"
ACCOUNT = sys.argv[2] if len(sys.argv) > 2 else "admin"
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else ACCOUNT

def p80():
    return b"\x80" + ACCOUNT.encode().ljust(30, b"\0") + PASSWORD.encode().ljust(30, b"\0") + b"\x00"

def p91(seed):
    return struct.pack(">I", 0) + b"\x91" + b"\x00\x00" + struct.pack(">H", 0) + \
        ACCOUNT.encode().ljust(30, b"\0") + PASSWORD.encode().ljust(30, b"\0")

def pF8():
    b = bytearray(106)
    b[0] = 0xF8
    struct.pack_into(">I", b, 1, 0xEDEDEDED)
    b[5:10] = b"\xFF\xFF\xFF\xFF\x00"
    nm = NAME.encode()[:29]
    b[10:10+len(nm)] = nm
    b[54] = 0
    b[70] = 0
    b[71], b[72], b[73] = 60, 10, 10
    # Ровно 120 очков стартовых навыков, иначе POL рвёт соединение.
    b[74], b[75] = 44, 50   # Lumberjacking
    b[76], b[77] = 11, 30   # Carpentry
    b[78], b[79] = 37, 20   # Tinkering
    b[80], b[81] = 0, 20    # Alchemy (лишь бы сумма была 120)
    b[74], b[75] = 7, 50
    struct.pack_into(">H", b, 82, 0x03EA)
    struct.pack_into(">H", b, 84, 0x203C)
    struct.pack_into(">H", b, 86, 0x044E)
    b[93] = 0
    b[97] = 0
    return bytes(b)

def read_until(s, want, timeout=10):
    s.settimeout(1.0)
    buf = b""
    end = time.time() + timeout
    while time.time() < end:
        try:
            d = s.recv(8192)
        except socket.timeout:
            continue
        if not d:
            break
        buf += d
        if want in buf:
            return buf
    return buf

print("== login connection ==")
s = socket.create_connection((HOST, PORT), timeout=5)
s.sendall(b"\0\0\0\0" + p80())
data = read_until(s, b"\xA8", 5)
print("login response", data[:1].hex(), len(data))
if b"\xA8" not in data:
    print("no server list"); sys.exit(1)
s.sendall(b"\xA0\x00\x01")
data = read_until(s, b"\x8C", 5)
print("select response", data[:1].hex(), len(data), data.hex())
i = data.find(b"\x8C")
if i < 0 or len(data) < i + 11:
    print("no 0x8C relay"); sys.exit(1)
pkt = data[i:i+11]
ip = ".".join(str(x) for x in pkt[1:5])
port = struct.unpack(">H", pkt[5:7])[0]
seed = struct.unpack(">I", pkt[7:11])[0]
print("game server", ip, port, "seed", hex(seed))
s.close()

print("== game connection ==")
g = socket.create_connection((ip, port), timeout=5)
g.sendall(p91(seed))
data = read_until(g, b"\xA9", 8)
print("game response", data[:1].hex() if data else None, len(data)); print(data[:60].hex())
if b"\xA9" not in data and b"\xB3" not in data:
    print("no char list"); sys.exit(1)
g.sendall(pF8())
time.sleep(3)
try:
    g.settimeout(2)
    d = g.recv(8192)
    print("after create", d[:1].hex() if d else None, len(d))
except Exception as e:
    print("after create: no data", e)
time.sleep(5)
g.close()
print("done")
