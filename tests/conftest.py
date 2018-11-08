import logging

import pytest
from pyphantom import fakecam

fakecam.logger.setLevel(logging.INFO)


@pytest.fixture(scope="session", autouse=True)
def run_fakecam(request):
    fakecam.run()
