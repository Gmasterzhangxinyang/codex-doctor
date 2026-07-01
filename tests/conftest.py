from datetime import datetime, timedelta, timezone

import pytest

from codex_doctor.schemas import Event


@pytest.fixture
def events_prompt_old():
    return [
        Event(
            event_type="UserPromptSubmit",
            session_id="s1",
            ts=datetime.now(timezone.utc) - timedelta(seconds=30),
        )
    ]
