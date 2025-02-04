# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import tempfile

import pytest
from torchtitan.config_manager import JobConfig


class TestJobConfig:
    def test_command_line_args(self):
        config = JobConfig()
        config.parse_args([])

    def test_job_config_file(self):
        config = JobConfig()
        config.parse_args(["--job.config_file", "./train_configs/debug_model.toml"])

    def test_job_file_does_not_exist(self):
        with pytest.raises(FileNotFoundError):
            config = JobConfig()
            config.parse_args(["--job.config_file", "ohno.toml"])

    def test_empty_config_file(self):
        with tempfile.NamedTemporaryFile() as fp:
            config = JobConfig()
            config.parse_args(["--job.config_file", fp.name])

    def test_job_config_file_cmd_overrides(self):
        config = JobConfig()
        config.parse_args(
            [
                "--job.config_file",
                "./train_configs/debug_model.toml",
                "--job.dump_folder",
                "/tmp/test_tt/",
            ]
        )

    def test_print_help(self):
        config = JobConfig()
        parser = config.parser
        parser.print_help()
