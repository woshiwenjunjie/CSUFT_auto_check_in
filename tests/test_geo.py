"""Haversine 距离计算与 GPS 随机偏移测试"""
from src.utils.geo import haversine, random_offset


def test_haversine_same_point():
    """同一点距离为 0"""
    assert haversine(30.0, 120.0, 30.0, 120.0) == 0.0


def test_haversine_equator_one_degree():
    """赤道上 1 度约 111 公里"""
    dist = haversine(0, 0, 0, 1)
    assert 111000 < dist < 112000


def test_haversine_pole_to_pole():
    """南极到北极约 10000 公里"""
    dist = haversine(0, 0, 90, 0)
    assert 10000000 < dist < 10020000


def test_haversine_known_two_points():
    """北京到上海约 1070 公里"""
    dist = haversine(39.9042, 116.4074, 31.2304, 121.4737)
    assert 1060000 < dist < 1080000


def test_random_offset_bounds():
    """偏移量不超过 max_offset"""
    lat, lng = 30.0, 120.0
    max_off = 0.001
    for _ in range(100):
        rlat, rlng = random_offset(lat, lng, max_off)
        assert abs(rlat - lat) <= max_off + 1e-6
        assert abs(rlng - lng) <= max_off + 1e-6


def test_random_offset_seed_reproducibility():
    """相同 seed 产生相同偏移"""
    lat, lng = 30.0, 120.0
    r1a, r1b = random_offset(lat, lng, seed=42)
    r2a, r2b = random_offset(lat, lng, seed=42)
    assert r1a == r2a
    assert r1b == r2b


def test_random_offset_seed_different():
    """不同 seed 产生不同偏移"""
    lat, lng = 30.0, 120.0
    r1 = random_offset(lat, lng, seed=1)
    r2 = random_offset(lat, lng, seed=2)
    assert r1 != r2


def test_random_offset_6_decimal():
    """偏移结果保留 6 位小数"""
    lat, lng = random_offset(30.0, 120.0, seed=42)
    assert len(str(lat).split(".")[1]) <= 6
    assert len(str(lng).split(".")[1]) <= 6


def test_haversine_zero_coordinates():
    """空坐标 (0, 0) 的 haversine 距离"""
    assert haversine(0, 0, 0, 0) == 0.0


def test_haversine_zero_to_nonzero():
    """从 (0, 0) 到非零坐标的距离应为正值"""
    dist = haversine(0, 0, 30, 120)
    assert dist > 0


def test_haversine_extreme_lat_near_pole():
    """极大纬度值（接近 90）的 haversine 计算"""
    dist = haversine(89.9, 0, 89.9, 1)
    assert dist > 0
    assert dist < 20000


def test_haversine_extreme_lng_wraparound():
    """经度接近 180/-180 的情况"""
    dist = haversine(0, 179.9, 0, -179.9)
    assert dist > 0
    assert dist < 50000


def test_random_offset_zero_max_offset():
    """max_offset=0 时不改变坐标"""
    lat, lng = 30.0, 120.0
    rlat, rlng = random_offset(lat, lng, max_offset=0, seed=42)
    assert rlat == lat
    assert rlng == lng


def test_random_offset_very_small_max_offset():
    """极小 max_offset（1e-9）坐标变化极小"""
    lat, lng = 30.0, 120.0
    rlat, rlng = random_offset(lat, lng, max_offset=1e-9, seed=42)
    lat_diff = abs(rlat - lat)
    lng_diff = abs(rlng - lng)
    assert lat_diff <= 1e-9 + 1e-6
    assert lng_diff <= 1e-9 + 1e-6
