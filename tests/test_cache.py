from cde_recommend.cache import compute_cache_key


def test_compute_cache_key_is_deterministic():
    k1 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])
    k2 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])
    assert k1 == k2


def test_compute_cache_key_differs_for_different_values():
    k1 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])
    k2 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female", "Unknown"])
    assert k1 != k2


def test_compute_cache_key_differs_for_different_version():
    k1 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])
    k2 = compute_cache_key("ccdi", 2, "gender", ["Male", "Female"])
    assert k1 != k2


def test_compute_cache_key_differs_for_different_column():
    k1 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])
    k2 = compute_cache_key("ccdi", 1, "sex", ["Male", "Female"])
    assert k1 != k2


def test_compute_cache_key_order_independent():
    """Sorted values means order of input doesn't matter."""
    k1 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])
    k2 = compute_cache_key("ccdi", 1, "gender", ["Female", "Male"])
    assert k1 == k2


def test_compute_cache_key_is_hex_sha256():
    key = compute_cache_key("ccdi", 1, "gender", ["Male"])
    assert len(key) == 64  # SHA-256 hex digest
    assert all(c in "0123456789abcdef" for c in key)
