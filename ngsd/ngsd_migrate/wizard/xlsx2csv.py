# importing pandas as pd
import pandas as pd
from os import listdir
from os.path import isfile, join


path = 'C:\\Users\\TOM\\Downloads\\OneDrive_2024-03-15\\timesheet_xuat_tay'


def sync_folder_data(path):
    for c in listdir(path):
        if '.xlsx' not in c:
            continue
        path_file = join(path, c)
        if isfile(path_file):
            read_file = pd.read_excel(path_file)
            read_file.to_csv(path_file.replace('.xlsx', '.csv'),
                             index=None,
                             header=True, encoding='utf-8-sig')
sync_folder_data(path)
