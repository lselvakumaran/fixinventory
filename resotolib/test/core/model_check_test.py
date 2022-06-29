import os
from abc import ABC
from dataclasses import dataclass
from typing import ClassVar

import pytest
from pytest import raises

from resotolib.baseresources import BaseResource
from resotolib.core.model_check import check_overlap


@dataclass
class BreakingResource(BaseResource, ABC):
    kind: ClassVar[str] = "breaking"
    volume_size: str = ""


@pytest.mark.skipif(os.environ.get("MODEL_CHECK") is None, reason="Model check is disabled")
def test_check() -> None:
    # this will throw an exception, since breaking resource has a breaking property
    with raises(Exception):
        check_overlap()
    # hacky way to "delete" the fields - the exporter will not see the field any longer.
    BreakingResource.__dataclass_fields__ = {}
    check_overlap()
