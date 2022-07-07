__numerals = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
              '百': 100, '千': 1000, '万': 10000, '亿': 100000000}


def decode_chinese_integer(text: str) -> int:
    """
    将中文整数转换为int
    :param text: 中文整数
    :return: 对应int
    """
    ans = 0
    radix = 1
    for i in reversed(range(len(text))):
        if text[i] not in __numerals:
            raise ValueError()
        digit = __numerals[text[i]]
        if digit >= 10:
            if digit > radix:  # 成为新的基数
                radix = digit
                if i == 0:  # 若给定字符串省略了最前面的“一”，如十三、十五……
                    ans = ans + radix
            else:
                radix = radix * digit
        else:
            ans = ans + radix * digit

    return ans


def decode_integer(text: str) -> int:
    try:
        return int(text)
    except ValueError:
        pass

    return decode_chinese_integer(text)


__all__ = ("decode_integer", "decode_chinese_integer")
