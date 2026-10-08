import lumamatch


def test_import_exposes_version():
    assert isinstance(lumamatch.__version__, str) and lumamatch.__version__
