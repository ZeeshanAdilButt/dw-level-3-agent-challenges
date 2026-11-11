import sys

import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import check_dashes  # noqa: E402

pytestmark = pytest.mark.invariant


def test_fails_on_an_em_or_en_dash_and_passes_on_a_range(tmp_path, capsys):
    clean = tmp_path / "a.md"
    clean.write_text("Between 60-70 percent, a plain hyphen - is fine.\n", encoding="utf-8")
    em = tmp_path / "b.md"
    em.write_text("one " + chr(0x2014) + " two\n", encoding="utf-8")
    en = tmp_path / "c.js"
    en.write_text("// 60" + chr(0x2013) + "70\n", encoding="utf-8")
    assert check_dashes.main([str(clean)]) == 0
    assert check_dashes.main([str(em)]) == 1 and "b.md:1: em dash" in capsys.readouterr().out
    assert check_dashes.main([str(tmp_path)]) == 1
    assert check_dashes.main(["--warn", str(en)]) == 0
