"""Basic health checks - pytest setup validation"""


def test_pytest_is_working():
    """Verify pytest framework is working"""
    assert True


def test_basic_math():
    """Verify basic Python operations"""
    assert 2 + 2 == 4


def test_list_operations():
    """Verify list manipulation"""
    test_list = [1, 2, 3]
    test_list.append(4)
    assert len(test_list) == 4
    assert test_list[0] == 1
