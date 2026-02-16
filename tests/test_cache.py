from cde_recommend.cache import compute_cache_key


def test_compute_cache_key_is_deterministic():
    # Given: identical inputs
    # When: computed twice
    k1 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])
    k2 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])

    # Then: keys match
    assert k1 == k2


def test_compute_cache_key_differs_for_different_values():
    # Given: same column but different value lists
    k1 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])
    k2 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female", "Unknown"])

    # Then: keys differ
    assert k1 != k2


def test_compute_cache_key_differs_for_different_version():
    # Given: same column but different version numbers
    k1 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])
    k2 = compute_cache_key("ccdi", 2, "gender", ["Male", "Female"])

    # Then: keys differ
    assert k1 != k2


def test_compute_cache_key_differs_for_different_column():
    # Given: same values but different column names
    k1 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])
    k2 = compute_cache_key("ccdi", 1, "sex", ["Male", "Female"])

    # Then: keys differ
    assert k1 != k2


def test_compute_cache_key_order_independent():
    # Given: same values in different order
    k1 = compute_cache_key("ccdi", 1, "gender", ["Male", "Female"])
    k2 = compute_cache_key("ccdi", 1, "gender", ["Female", "Male"])

    # Then: keys match (values are sorted internally)
    assert k1 == k2


def test_compute_cache_key_is_hex_sha256():
    # Given: any valid input
    key = compute_cache_key("ccdi", 1, "gender", ["Male"])

    # Then: result is a 64-char hex SHA-256 digest
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)
