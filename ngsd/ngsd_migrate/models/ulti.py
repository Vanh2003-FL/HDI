
# phogng ban nhân viên
def to_hr(unit):
    dta = unit.split('/')
    address_id = en_area_id = en_block_id = department_id = en_department_id = ''
    for d in dta:
        if d == 'NGS Consulting (NGSC)':
            address_id = 'NGSC'
        elif 'Khối' in d:
            en_block_id = d.replace('Khối ', '')
        elif 'Phòng' in d:
            en_department_id = d.replace('Phòng ', '')
        elif 'Trung tâm' in d or 'Ban' in d:
            department_id = d.replace('Trung tâm ', '').replace('Ban ', '')
        elif f"{d}/Khối" in unit:
            en_area_id = d
        elif f"{d}/Phòng" in unit:
            department_id = d
        else:
            department_id = d
    print('\t'.join([address_id, en_area_id, en_block_id, department_id, en_department_id]))
a = """"""
print("\n".join([to_hr(name) for name in a.split('\n')]))


# Mã dự án
import re

def no_accent_vietnamese(s):
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[ÀÁẠẢÃĂẰẮẶẲẴÂẦẤẬẨẪ]', 'A', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[ÈÉẸẺẼÊỀẾỆỂỄ]', 'E', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]', 'O', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[ÌÍỊỈĨ]', 'I', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ƯỪỨỰỬỮÙÚỤỦŨ]', 'U', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[ỲÝỴỶỸ]', 'Y', s)
    s = re.sub(r'[Đ]', 'D', s)
    s = re.sub(r'[đ]', 'd', s)
    return s

import unidecode
def remove_accent(text):
    return unidecode.unidecode(text)
a = """"""
print("\n".join([remove_accent(no_accent_vietnamese(name)).replace(' ', '_') for name in a.split('\n')]))

# ngày
from datetime import datetime
def remove_time(to_date):
    return datetime.strptime(to_date, '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')
a = """"""
print("\n".join([remove_time(name) for name in a.split('\n')]))

# khnl
def santi_same(datas, idx):
    current = ''
    res = []
    emty = ['' for x in range(len(datas[0]))]
    for data in datas:
        if data[idx] == current:
            res.append(emty)
        else:
            res.append(data)
            current = data[idx]
    return "\n".join(['\t'.join(name) for name in res])

a = """"""
b = santi_same([x.split('\t') for x in a.split('\n')])

# số phiên bản
def santi_version(vesion):
    return '.'.join(vesion)
a = """"""
print("\n".join([santi_version(name) for name in a.split('\n')]))


# trạng thi giai đoạn
map = {
    'PENDING': 'delayed',
    'IN_PROGRESS': 'ongoing',
    'CHECKING': 'review',
    'DONE': 'done',
}
a = """"""
print("\n".join([map.get(name) for name in a.split('\n')]))


# trạng thái gói việc
map = {
    'PENDING': 'delayed',
    'IN_PROGRESS': 'ongoing',
    'CHECKING': 'review',
    'DONE': 'done',
}
a = """"""
print("\n".join([map.get(name) for name in a.split('\n')]))

# trạng thái wbs
map = {
    'INIT': 'draft',
    'PENDING': 'awaiting',
    'APPROVED': 'approved',
    'FAILED': 'refused',
}
a = """"""
print("\n".join([map.get(name) for name in a.split('\n')]))

# Tên nhân viên
def santi_hr_name(name):
    name_ds = name.split(' ')
    if len(name_ds) == 2:
        return ' '.join([name_ds[1], name_ds[0]])
    if len(name_ds) == 3:
        return ' '.join([name_ds[2], name_ds[1], name_ds[0]])
    if len(name_ds) == 4:
        return ' '.join([name_ds[3], name_ds[2], name_ds[0], name_ds[1]])
    return name
a = """"""
print("\n".join([santi_hr_name(name) for name in a.split('\n')]))

