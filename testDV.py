# test_dv.py
# Chạy: python3 test_dv.py
import sys, json
sys.path.insert(0, '.')

from DVrouter import DVrouter
from packet import Packet

# ═══════════════════════════════════════════════════
# Mạng test:   A --2-- B --1-- D
#              |               |
#              5               3
#              |               |
#              C ──────────────┘
# ═══════════════════════════════════════════════════

PASS = "✓ PASS"
FAIL = "✗ FAIL"

def check(label, actual, expected):
    ok = actual == expected
    print(f"  {PASS if ok else FAIL}: {label}")
    if not ok:
        print(f"         kỳ vọng : {expected}")
        print(f"         thực tế : {actual}")
    return ok

def section(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)

# ─────────────────────────────────────────────────
# Hàm giả lập trao đổi DV
# (trong simulator, network.py làm việc này tự động)
# ─────────────────────────────────────────────────
def send_dv(sender, receivers):
    """
    sender gửi DV của mình cho danh sách receivers.
    receivers: list of (router, in_port)
        in_port = cổng mà receiver dùng để nhận từ sender
    """
    content = json.dumps(sender.dv)
    for (router, in_port) in receivers:
        pkt = Packet(Packet.ROUTING, sender.addr, router.addr, content)
        router.handle_packet(in_port, pkt)

def converge(rounds=6):
    """
    Chạy nhiều vòng trao đổi DV cho đến khi hội tụ.
    DV cần nhiều vòng vì thông tin lan dần từng hop.
    """
    for _ in range(rounds):
        send_dv(A, [(B, 1), (C, 1)])   # A gửi cho B (B nhận ở port 1) và C (C nhận ở port 1)
        send_dv(B, [(A, 1), (D, 1)])   # B gửi cho A và D
        send_dv(C, [(A, 2), (D, 2)])   # C gửi cho A và D
        send_dv(D, [(B, 2), (C, 2)])   # D gửi cho B và C


# ═══════════════════════════════════════════════════
# BƯỚC 1: Khởi tạo
# ═══════════════════════════════════════════════════
section("BƯỚC 1: Khởi tạo router")

A = DVrouter("A", heartbeat_time=1000)
B = DVrouter("B", heartbeat_time=1000)
C = DVrouter("C", heartbeat_time=1000)
D = DVrouter("D", heartbeat_time=1000)

check("A.dv  ban đầu chỉ có chính mình", A.dv,       {"A": 0})
check("A.neighbors ban đầu rỗng",        A.neighbors, {})
check("A.next_hop ban đầu rỗng",         A.next_hop,  {})


# ═══════════════════════════════════════════════════
# BƯỚC 2: Kết nối link
# ═══════════════════════════════════════════════════
section("BƯỚC 2: Kết nối link")

# handle_new_link(port, endpoint_addr, cost)
# port là số tự đặt — mỗi router đánh port riêng
A.handle_new_link(port=1, endpoint="B", cost=2)
A.handle_new_link(port=2, endpoint="C", cost=5)

B.handle_new_link(port=1, endpoint="A", cost=2)
B.handle_new_link(port=2, endpoint="D", cost=1)

C.handle_new_link(port=1, endpoint="A", cost=5)
C.handle_new_link(port=2, endpoint="D", cost=3)

D.handle_new_link(port=1, endpoint="B", cost=1)
D.handle_new_link(port=2, endpoint="C", cost=3)

# Sau khi add link, mỗi router chỉ biết hàng xóm trực tiếp
check("A.neighbors đúng", A.neighbors, {1: ("B", 2), 2: ("C", 5)})
check("A.dv biết B và C", A.dv,        {"A": 0, "B": 2, "C": 5})
check("A.next_hop B→port1", A.next_hop.get("B"), 1)
check("A.next_hop C→port2", A.next_hop.get("C"), 2)
check("A chưa biết D",      "D" in A.dv,         False)


# ═══════════════════════════════════════════════════
# BƯỚC 3: Trao đổi DV — vòng 1
# ═══════════════════════════════════════════════════
section("BƯỚC 3: Vòng trao đổi DV đầu tiên")

# Chỉ 1 vòng — thông tin mới lan được 1 hop
send_dv(A, [(B, 1), (C, 1)])
send_dv(B, [(A, 1), (D, 1)])
send_dv(C, [(A, 2), (D, 2)])
send_dv(D, [(B, 2), (C, 2)])

# Sau 1 vòng, A biết D qua B (cost=2+1=3)
check("A biết D sau vòng 1", "D" in A.dv, True)
print(f"  [info] A.dv = {A.dv}")


# ═══════════════════════════════════════════════════
# BƯỚC 4: Hội tụ hoàn toàn
# ═══════════════════════════════════════════════════
section("BƯỚC 4: Hội tụ hoàn toàn (6 vòng)")

converge(rounds=6)

print(f"  [info] A.dv       = {A.dv}")
print(f"  [info] A.next_hop = {A.next_hop}")

# A→D: qua B cost=2+1=3, qua C cost=5+3=8 → chọn qua B (port 1)
check("A→B  cost=2,  port=1", (A.dv.get("B"), A.next_hop.get("B")), (2, 1))
check("A→C  cost=5,  port=2", (A.dv.get("C"), A.next_hop.get("C")), (5, 2))
check("A→D  cost=3,  port=1", (A.dv.get("D"), A.next_hop.get("D")), (3, 1))

print(f"\n  [info] D.dv       = {D.dv}")
print(f"  [info] D.next_hop = {D.next_hop}")

check("D→B  cost=1,  port=1", (D.dv.get("B"), D.next_hop.get("B")), (1, 1))
check("D→C  cost=3,  port=2", (D.dv.get("C"), D.next_hop.get("C")), (3, 2))
check("D→A  cost=3,  port=1", (D.dv.get("A"), D.next_hop.get("A")), (3, 1))


# ═══════════════════════════════════════════════════
# BƯỚC 5: Forward data packet
# ═══════════════════════════════════════════════════
section("BƯỚC 5: Forward traceroute packet")

# Tạo packet từ A đến D
pkt = Packet(Packet.TRACEROUTE, src_addr="A", dst_addr="D")

# A nhận packet này ở port 0 (từ client), phải forward ra port 1 (về phía B)
forwarded_port = None
original_send  = A.send

def mock_send(port, packet):
    global forwarded_port
    forwarded_port = port

A.send = mock_send
A.handle_packet(port=0, packet=pkt)
A.send = original_send

check("A forward gói A→D ra port 1 (về B)", forwarded_port, 1)


# ═══════════════════════════════════════════════════
# BƯỚC 6: handle_time
# ═══════════════════════════════════════════════════
section("BƯỚC 6: handle_time — heartbeat")

A.last_time = 0
A.handle_time(999)
check("Chưa đủ 1000ms → last_time không đổi", A.last_time, 0)

A.handle_time(1000)
check("Đủ 1000ms → last_time cập nhật", A.last_time, 1000)

A.handle_time(1500)
check("Chưa đủ 1000ms tiếp → last_time không đổi", A.last_time, 1000)

A.handle_time(2000)
check("Đủ 1000ms tiếp → last_time cập nhật", A.last_time, 2000)


# ═══════════════════════════════════════════════════
# BƯỚC 7: Link failure
# ═══════════════════════════════════════════════════
section("BƯỚC 7: Link failure — A mất link đến B")

A.handle_remove_link(port=1)   # link A-B đứt

check("A.neighbors không còn port 1", 1 in A.neighbors, False)
check("A.neighbor_dvs không còn B",   "B" in A.neighbor_dvs, False)

# Sau khi mất B, A đến D phải đi qua C (port 2): cost = 5+3 = 8
# Cần vài vòng trao đổi để hội tụ lại
for _ in range(8):
    send_dv(A, [(C, 1)])           # A chỉ còn hàng xóm C
    send_dv(C, [(A, 2), (D, 2)])
    send_dv(D, [(B, 2), (C, 2)])
    send_dv(B, [(D, 1)])           # B không còn link A

print(f"  [info] A.dv sau failure       = {A.dv}")
print(f"  [info] A.next_hop sau failure = {A.next_hop}")

check("A→D sau failure: cost=8, port=2 (qua C)",
      (A.dv.get("D"), A.next_hop.get("D")), (8, 2))
check("A→B sau failure: không còn trong dv",
      "B" in A.dv, False)


# ═══════════════════════════════════════════════════
# Tổng kết
# ═══════════════════════════════════════════════════
print("\n" + "="*50)
print("  Chạy xong toàn bộ test")
print("="*50)