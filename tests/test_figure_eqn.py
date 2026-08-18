import pytest

import _hwpxlib as lib
from conftest import SECTION_XML, PNG_1x1


def test_png_dimensions():
    assert lib.png_dimensions(PNG_1x1) == (1, 1)


def test_clone_equation_fresh_id():
    out = lib.clone_equation(SECTION_XML, "device _{key}", "로 끝난다.")
    ids = lib._EQ_ID.findall(out)
    assert len(ids) == 2                 # original + clone
    assert len(set(ids)) == 2            # ids are unique
    assert lib.is_wellformed(out) is True


def test_clone_equation_bad_template():
    with pytest.raises(ValueError):
        lib.clone_equation(SECTION_XML, "no such script", "로 끝난다.")
