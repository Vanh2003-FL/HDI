# -*- coding: utf-8 -*-


def trim_recursion(string):
    string = string.replace(SPACE_CHAR * 2, SPACE_CHAR)
    return trim_recursion(string) if SPACE_CHAR * 2 in string else string


SPACE_CHAR, CURRENCY, HUNDRED_UNIT = ' ', 'đồng', ['', 'mươi', 'trăm']
UNIT_NAME = ['', 'nghìn', 'triệu', 'tỷ', 'nghìn tỷ', 'triệu tỷ', 'tỷ tỷ']
NUMBER_TO_STRING = {'0': 'không', '1': 'một', '2': 'hai', '3': 'ba', '4': 'bốn', '5': 'năm', '6': 'sáu', '7': 'bảy', '8': 'tám', '9': 'chín'}
REPLACE_WORD = {'không mươi': 'linh', 'linh không': '', 'mươi không': 'mươi', 'một mươi': 'mười', 'mươi bốn': 'mươi tư', 'mười năm': 'mười lăm', 'mươi một': 'mươi mốt', 'mươi năm': 'mươi lăm', }
REPLACE_WORD_2 = dict([(trim_recursion(SPACE_CHAR.join((NUMBER_TO_STRING['0'], HUNDRED_UNIT[2], unit_name, CURRENCY))), CURRENCY) for unit_name in UNIT_NAME])
REPLACE_WORD_3 = {'không trăm linh đồng': 'đồng', 'không trăm linh không đồng': 'đồng', 'trăm linh nghìn': 'trăm nghìn'}
REPLACE_WORD_4 = dict([('không trăm %s không trăm' % s, 'không trăm') for s in UNIT_NAME[1:]])
REPLACE_WORD_5 = dict([('không trăm %s' % s, '') for s in UNIT_NAME[1:]])

def number2text_vn(n):
    """ Convert number to Vietnam currency """
    float_number = float(n) if not isinstance(n, float) else n
    integer_part = int(float_number)
    decimal_part = str(float_number).split('.')[1] if '.' in str(float_number) else 0

    def read_hundred(hundred_number_s='025'):
        res, index = '', 0
        for char in reversed(hundred_number_s):
            res = SPACE_CHAR.join((NUMBER_TO_STRING[char], HUNDRED_UNIT[index], res))
            index += 1
        return res

    def read_number(number_s='1600300444'):
        groups = [number_s[::-1][i:i + 3][::-1] for i in range(0, len(number_s), 3)]
        res, index = '', 0
        for hundred in groups:
            res = SPACE_CHAR.join((read_hundred(hundred), UNIT_NAME[index], res))
            index += 1
        return res

    def to_string(money):
        string_money = str(money) if not isinstance(money, str) else money
        string_money = read_number(string_money)
        return string_money

    string_integer = to_string(integer_part)
    string_decimal = to_string(decimal_part) if int(decimal_part) else ''
    comma = 'phẩy' if string_decimal else ''
    result = trim_recursion(SPACE_CHAR.join((string_integer, comma, string_decimal, CURRENCY)))

    # Replace wrong words
    for wrong_word, right_word in REPLACE_WORD.items():
        result = trim_recursion(result.replace(wrong_word, right_word))
    for wrong_word, right_word in REPLACE_WORD_2.items():
        result = trim_recursion(result.replace(trim_recursion(wrong_word), right_word))
    for wrong_word, right_word in REPLACE_WORD_3.items():
        result = trim_recursion(result.replace(trim_recursion(wrong_word), right_word))
    for wrong_word, right_word in REPLACE_WORD_4.items():
        result = trim_recursion(result.replace(trim_recursion(wrong_word), right_word))
    for wrong_word, right_word in REPLACE_WORD_5.items():
        result = trim_recursion(result.replace(trim_recursion(wrong_word), right_word))

    return result.strip()


if __name__ == '__main__':
    assert number2text_vn(7000000) == 'bảy triệu đồng'
    assert number2text_vn(7000002) == 'bảy triệu không trăm linh hai đồng'
    assert number2text_vn(7000020) == 'bảy triệu không trăm hai mươi đồng'
    assert number2text_vn(7000200) == 'bảy triệu hai trăm đồng'
    assert number2text_vn(7002000) == 'bảy triệu không trăm linh hai nghìn đồng'
    assert number2text_vn(7020000) == 'bảy triệu không trăm hai mươi nghìn đồng'
    assert number2text_vn(7200000) == 'bảy triệu hai trăm nghìn đồng'

    assert number2text_vn(7000022) == 'bảy triệu không trăm hai mươi hai đồng'
    assert number2text_vn(7000220) == 'bảy triệu hai trăm hai mươi đồng'
    assert number2text_vn(7002200) == 'bảy triệu không trăm linh hai nghìn hai trăm đồng'
    assert number2text_vn(7022000) == 'bảy triệu không trăm hai mươi hai nghìn đồng'
    assert number2text_vn(7220000) == 'bảy triệu hai trăm hai mươi nghìn đồng'

    assert number2text_vn(7000202) == 'bảy triệu hai trăm linh hai đồng'
    assert number2text_vn(7002020) == 'bảy triệu không trăm linh hai nghìn không trăm hai mươi đồng'
    assert number2text_vn(7020200) == 'bảy triệu không trăm hai mươi nghìn hai trăm đồng'
    assert number2text_vn(7202000) == 'bảy triệu hai trăm linh hai nghìn đồng'

    assert number2text_vn(7000222) == 'bảy triệu hai trăm hai mươi hai đồng'
    assert number2text_vn(7002220) == 'bảy triệu không trăm linh hai nghìn hai trăm hai mươi đồng'
    assert number2text_vn(7022200) == 'bảy triệu không trăm hai mươi hai nghìn hai trăm đồng'
    assert number2text_vn(7222000) == 'bảy triệu hai trăm hai mươi hai nghìn đồng'
    assert number2text_vn(7002022) == 'bảy triệu không trăm linh hai nghìn không trăm hai mươi hai đồng'
    assert number2text_vn(7020220) == 'bảy triệu không trăm hai mươi nghìn hai trăm hai mươi đồng'
    assert number2text_vn(7202200) == 'bảy triệu hai trăm linh hai nghìn hai trăm đồng'
    assert number2text_vn(7020022) == 'bảy triệu không trăm hai mươi nghìn không trăm hai mươi hai đồng'
    assert number2text_vn(7200220) == 'bảy triệu hai trăm nghìn hai trăm hai mươi đồng'
    assert number2text_vn(7200022) == 'bảy triệu hai trăm nghìn không trăm hai mươi hai đồng'

