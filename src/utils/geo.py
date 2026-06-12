"""GPS 坐标工具 — 球面距离计算与随机偏移模拟

Haversine 公式用于验证打卡位置是否在宿舍精度范围内。
random_offset 使用独立 Random 实例（seed 参数）避免污染全局随机状态，
同时支持测试场景的确定性复现。

Important caveats:
  - 所有坐标单位为度（decimal degrees），距离单位为米
  - random_offset 最大偏移量默认 0.0005°（约 55m），保留 6 位小数

Variable naming: All names must be meaningful and context-relevant.
"""
import math
import random


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine 球面距离公式，返回两点间距离（米）

    用于校验当前定位与宿舍坐标之间的距离是否在精度上限内
    """
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def random_offset(lat: float, lng: float, max_offset: float = 0.0005,
                 seed: int | None = None) -> tuple:
    """以宿舍坐标为中心生成随机偏移，模拟真实 GPS 定位

    保留 6 位小数（约 0.1 米精度），seed 参数用于测试场景复现
    """
    rng = random.Random(seed)  # seed=None 自动使用系统熵源，避免污染全局随机状态
    lat += rng.uniform(-max_offset, max_offset)
    lng += rng.uniform(-max_offset, max_offset)
    return round(lat, 6), round(lng, 6)
