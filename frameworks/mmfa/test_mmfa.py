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

import unittest
import os
from solve_mmfa import main_solve_mmfa


def get_resulting_allocation(directed_topology_content, flow_paths_content):

    # Write input
    os.makedirs("temp-input", exist_ok=True)
    with open("temp-input/directed-topology.txt", "w+") as f_out:
        f_out.write(directed_topology_content)
    with open("temp-input/flow-paths.txt", "w+") as f_out:
        f_out.write(flow_paths_content)

    # Solve
    main_solve_mmfa("temp-input", "temp-output")

    # Read result
    flow_to_allocation = {}
    with open("temp-output/flow-allocation.txt", "r") as f_in:
        for line in f_in:
            spl = line.split(",")
            flow_to_allocation[int(spl[0])] = spl[1], float(spl[2])

    # Clean up
    os.remove("temp-input/directed-topology.txt")
    os.remove("temp-input/flow-paths.txt")
    os.removedirs("temp-input")
    os.remove("temp-output/finished.txt")
    os.remove("temp-output/flow-allocation.txt")
    os.removedirs("temp-output")

    return flow_to_allocation


class TestSum(unittest.TestCase):

    def test_one_one(self):
        flow_to_allocation = get_resulting_allocation(
            (
                "2,1\n"
                "0,1,5"
            ),
            (
                "0-1"
            )
        )
        self.assertEqual(set(flow_to_allocation.keys()), {0})
        self.assertEqual(flow_to_allocation[0][0], "0-1")
        self.assertAlmostEqual(flow_to_allocation[0][1], 5.0, places=7)

    def test_one_several(self):
        flow_to_allocation = get_resulting_allocation(
            (
                "2,1\n"
                "0,1,1.3"
            ),
            (
                "0-1\n"
                "0-1\n"
                "0-1\n"
                "0-1\n"
                "0-1"
            )
        )
        self.assertEqual(set(flow_to_allocation.keys()), set(list(range(5))))
        for i in range(5):
            self.assertEqual(flow_to_allocation[i][0], "0-1")
            self.assertAlmostEqual(flow_to_allocation[i][1], 0.26, places=7)

    def test_two_one_inactive(self):
        flow_to_allocation = get_resulting_allocation(
            (
                "3,2\n"
                "0,1,1.3\n"
                "1,2,1.3\n"
            ),
            (
                "0-1\n"
                "0-1\n"
                "0-1\n"
                "0-1\n"
                "0-1"
            )
        )
        self.assertEqual(set(flow_to_allocation.keys()), set(list(range(5))))
        for i in range(5):
            self.assertEqual(flow_to_allocation[i][0], "0-1")
            self.assertAlmostEqual(flow_to_allocation[i][1], 0.26, places=7)

    def test_two(self):
        flow_to_allocation = get_resulting_allocation(
            (
                "3,2\n"
                "0,1,1\n"
                "1,2,1\n"
            ),
            (
                "0-1\n"
                "1-2\n"
                "0-1-2"
            )
        )
        self.assertEqual(set(flow_to_allocation.keys()), set(list(range(3))))
        self.assertEqual(flow_to_allocation[0][0], "0-1")
        self.assertAlmostEqual(flow_to_allocation[0][1], 0.5, places=7)
        self.assertEqual(flow_to_allocation[1][0], "1-2")
        self.assertAlmostEqual(flow_to_allocation[1][1], 0.5, places=7)
        self.assertEqual(flow_to_allocation[2][0], "0-1-2")
        self.assertAlmostEqual(flow_to_allocation[2][1], 0.5, places=7)

    def test_two_first_is_bottleneck(self):
        flow_to_allocation = get_resulting_allocation(
            (
                "3,2\n"
                "0,1,1\n"
                "1,2,1\n"
            ),
            (
                "0-1\n"
                "0-1\n"
                "0-1\n"
                "0-1\n"
                "1-2\n"
                "0-1-2"
            )
        )
        self.assertEqual(set(flow_to_allocation.keys()), set(list(range(6))))
        for i in range(4):
            self.assertEqual(flow_to_allocation[i][0], "0-1")
            self.assertAlmostEqual(flow_to_allocation[i][1], 0.2, places=7)
        self.assertEqual(flow_to_allocation[4][0], "1-2")
        self.assertAlmostEqual(flow_to_allocation[4][1], 0.8, places=7)
        self.assertEqual(flow_to_allocation[5][0], "0-1-2")
        self.assertAlmostEqual(flow_to_allocation[5][1], 0.2, places=7)


if __name__ == '__main__':
    unittest.main()
