from uniscript_ink.handwriting.profiles import list_profiles, load_profile


def test_profiles_load():
    names = list_profiles()
    assert "everyday" in names
    assert "neat_student" in names
    profile = load_profile("everyday")
    assert profile.synthesis_level == "C"
    assert profile.name == "everyday"
