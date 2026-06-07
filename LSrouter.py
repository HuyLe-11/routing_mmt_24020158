
####################################################
# LSrouter.py
# Name:
# HUID:
#####################################################

from router import Router
from packet import Packet
import json
import heapq

class LSrouter(Router):
    """Link state routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_time = 0

        self.seq = 0
        # This store current seq num to broadcast
        self.seq_num = {}
        # This store the seq_num for each source router to avoid infinity loop 
        # Eg {'A': 5} -> this means that the newest seq_num seen from source A is 5
        # If there's a packet from A has the seq_num = 5 => outdated packet, then ignore

        self.neighbors = {}
        # This store the info aout its neighbor, also the main data structure for the live time 
        # change part
        # a iter of this set should be like: port (key) -> (router_addr, cost) (value)
        # Eg: 1: ('A', 5)
        #     2: ('B', 6)

        self.lsdb = {self.addr: {}}
        # This only store the cost of every node, including itself
        # Eg   A: {'B': 2, 'C': 5}, this mean, from the source A, there's a way to B, cost = 2 and C, cost = 5


        self.next_hop = {}
        # This store the whole map to deliver a packet with lowest cost
        # To deliver a packet, a router only knows the port to go out, the left way is handled by others
        # 

        pass

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""
        # TODO
        #   update local data structures and forwarding table
        #   broadcast the new link state of this router to all neighbors

        # router = {port: (endpoint, cost)}
        self.neighbors[port] = (endpoint, cost)
        self.lsdb[self.addr][endpoint] = cost
        # 
        # print(self.lsdb)

        self.run_dijkstra()

        self.broadcast_lsp()

        pass

    def handle_remove_link(self, port):
        """Handle removed link."""
        # TODO
        #   update local data structures and forwarding table
        #   broadcast the new link state of this router to all neighbors

        if (port not in self.neighbors):
            return

        endpoint = self.neighbors[port][0]

        del self.neighbors[port]

        self.lsdb[self.addr].pop(endpoint, None)

        # self.seq_num[self.addr] = self.seq_num.get(self.addr, 0) + 1

        self.run_dijkstra()

        # self.seq_num[self.addr] += 1

        self.broadcast_lsp()


        pass

    def handle_time(self, time_ms):
        """Handle current time."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            # TODO
            #   broadcast the link state of this router to all neighbors
            
            self.broadcast_lsp()


            pass

    def broadcast_lsp(self):

        self.seq += 1

        pre_content = {}
        
        for _, (router_addr, cost) in self.neighbors.items():
            pre_content[router_addr] = cost

        # print(f"abc{pre_content}")
        
        content = {
            "seq": self.seq,
            "src": self.addr,
            "links": pre_content
        }

        # print("helo broadcast")

        content = json.dumps(content)
        # p = Packet(Packet.ROUTING, self.addr, )
        
        for port, (endpoint, _) in self.neighbors.items():
            p = Packet(Packet.ROUTING, self.addr, endpoint, content=content)
            self.send(port, p)
            # print('broadcasted')

    def flood_lsp(self, in_port, lsp):

        lsp = json.dumps(lsp)

        for port, (endpoint, _)  in self.neighbors.items():
            if (port != in_port):
                p = Packet(Packet.ROUTING, self.addr, endpoint, lsp)
                self.send(port, p)
        
    def run_dijkstra(self):

        distTo = {self.addr : 0}

        pq = [(0, self.addr, None)]
        next_hop = {}

        while pq:
            current_dist, u, port = heapq.heappop(pq)

            if current_dist > distTo.get(u, float('inf')):
                continue

            if u != self.addr and port is not None:
                next_hop[u] = port

            if u in self.lsdb:
                for node, cost in self.lsdb[u].items():

                    new_dist = distTo[u] + cost

                    if (node not in distTo or new_dist < distTo[node]):
                        distTo[node] = new_dist

                        if (u == self.addr):
                            next_port = None
                            for p, (endpoint, _) in self.neighbors.items():
                                if (endpoint == node):
                                    next_port = p
                                    break
                            if next_port is None:
                                continue
                        else:
                            next_port = port
                        
                        heapq.heappush(pq, (new_dist, node, next_port))
                        
        
        self.next_hop = next_hop


    def handle_packet(self, port, packet):
        if packet.is_traceroute:
            if (self.next_hop.get(packet.dst_addr, -1) != -1):
                self.send(self.next_hop[packet.dst_addr], packet)
        else:
            content = json.loads(packet.content)
            # print(content)
            src = content['src']
            seq = content['seq']
            links = content['links']

            # print(src)
            # print(self.seq_num.get(src, -1))

            if src == self.addr:
                return

            if (seq <= self.seq_num.get(src, -1)):
                return

            self.seq_num[src] = seq
            self.lsdb[src] = links

            self.run_dijkstra()

            self.flood_lsp(in_port=port, lsp=content)

            # dijiktra
            # flood


    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        # TODO
        #   NOTE This method is for your own convenience and will not be graded
        return f"LSrouter(addr={self.addr})"


def main():
    demo = LSrouter(0, 0)
    demo.handle_new_link(5, 6, 10)
    demo.handle_time(0.1)
    

