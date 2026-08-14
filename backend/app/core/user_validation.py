import re


USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")


def normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("用户名须以字母开头，仅含字母、数字、下划线，长度 4～32 位")
    return normalized


def normalize_display_name(display_name: str) -> str:
    normalized = display_name.strip()
    if not normalized:
        raise ValueError("显示姓名不能为空")
    if len(normalized) > 64:
        raise ValueError("显示姓名不能超过 64 位")
    return normalized
