# The MIT License (MIT)
#
# Copyright (c) 2021 ETH Zurich
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import exputil
import networkx
import os


def read_directed_topology(filename_directed_topology):
    """
    Read the topology

    directed-topology.txt format:

    <number of nodes>,<number of directed edges>
    <edge A node id 1>,<edge A node id 2>,<edge A capacity>
    <edge B node id 1>,<edge B node id 2>,<edge B capacity>
    ...

    Restrictions:
    - No self-loops
    - No duplicate directed edges

    :param filename_directed_topology: Filename of the topology

    :return: NetworkX directional Graph (DiGraph)
    """

    with open(filename_directed_topology, "r") as f_topology:
        dir_graph = networkx.DiGraph()
        num_nodes = -1
        num_edges = -1
        directed_edges = list()
        first = True
        for line in f_topology:
            spl = line.split(",")

            # <number of nodes>,<number of directed edges>
            if first:
                if len(spl) != 2:
                    raise ValueError("Invalid first line (incorrect 2-split): " + line)
                num_nodes = exputil.parse_positive_int(spl[0])
                num_edges = exputil.parse_positive_int(spl[1])
                first = False

            # <edge A node id 1>,<edge A node id 2>,<edge A capacity>
            else:
                if len(spl) != 3:
                    raise ValueError("Invalid directed edge line (incorrect 3-split): " + line)
                directed_edge_pair = (
                    exputil.parse_positive_int(spl[0]),
                    exputil.parse_positive_int(spl[1]),
                    exputil.parse_positive_float(spl[2])
                )
                if directed_edge_pair[0] >= num_nodes:
                    raise ValueError("Invalid node id in edge: " + str(directed_edge_pair[0]))

                if directed_edge_pair[1] >= num_nodes:
                    raise ValueError("Invalid node id in edge: " + str(directed_edge_pair[1]))

                if directed_edge_pair[0] == directed_edge_pair[1]:
                    raise ValueError("Self loops are not allowed: " + str(directed_edge_pair[0]))

                for existing in directed_edges:
                    if existing[0] == directed_edge_pair[0] and existing[1] == directed_edge_pair[1]:
                        raise ValueError("Duplicate directed edges are not allowed: " + str(directed_edge_pair))

                # Finally add
                directed_edges.append(directed_edge_pair)

        # Empty file
        if first:
            raise ValueError("Directed topology file was empty: %s" % filename_directed_topology)

        # Amount of declared edges must match up
        if num_edges != len(directed_edges):
            raise ValueError(
                "Number of directed edges declared at start (%d) does not equal amount defined (%d)" %
                (
                    num_edges,
                    len(directed_edges)
                )
            )

        # Now we create the graph
        for node_id in range(0, num_nodes):
            dir_graph.add_node(node_id)
        for directed_edge in directed_edges:
            dir_graph.add_edge(
                directed_edge[0],
                directed_edge[1],
                capacity=directed_edge[2]
            )

        return dir_graph

    raise ValueError("Directed topology file could not be opened: %s" % filename_directed_topology)


def read_flow_paths(dir_graph, flow_paths_filename):
    """
    Read all flow paths and return list of them.

    flow-paths.txt format:

    <node-id-0>-<node-id-1>-...-<node-id-n>

    Restrictions:
    - Must be a valid path in the directed graph
    - Duplicates are allowed
    ...

    :param dir_graph: Directed graph (in)
    :param flow_paths_filename: Flow paths filename (in)

    :return: List of all paths, i.e. [ (0, 3, 4, 9), (0, 8, 9), ... ]
    """
    flow_paths_list = []
    with open(flow_paths_filename, "r") as path_file:
        for line in path_file:
            path = tuple(list(map(int, line.split("-"))))
            for i in range(len(path) - 1):
                if not dir_graph.has_edge(path[i], path[i + 1]):
                    raise ValueError(
                        "Invalid path %s : edge %d -> %d does not exist" % (str(path), path[i], path[i + 1])
                    )
            flow_paths_list.append(path)
    return flow_paths_list


def calculate_tightness(link_remainder_capacity, link_num_present_flows, link_num_fixed_flows):
    """
    Calculate the tightness of a link.

    :param link_remainder_capacity:     Remainder capacity of the link
    :param link_num_present_flows:      Number of total present flows
    :param link_num_fixed_flows:        Number of fixed flows (amount of present flows fixed)

    :return: Tightness
    """
    if link_num_fixed_flows == link_num_present_flows:
        raise ValueError("Cannot calculate tightness on a link with all its flows fixed")
    else:
        val = link_remainder_capacity / float(link_num_present_flows - link_num_fixed_flows)
        if val <= 0:
            # In rare occasions if the capacity approaches a very tiny number and there is a division,
            # it could potentially result in a negative or zero tightness.
            raise ValueError("Non-positive tightness was calculated")
        return val


def solve_mmfa(graph, flow_paths):
    """
    Max-min fair allocation.

    It can be sped up by using a better data structure (e.g., heap) to find the tightest link each iteration.

    :param graph:       Directed graph instance
    :param flow_paths:  Flow paths list

    :return: Mapping of flow_id to its max-min fair allocation
    """

    if len(flow_paths) == 0:
        raise ValueError("There are no flows, as such there is no max-min fair allocation to solve.")

    # For the algorithm
    link_tightness_ordered = []
    link_to_num_fixed_flows = {}
    link_to_present_flows = {}
    link_to_remainder_capacity = {}
    for link in graph.edges:

        # Find all flows present on this link
        present_flows = []
        flow_id = 0
        for path in flow_paths:
            link_is_there = False
            for i in range(len(path) - 1):
                assert(graph.has_edge(path[i], path[i + 1]))
                if path[i] == link[0] and path[i + 1] == link[1]:
                    link_is_there = True
                    break
            if link_is_there:
                present_flows.append((flow_id, path))
            flow_id += 1

        # Only if there are flows present, do we add them to the list of links to tighten
        if len(present_flows) > 0:
            link_to_num_fixed_flows[link] = 0
            link_to_present_flows[link] = present_flows
            link_to_remainder_capacity[link] = graph.get_edge_data(link[0], link[1])["capacity"]
            link_tightness_ordered.append(
                (calculate_tightness(link_to_remainder_capacity[link], len(present_flows), 0), link)
            )

    # Final result
    flow_id_to_allocation = {}

    # Each time find the link which is the current bottleneck
    flows_fixed = set()
    while len(link_tightness_ordered) != 0:

        # Retrieve the tightest link
        link_tightness_ordered = sorted(link_tightness_ordered)
        lowest_tightness = link_tightness_ordered[0][0]
        lowest_link = link_tightness_ordered[0][1]

        # Set of links that were affected by the flow being set
        affected_links = set()

        # For each flow present on the link
        for flow_id, flow_path in link_to_present_flows[lowest_link]:

            # If the present flow is already fixed, it no longer matters
            if flow_id not in flows_fixed:
                flows_fixed.add(flow_id)

                # Save the previous allocation of the link so that it can be removed later from the mapping
                for i in range(len(flow_path) - 1):
                    link = (flow_path[i], flow_path[i + 1])
                    affected_links.add(link)
                    link_to_num_fixed_flows[link] += 1
                    link_to_remainder_capacity[link] -= lowest_tightness

                # Finalize the flow allocation
                flow_id_to_allocation[flow_id] = lowest_tightness

        # Remap each affected link
        for link in affected_links:

            # Remove the old (tightness, link) from the tightness mapping
            for i in range(len(link_tightness_ordered)):
                if link_tightness_ordered[i][1] == link:
                    link_tightness_ordered.remove(link_tightness_ordered[i])
                    break

            # Calculate and insert the new (tightness, link) into the tightness mapping
            # if the link is not already completely tight
            if len(link_to_present_flows[link]) != link_to_num_fixed_flows[link]:
                new_tightness = calculate_tightness(
                    link_to_remainder_capacity[link],
                    len(link_to_present_flows[link]),
                    link_to_num_fixed_flows[link]
                )
                link_tightness_ordered.append((new_tightness, link))

    # Final assertions
    assert(len(flows_fixed) == len(flow_paths))

    return flow_id_to_allocation


def main_solve_mmfa(input_dir, output_dir):

    # Create output directory if not already exists
    os.makedirs(output_dir, exist_ok=True)

    # Finished: no
    with open(output_dir + "/finished.txt", "w+") as f_finished:
        f_finished.write("No")

    # Input
    dir_graph = read_directed_topology(input_dir + "/directed-topology.txt")
    flow_paths_list = read_flow_paths(dir_graph, input_dir + "/flow-paths.txt")

    # Solve
    flow_id_to_allocation = solve_mmfa(dir_graph, flow_paths_list)

    # Output
    with open(output_dir + "/flow-allocation.txt", "w+") as f_flow_allocation:
        keys = flow_id_to_allocation.keys()
        keys = sorted(keys)
        for flow_id in keys:
            f_flow_allocation.write("%d,%s,%.6f\n" % (
                flow_id, "-".join(map(lambda x: str(x), flow_paths_list[flow_id])), flow_id_to_allocation[flow_id]
            ))

    # Finished: Yes
    with open(output_dir + "/finished.txt", "w+") as f_finished:
        f_finished.write("Yes")


def main():
    args = sys.argv[1:]
    if len(args) != 2:
        print("Must supply exactly two arguments")
        print("Usage: python3 solve_mmfa.py [input_dir] [output_dir]")
        print("")
        print("     The input_dir must have two files: topology.txt and flow-paths.txt")
        print("")
        exit(1)
    else:
        main_solve_mmfa(
            args[0],
            args[1],
        )


if __name__ == "__main__":
    main()
