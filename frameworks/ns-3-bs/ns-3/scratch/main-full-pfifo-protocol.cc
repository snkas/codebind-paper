/*
 * Copyright (c) 2021 ETH Zurich
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Author: Simon
 */

#include <ns3/command-line.h>
#include "ns3/basic-simulation.h"
#include "ns3/topology-ptop.h"
#include "ns3/ipv4-arbiter-routing-helper.h"
#include "ns3/arbiter-ecmp-helper.h"
#include "ns3/ptop-link-net-device-utilization-tracking.h"
#include "ns3/ptop-link-net-device-queue-tracking.h"
#include "ns3/ptop-link-interface-tc-qdisc-queue-tracking.h"
#include "ns3/tcp-config-helper.h"

#include "ns3/tcp-flow-scheduler.h"
#include "ns3/udp-burst-scheduler.h"
#include "ns3/udp-ping-scheduler.h"

#include "ns3/topology-ptop-receive-error-model-selector-default.h"
#include "ns3/topology-ptop-queue-selector-default.h"

#include "ns3/ip-tos-generator.h"

using namespace ns3;

namespace ns3 {

    uint16_t SERVER_PORT_LOW_PRIORITY = 88;
    uint16_t SERVER_PORT_HIGH_PRIORITY = 89;
    uint8_t IP_TOS_LOW_PRIORITY = 0;
    uint8_t IP_TOS_HIGH_PRIORITY = 55;

    class ClientRemotePortSelectorTwo : public ClientRemotePortSelector {
    public:
        static TypeId GetTypeId(void);
        uint16_t SelectRemotePort(TypeId appTypeId, Ptr<Application> app);
    };

    NS_OBJECT_ENSURE_REGISTERED (ClientRemotePortSelectorTwo);
    TypeId ClientRemotePortSelectorTwo::GetTypeId (void)
    {
        static TypeId tid = TypeId ("ns3::ClientRemotePortSelectorTwo")
                .SetParent<ClientRemotePortSelector> ()
                .SetGroupName("BasicSim")
        ;
        return tid;
    }

    uint16_t ClientRemotePortSelectorTwo::SelectRemotePort(TypeId appTypeId, Ptr<Application> app) {
        Ptr<TcpFlowClient> client = app->GetObject<TcpFlowClient>();
        std::string additional_parameters = client->GetAdditionalParameters();
        if (additional_parameters == "low") {
            return SERVER_PORT_LOW_PRIORITY;
        } else if (additional_parameters == "high") {
            return SERVER_PORT_HIGH_PRIORITY;
        } else {
            throw std::runtime_error("Invalid additional parameters.");
        }
    }

    class TcpSocketGeneratorCustom : public TcpSocketGenerator {
    public:
        void SetProtocolTypeId(std::string protocol);
        static TypeId GetTypeId(void);
        Ptr<Socket> GenerateTcpSocket(TypeId appTypeId, Ptr<Application> app);
    private:
       TypeId m_protocolTypeId;
    };

    NS_OBJECT_ENSURE_REGISTERED (TcpSocketGeneratorCustom);
    TypeId TcpSocketGeneratorCustom::GetTypeId (void)
    {
        static TypeId tid = TypeId ("ns3::TcpSocketGeneratorCustom")
                .SetParent<TcpSocketGenerator> ()
                .SetGroupName("BasicSim")
        ;
        return tid;
    }

    void TcpSocketGeneratorCustom::SetProtocolTypeId(std::string protocol) {
        m_protocolTypeId = TypeId::LookupByName ("ns3::" + protocol);
    }

    Ptr<Socket> TcpSocketGeneratorCustom::GenerateTcpSocket(TypeId appTypeId, Ptr<Application> app) {
        app->GetNode()->GetObject<TcpL4Protocol>()->SetAttribute("SocketType",  TypeIdValue(m_protocolTypeId));
        return Socket::CreateSocket(app->GetNode(), TcpSocketFactory::GetTypeId());
    }

    class IpTosGeneratorFromAdditionalParameters : public IpTosGenerator {
    public:
        static TypeId GetTypeId(void);
        uint8_t GenerateIpTos(TypeId appTypeId, Ptr<Application> app);
    };

    NS_OBJECT_ENSURE_REGISTERED (IpTosGeneratorFromAdditionalParameters);
    TypeId IpTosGeneratorFromAdditionalParameters::GetTypeId (void)
    {
        static TypeId tid = TypeId ("ns3::IpTosGeneratorFromAdditionalParameters")
                .SetParent<IpTosGenerator> ()
                .SetGroupName("BasicSim")
        ;
        return tid;
    }

    uint8_t IpTosGeneratorFromAdditionalParameters::GenerateIpTos(TypeId appTypeId, Ptr<Application> app) {
        if (appTypeId == TcpFlowClient::GetTypeId()) {
            Ptr<TcpFlowClient> client = app->GetObject<TcpFlowClient>();
            std::string additional_parameters = client->GetAdditionalParameters();
            if (additional_parameters == "low") {
                return IP_TOS_LOW_PRIORITY;
            } else if (additional_parameters == "high") {
                return IP_TOS_HIGH_PRIORITY;
            } else {
                throw std::runtime_error("Invalid additional parameters.");
            }
        } else {
            Ptr<TcpFlowServer> server = app->GetObject<TcpFlowServer>();
            AddressValue addressValue;
            server->GetAttribute ("LocalAddress", addressValue);
            InetSocketAddress address = InetSocketAddress::ConvertFrom(addressValue.Get());
            if (address.GetPort() == SERVER_PORT_LOW_PRIORITY) {
                return IP_TOS_LOW_PRIORITY;
            } else if (address.GetPort() == SERVER_PORT_HIGH_PRIORITY) {
                return IP_TOS_HIGH_PRIORITY;
            } else {
                throw std::runtime_error("Invalid port.");
            }
        }
    }

}

int main(int argc, char *argv[]) {

    // No buffering of printf
    setbuf(stdout, nullptr);

    // Retrieve run directory
    CommandLine cmd;
    std::string run_dir = "";
    cmd.Usage("Usage: ./waf --run=\"main-full-pfifo-protocol --run_dir='<path/to/run/directory>'\"");
    cmd.AddValue("run_dir",  "Run directory", run_dir);
    cmd.Parse(argc, argv);
    if (run_dir.compare("") == 0) {
        printf("Usage: ./waf --run=\"main-full-pfifo-protocol --run_dir='<path/to/run/directory>'\"");
        return 1;
    }

    // Load basic simulation environment
    Ptr<BasicSimulation> basicSimulation = CreateObject<BasicSimulation>(run_dir);

    // Read point-to-point topology, and install routing arbiters
    Ptr<TopologyPtop> topology = CreateObject<TopologyPtop>(basicSimulation, Ipv4ArbiterRoutingHelper());
    ArbiterEcmpHelper::InstallArbiters(basicSimulation, topology);

    // Install link net-device utilization trackers
    PtopLinkNetDeviceUtilizationTracking netDeviceUtilizationTracking = PtopLinkNetDeviceUtilizationTracking(basicSimulation, topology); // Requires enable_link_net_device_utilization_tracking=true

    // Install link net-device queue trackers
    PtopLinkNetDeviceQueueTracking netDeviceQueueTracking = PtopLinkNetDeviceQueueTracking(basicSimulation, topology); // Requires enable_link_net_device_queue_tracking=true

    // Install link interface traffic-control qdisc queue trackers
    PtopLinkInterfaceTcQdiscQueueTracking tcQdiscQueueTracking = PtopLinkInterfaceTcQdiscQueueTracking(basicSimulation, topology); // Requires enable_link_interface_tc_qdisc_queue_tracking=true

    // Configure TCP
    TcpConfigHelper::Configure(basicSimulation);

    // Schedule TCP flows
    Ptr<TcpSocketGeneratorCustom> tcpSocketGeneratorCustom = CreateObject<TcpSocketGeneratorCustom>();
    tcpSocketGeneratorCustom->SetProtocolTypeId(basicSimulation->GetConfigParamOrFail("tcp_protocol"));
    Ptr<IpTosGeneratorFromAdditionalParameters> ipTosGenerator = CreateObject<IpTosGeneratorFromAdditionalParameters>();
    TcpFlowScheduler tcpFlowScheduler(basicSimulation, topology, {SERVER_PORT_LOW_PRIORITY, SERVER_PORT_HIGH_PRIORITY}, CreateObject<ClientRemotePortSelectorTwo>(), tcpSocketGeneratorCustom, ipTosGenerator); // Requires enable_tcp_flow_scheduler=true

    // Schedule UDP bursts
    UdpBurstScheduler udpBurstScheduler(basicSimulation, topology); // Requires enable_udp_burst_scheduler=true

    // Schedule UDP pings
    UdpPingScheduler udpPingScheduler(basicSimulation, topology); // Requires enable_udp_ping_scheduler=true

    // Run simulation
    basicSimulation->Run();

    // Write TCP flow results
    tcpFlowScheduler.WriteResults();

    // Write UDP burst results
    udpBurstScheduler.WriteResults();

    // Write UDP ping results
    udpPingScheduler.WriteResults();

    // Write link net-device utilization results
    netDeviceUtilizationTracking.WriteResults();

    // Write link net-device queue results
    netDeviceQueueTracking.WriteResults();

    // Write link interface traffic-control qdisc queue results
    tcQdiscQueueTracking.WriteResults();

    // Finalize the simulation
    basicSimulation->Finalize();

    return 0;

}
