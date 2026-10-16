from uniscript_ink.languages.scripts import detect_script, split_script_runs


def test_detect_latin():
    assert detect_script("A")[0] == "latin"


def test_detect_sinhala():
    assert detect_script("අ")[0] == "sinhala"


def test_detect_tamil():
    assert detect_script("அ")[0] == "tamil"


def test_mixed_runs_preserve_text():
    text = "Hello අකුරු Tamil த"
    runs = split_script_runs(text)
    assert "".join(r.text for r in runs) == text
    scripts = {r.script for r in runs}
    assert "latin" in scripts
    assert "sinhala" in scripts
    assert "tamil" in scripts
