
def time_to_seconds(time_str: str) -> float:
        h, m, s = time_str.split(':')
        total_seconds = int(h) * 3600 + int(m) * 60 + float(s)
        return total_seconds