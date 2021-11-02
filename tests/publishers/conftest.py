from datetime import timedelta
from uuid import UUID

import arrow
import pytest

from mobilizon_reshare.event.event import MobilizonEvent
from mobilizon_reshare.publishers.abstract import (
    AbstractPlatform,
    AbstractEventFormatter,
)
from mobilizon_reshare.publishers.exceptions import PublisherError, InvalidResponse


@pytest.fixture
def test_event():
    now = arrow.now()
    return MobilizonEvent(
        **{
            "name": "TestName",
            "description": "TestDescr",
            "begin_datetime": now,
            "end_datetime": now + timedelta(hours=1),
            "mobilizon_link": "",
            "mobilizon_id": UUID(int=0),
        }
    )


@pytest.fixture
def mock_formatter_invalid():
    class MockFormatter(AbstractEventFormatter):
        def validate_event(self, event) -> None:
            raise PublisherError("Invalid event error")

        def get_message_from_event(self, event) -> str:
            return ""

        def validate_message(self, event) -> None:
            raise PublisherError("Invalid message error")

    return MockFormatter()


@pytest.fixture
def mock_publisher_invalid(message_collector):
    class MockPublisher(AbstractPlatform):

        name = "mock"

        def _send(self, message):
            message_collector.append(message)

        def _validate_response(self, response):
            return InvalidResponse("response error")

        def validate_credentials(self) -> None:
            raise PublisherError("credentials error")

    return MockPublisher()


@pytest.fixture
def mock_publisher_invalid_response(message_collector):
    class MockPublisher(AbstractPlatform):

        name = "mock"

        def _send(self, message):
            message_collector.append(message)

        def _validate_response(self, response):
            raise InvalidResponse("Invalid response")

        def validate_credentials(self) -> None:
            pass

    return MockPublisher()
