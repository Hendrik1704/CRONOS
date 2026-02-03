from src.module_base import BaseModule, time_execution, run_external_command
import logging
import os
import subprocess
import shutil


class IPGlasma(BaseModule):

    def prepare_environment(self, event_dir):
        pass

    def prepare_input(self, event_dir):
        pass

    @time_execution
    def run(self, event_dir):
        pass

    def fetch_output(self, event_dir):
        pass