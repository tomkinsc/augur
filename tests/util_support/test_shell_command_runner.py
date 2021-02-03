import os
import re
import subprocess

from augur.util_support.shell_command_runner import ShellCommandRunner

import pytest


class TestShellCommandRunner:
    def test_run_exception_no_raise(self, mocker):
        mocker.patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(5, "actual-cmd"),
        )

        assert ShellCommandRunner("great-command", raise_errors=False).run() is False

    def test_run_exception_raise(self, mocker):
        mocker.patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(5, "actual-cmd"),
        )

        with pytest.raises(subprocess.CalledProcessError):
            ShellCommandRunner("great-command", raise_errors=True).run()

    def test_modified_env(self):
        modified_env = ShellCommandRunner(
            "great-command", extra_env={"a": 5}
        ).modified_env

        assert modified_env["a"] == 5
        assert modified_env["HOME"] == os.getenv("HOME")

    @pytest.mark.parametrize(
        "exception, expected_message",
        [
            (
                subprocess.CalledProcessError(5, "actual-cmd", output=b"some error"),
                "Shell exited 5 when running: cmd.*?some error",
            ),
            (
                subprocess.CalledProcessError(-15, "actual-cmd"),
                "Shell exited from fatal signal SIGTERM when running: cmd",
            ),
            (
                subprocess.CalledProcessError(128 + 15, "actual-cmd"),
                "Shell exited from fatal signal SIGTERM when running: cmd",
            ),
            (
                subprocess.CalledProcessError(128 + 9, "actual-cmd"),
                "Shell exited from fatal signal SIGKILL when running: cmd.*out-of-memory",
            ),
            (
                # Unknown signal doesn't cause exception
                subprocess.CalledProcessError(-120, "actual-cmd"),
                "Shell exited -120 when running: cmd",
            ),
            (
                FileNotFoundError(),
                "Unable to run shell commands using /bin/bash",
            ),
            (
                Exception("generic or other exception"),
                "generic or other exception",
            )
        ]
    )
    def test_print_error_message(self, mocker, exception, expected_message):
        mock_print_error = mocker.patch(
            "augur.util_support.shell_command_runner.ShellCommandRunner.print_error"
        )

        ShellCommandRunner("cmd").print_error_message(exception)

        assert re.search(
            expected_message,
            mock_print_error.call_args[0][0],
            re.MULTILINE | re.DOTALL
        )
