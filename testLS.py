# test_ls.py
import sys, json
sys.path.insert(0, '.')      # để import được router.py, packet.py

from LSrouter import LSrouter
from packet import Packet

# ─────────────────────────────────────────
# BƯỚC 1: Khởi tạo các router
# ─────────────────────────────────────────
# LSrouter(địa_chỉ, heartbeat_time_ms)
A = LSrouter("A", heartbeat_time=1000)
B = LSrouter("B", heartbeat_time=1000)
C = LSrouter("C", heartbeat_time=1000)
D = LSrouter("D", heartbeat_time=1000)

print("=== Khởi tạo xong ===")
print("A.lsdb:", A.lsdb)    # phải là {"A": {}}
print("A.neighbors:", A.neighbors)  # phải là {}

# ─────────────────────────────────────────
# BƯỚC 2: Kết nối link (gọi handle_new_link thủ công)
# ─────────────────────────────────────────
# handle_new_link(port, endpoint_addr, cost)
# port chỉ là số tự đặt — mỗi router đánh port riêng
A.handle_new_link(port=1, endpoint="B", cost=2)
A.handle_new_link(port=2, endpoint="C", cost=5)

B.handle_new_link(port=1, endpoint="A", cost=3)
B.handle_new_link(port=2, endpoint="D", cost=1)

C.handle_new_link(port=1, endpoint="A", cost=5)
C.handle_new_link(port=2, endpoint="D", cost=3)

D.handle_new_link(port=1, endpoint="B", cost=1)
D.handle_new_link(port=2, endpoint="C", cost=3)

print("\n=== Sau khi kết nối link ===")
print("A.neighbors:", A.neighbors)
# phải là {1: ('B', 2), 2: ('C', 5)}
print("A.lsdb[A]:", A.lsdb["A"])
# phải là {'B': 2, 'C': 5}

# ─────────────────────────────────────────
# BƯỚC 3: Giả lập trao đổi LSP
# (trong simulator, network.py lo việc này)
# ─────────────────────────────────────────

def exchange_lsp(sender, receivers):
    """Giả lập sender broadcast LSP, receivers nhận vào."""
    sender.seq += 1
    lsp = {
        "src":   sender.addr,
        "seq":   sender.seq,
        "links": {ep: c for _, (ep, c) in sender.neighbors.items()}
    }
    content = json.dumps(lsp)
    for router, in_port in receivers:
        pkt = Packet(Packet.ROUTING, sender.addr, router.addr, content)
        router.handle_packet(in_port, pkt)

# A broadcast → B (nhận ở port 1), C (nhận ở port 1)
exchange_lsp(A, [(B, 1), (C, 1)])

# B broadcast → A (port 1), D (port 1)
exchange_lsp(B, [(A, 1), (D, 1)])

# C broadcast → A (port 2), D (port 2)
exchange_lsp(C, [(A, 2), (D, 2)])

# D broadcast → B (port 2), C (port 2)
exchange_lsp(D, [(B, 2), (C, 2)])

# Vài vòng nữa để flood lan ra hết
exchange_lsp(B, [(A, 1), (D, 1)])
exchange_lsp(C, [(A, 2), (D, 2)])

# ─────────────────────────────────────────
# BƯỚC 4: Kiểm tra kết quả
# ─────────────────────────────────────────
print("\n=== Kiểm tra LSDB của A ===")
for node, links in A.lsdb.items():
    print(f"  {node}: {links}")
# Phải có đủ A, B, C, D

print("\n=== Kiểm tra forwarding table (next_hop) của A ===")
print("A.next_hop:", A.next_hop)
# Phải là: {'B': 1, 'C': 2, 'D': 1}
#           B qua port1, C qua port2, D qua port1 (vì A→B→D ngắn hơn A→C→D)

print("\n=== Kiểm tra đường đi A → D ===")
expected_port = 1   # D phải đi qua port 1 (tức là qua B, cost=2+1=3)
actual_port   = A.next_hop.get("D")
if actual_port == expected_port:
    print(f"✓ PASS: A→D đúng, thoát cổng {actual_port}")
else:
    print(f"✗ FAIL: A→D sai, cổng {actual_port}, kỳ vọng {expected_port}")

print("\n=== Kiểm tra handle_time ===")
A.last_time = 0
A.handle_time(999)   # chưa đủ 1000ms → không gửi gì
A.handle_time(1000)  # đủ 1000ms → phải gửi LSP
print("last_time sau 1000ms:", A.last_time)  # phải là 1000

print("\n=== Kiểm tra link failure ===")
# Giả lập link A-B đứt
A.handle_remove_link(port=1)
print("A.neighbors sau khi mất link B:", A.neighbors)
# phải không còn port 1
print("A.lsdb[A] sau khi mất link B:", A.lsdb["A"])
# phải không còn B
print("A.next_hop sau khi mất link B:", A.next_hop)
# D giờ phải đi qua C (port 2), cost = 5+3 = 8