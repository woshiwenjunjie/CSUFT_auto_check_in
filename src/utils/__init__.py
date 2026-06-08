from datetime import timezone, timedelta

# 北京时间 (UTC+8)，项目全局统一使用，不受系统时区影响
BEIJING_TZ = timezone(timedelta(hours=8))
