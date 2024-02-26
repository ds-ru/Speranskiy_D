import os
import sqlite3
import func_x5
import pandas as pd
import openpyxl

connection = sqlite3.connect('x5.db')
cursor = connection.cursor()

while True:
    print("Выберите нужное действие или 0 "
          "\n1 Для создания таблиц "
          "\n2 Для чтения Excle "
          "\n3 Для вывода всех данных "
          "\n4 Для кода")
    cmd = 0
    cmd = int(input())
    if cmd == 0:
        break
    if cmd == 1:
        os.system('cls')
        func_x5.create_table(connection, cursor)
    if cmd == 2:
        os.system('cls')
        func_x5.read_date(connection, cursor)
    if cmd == 3:

        func_x5.all_data(connection, cursor)
    if cmd == 4:
        os.system('cls')
        func_x5.use_code(connection, cursor)

connection.commit()
connection.close()
