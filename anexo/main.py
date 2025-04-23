from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.cli import CLI


class LinuxRouter(Node):
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()


class NetworkTopo(Topo):
    def build(self, **_opts):
        r1 = self.addHost('r1', cls=LinuxRouter, ip='10.0.0.1/24', mtu=500)

        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        self.addLink(s1,
                     r1,
                     intfName2='r1-eth1',
                     params2={'ip': '10.0.0.1/24'})

        self.addLink(s2,
                     r1,
                     intfName2='r1-eth2',  # Corregido: era r2-eth1 pero el nodo es r1
                     params2={'ip': '10.1.0.1/24'})

        h1 = self.addHost(name='h1',
                          ip='10.0.0.251/24',
                          defaultRoute='via 10.0.0.1')
        h2 = self.addHost(name='h2',
                          ip='10.1.0.252/24',
                          defaultRoute='via 10.1.0.1')

        self.addLink(h1, s1)
        self.addLink(h2, s2)


def run():
    topo = NetworkTopo()
    net = Mininet(topo=topo)

    info(net['r1'].cmd("ip route add 10.1.0.0/24 via 10.1.0.1 dev r1-eth2"))  # Corregida la ruta
    
    net.start()
    
    r1 = net.get('r1')
    r1.cmd('ifconfig r1-eth1 mtu 520')
    r1.cmd('ifconfig r1-eth2 mtu 520')
    
    h1 = net.get('h1')
    h2 = net.get('h2')
    
    # Desactivar el flag DF (Do Not Fragment) en las interfaces de los hosts
    h1.cmd('echo 0 > /proc/sys/net/ipv4/ip_no_pmtu_disc')  # Permitir descubrimiento de PMTU
    h1.cmd('iptables -A OUTPUT -p icmp --icmp-type destination-unreachable -j ACCEPT')
    h1.cmd('iptables -A OUTPUT -p icmp --icmp-type fragmentation-needed -j ACCEPT')
    
    h2.cmd('echo 0 > /proc/sys/net/ipv4/ip_no_pmtu_disc')  # Permitir descubrimiento de PMTU
    h2.cmd('iptables -A OUTPUT -p icmp --icmp-type destination-unreachable -j ACCEPT')
    h2.cmd('iptables -A OUTPUT -p icmp --icmp-type fragmentation-needed -j ACCEPT')
    

    
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()

# Orden para los comandos:

# mininet> h2 iperf -s -u &
# mininet> h1 iperf -c 10.1.0.252 -u -t 5

# udp
# h2 iperf -s & 
# h2 wireshark & 
# h1 iperf -c 10.1.0.252 -t 5
# tcp


