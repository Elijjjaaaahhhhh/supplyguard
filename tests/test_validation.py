import pytest

from supplyguard.validation import ValidationError


def test_validation_error_is_exception():
    with pytest.raises(ValidationError):
        raise ValidationError("test failure")