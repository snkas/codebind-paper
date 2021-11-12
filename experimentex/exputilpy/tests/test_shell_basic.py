# The MIT License (MIT)
#
# Copyright (c) 2019 snkas
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

from exputil import *
import unittest


ENABLE_REMOTE_TEST = False
REMOTE_USER = "user"
REMOTE_HOST = "machine"


class TestBasic(unittest.TestCase):

    def test_local_shell(self):
        local_shell = LocalShell()
        
        self.assertTrue(local_shell.exec("ls").return_code <= 100)

        res = local_shell.exec("echo \"Hello world\"")
        self.assertTrue(res.return_code <= 100)
        self.assertEqual(res.output.strip(), "Hello world")

        res = local_shell.exec("abcd")
        self.assertFalse(res.return_code <= 100)

        res = local_shell.exec("abcd", output_redirect=OutputRedirect.SILENT)
        self.assertFalse(res.return_code <= 100)

        res = local_shell.exec("echo 'Hello world'", output_redirect=OutputRedirect.SILENT)
        self.assertTrue(res.return_code <= 100)

        self.assertIsNotNone(str(local_shell.exec("ls")))

        res = local_shell.exec("ls", output_redirect=OutputRedirect.CONSOLE)
        self.assertTrue(res.return_code <= 100)
        self.assertEqual("", res.output)

        # Create file
        res = local_shell.exec("echo \"abcdef\" > abcdef.txt", sync=False)
        res.process.communicate()

        # Check file content sync
        self.assertEqual(local_shell.exec("cat abcdef.txt").output.strip(), "abcdef")

        # Check file content async
        res = local_shell.exec("cat abcdef.txt", sync=False)
        out, err = res.process.communicate()
        self.assertEqual("abcdef", out.decode("utf-8").strip())
        self.assertEqual(0, res.process.returncode)

        # Remove file (clean-up)
        self.assertTrue(local_shell.exec("rm -f abcdef.txt").return_code <= 100)

    def test_failing_commands(self):
        local_shell = LocalShell()
        self.assertFalse(local_shell.exec("/dev/null").return_code <= 100)
        self.assertTrue(local_shell.exec("exit -1").return_code > 100 or local_shell.exec("exit -1").return_code == 2)
        self.assertFalse(local_shell.exec("illegal_command").return_code <= 100)

        try:
            local_shell.perfect_exec("echo \"Hello world\"", output_redirect="invalid_value")
            self.assertTrue(False)
        except ValueError:
            self.assertTrue(True)

        try:
            local_shell.perfect_exec("/dev/null")
            self.assertTrue(False)
        except InvalidCommandError:
            self.assertTrue(True)

        try:
            local_shell.perfect_exec("exit 1")
            self.assertTrue(False)
        except FailedCommandError:
            self.assertTrue(True)

        try:
            local_shell.valid_exec("/dev/null")
            self.assertTrue(False)
        except InvalidCommandError:
            self.assertTrue(True)

        if ENABLE_REMOTE_TEST:
            remote_shell = RemoteShell(REMOTE_USER, REMOTE_HOST)

            self.assertFalse(remote_shell.exec("/dev/null").return_code <= 100)
            self.assertFalse(remote_shell.exec("exit -1").return_code <= 100)
            self.assertFalse(remote_shell.exec("illegal_command").return_code <= 100)

            try:
                remote_shell.perfect_exec("/dev/null")
                self.assertTrue(False)
            except InvalidCommandError:
                self.assertTrue(True)

            try:
                remote_shell.perfect_exec("exit 1")
                self.assertTrue(False)
            except FailedCommandError:
                self.assertTrue(True)

            try:
                remote_shell.valid_exec("/dev/null")
                self.assertTrue(False)
            except InvalidCommandError:
                self.assertTrue(True)

            remote_shell.valid_exec("exit 1")

    def test_local_shell_invalid(self):
        local_shell = LocalShell()
        try:
            local_shell.exec("echo 'Hello world'", sync=False, output_redirect=OutputRedirect.SIMPLE_STRING)
            self.assertTrue(False)
        except ValueError:
            self.assertTrue(True)

    def test_remote_shell(self):
        if ENABLE_REMOTE_TEST:
            remote_shell = RemoteShell(REMOTE_USER, REMOTE_HOST)

            self.assertTrue(remote_shell.exec("ls").return_code <= 100)

            res = remote_shell.exec("echo \"Hello world\"")
            self.assertTrue(res.return_code <= 100)
            self.assertEqual(res.output.strip(), "Hello world")

            res = remote_shell.exec("abcd")
            self.assertFalse(res.return_code <= 100)

            # Remove file if still there
            self.assertTrue(remote_shell.exec("rm -f abcdef.txt").return_code <= 100)

            # Create file
            res = remote_shell.exec("echo \"abcdef\" > abcdef.txt", sync=False)
            res.process.communicate()

            # Check file content sync
            self.assertEqual(remote_shell.exec("cat abcdef.txt").output.strip(), "abcdef")

            # Check file content async
            res = remote_shell.exec("cat abcdef.txt", sync=False)
            out, err = res.process.communicate()
            self.assertEqual("abcdef", out.decode("utf-8").strip())
            self.assertEqual(0, res.process.returncode)

            # Remove file (clean-up)
            self.assertTrue(remote_shell.exec("rm -f abcdef.txt").return_code <= 100)

    def test_remote_shell_screens(self):
        if ENABLE_REMOTE_TEST:
            remote_shell = RemoteShell(REMOTE_USER, REMOTE_HOST)
            remote_shell.killall("screen")
            self.assertEqual(0, remote_shell.count_screens())
            remote_shell.detached_exec("echo \"Hello\"", keep_alive=True)
            self.assertEqual(1, remote_shell.count_screens())
            remote_shell.killall("screen")
            self.assertEqual(0, remote_shell.count_screens())

    def test_local_shell_screens(self):
        local_shell = LocalShell()
        local_shell.killall("screen")
        self.assertEqual(0, local_shell.count_screens())
        local_shell.detached_exec("echo \"Hello\"", keep_alive=True)
        self.assertEqual(1, local_shell.count_screens())
        local_shell.killall("screen")
        self.assertEqual(0, local_shell.count_screens())
