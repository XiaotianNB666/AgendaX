import time

from core.i18n import t


def convert_hh_mm_ss_to_time_offset(time_str: str) -> int:
    """
    将 "hh:mm:ss" 格式的字符串转换为秒数偏移
    """
    try:
        hour, minutes, seconds = map(int, time_str.split(':'))
        return hour * 3600 + minutes * 60 + seconds
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}. Expected 'MM:ss'.")

def convert_offset_to_hh_mm_ss(offset: int) -> str:
    """
    将秒数偏移转换为 "hh:mm:ss" 格式的字符串
    """
    hour = offset // 3600
    minutes = (offset % 3600) // 60
    seconds = offset % 60
    return f"{hour:02d}:{minutes:02d}:{seconds:02d}"

def get_initial_time_of_this_day(_time: float = None) -> int:
    """
    获取当天 00:00:00 的时间戳
    """
    if _time is None:
        now = time.localtime()
    else:
        now = time.localtime(_time)
    return int(time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 0, 0, 0, now.tm_wday, now.tm_yday, now.tm_isdst)))

def get_closest_time(target: int, times: list[float]):
    """
    在 times 中找到最接近 target 的时间
    """
    closest_time = min(times, key=lambda t: abs(t - target))
    return closest_time

# 获取某天相对于今天的叫法(不处理今天以前的)。如今天是 2026-04-06，则 2026-04-07 是 "明天"，2026-04-08 是 "后天"，再往后则是(下)周几，直到下周日，然后就是日期了
def get_day_name(target_time: int) -> str:
    today_initial_time = get_initial_time_of_this_day()
    day_offset = (target_time - today_initial_time) // 86400
    if day_offset == 0:
        return t("time.today")
    elif day_offset == 1:
        return t("time.tomorrow")
    elif day_offset == 2:
        return t("time.day_after_tomorrow")
    else:
        # 计算目标时间是(下)周几
        target_weekday = time.localtime(target_time).tm_wday % 7 + 1 # Python 的 tm_wday 是 0-6，0 是周一；这里转换为 1-7，1 是周一
        weeks = (target_time - today_initial_time) // 604800 # 604800 是一周的秒数
        if weeks == 1:
            return t("time.next_weekday", weekday=t(f"time.weekday.{target_weekday}"))
        elif weeks == 0:
            return t(f"time.weekday.{target_weekday}")
        return time.strftime("%Y-%m-%d", time.localtime(target_time))
