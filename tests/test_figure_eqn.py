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


def test_img_dims_both_attribute_orders():
    a = '<hp:imgDim dimwidth="1800000" dimheight="1440000"/>'
    b = '<hp:imgDim dimheight="1440000" dimwidth="1800000"/>'
    assert lib.img_dims(a) == [(1800000, 1440000)]
    assert lib.img_dims(b) == [(1800000, 1440000)]
