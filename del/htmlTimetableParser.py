# -*- coding: utf-8 -*-

import requests
import constants
import pickle
import datetime
import os
from lxml import html


def get_groups():
    """ Получение списка групп в виде list[0,1],
            где list[0] - группа,
              а list[1] - подгруппа (или пустая строка)"""
    page = requests.get(constants.URL_TIMETABLES)

    tree = html.fromstring(page.content)
    raw_groups = tree.xpath(".//div[@class=\"collapsed-content\"]/ul/li/a[@href]/text()")
    groups = []
    for i in raw_groups:
        i = (i.replace('\xa0', ' ').split(' ('))
        try:
            i[1] = i[1].replace(')', '')
        except IndexError:
            i.append('')
        groups.append(i)

    return groups


def get_timetable(group):
    """

    Принимает группу из get_groups-списка или [ГРУППА, ПОДГРУППА]
    Возвращает полное расписание (исп. timetable[ЧЕТН\НЕЧЕТН(0-1)][ДЕНЬ_НЕДЕЛИ(0-5)][ЛЕНТА(0-6)])

    """

    raw_timetable = __get_raw_timetable(group)
    timetable = [[], []]
    for day in range(0, 6):
        timetable[0].append(__get_raw_day(raw_timetable, day=day, week=constants.ODD))
        timetable[1].append(__get_raw_day(raw_timetable, day=day, week=constants.EVEN))
    return timetable


def get_week():
    week_number = datetime.datetime.today().isocalendar()[1]
    return constants.EVEN if week_number % 2 == 0 else constants.ODD


def get_day(group, day=datetime.datetime.today().weekday(), week=get_week(), local=True):
    if not isinstance(group, list):
        raise TypeError
    if local is False:
        pass


def write(timetable, group):
    try:
        os.mkdir(os.getcwd() + '/timetables')
    except FileExistsError:
        pass
    filename = os.getcwd() + '/timetables/' + filename_parser(group)

    with open(filename, 'wb') as file:
         pickle.dump(timetable, file)


def read(group):
    filename = os.getcwd() + '/timetables/' + filename_parser(group)

    with open(filename, 'rb') as file:
        timetable = pickle.load(file)
    return timetable


def filename_parser(group):
    if type(group) == list:
        filename = group[0].replace(' ', '').replace('/', '').replace('-', '')
        try:
            if group[1] != "":
                filename += '_' + group[1]  # пробуем добавить подгруппу к запросу, если есть
        except IndexError:
            pass
        filename = filename.upper()
    elif type(group) == str:
        filename = group.replace(' ', '').replace('/', '').replace('-', '').upper()
    return filename


def __get_raw_timetable(group):
    """Получение расписания. Принимает список group состоящий из группы и подргруппы"""
    page = requests.get(__get_request(group))  # получаем страницу с расписанием
    tree = html.fromstring(page.content)  # вытаскиваем содержимое страницы в дерево
    timetable = tree.xpath("//table[@class=\"table timetable\"]/*/*/text()")
    lessons = tree.xpath('///td[@width="40%"]/*/node() | //td[@width="40%"]/text()')

    odd_even = tree.xpath("//tr[@class=\"table-center\"]")  # ленты нечетн\четн ([0] - нечет, [1] - чет). None-пары нет

    tmp = []
    # избавляемся от лишних пробелов и времени
    for i in timetable:
        if i[0] == ' ':
            i = i[1:]
        if __is_there(i, *constants.DAYS_WEEK, *constants.LESSON):
            tmp.append(i)
    timetable = tmp[:]
    lessons_final = []

    for i in range(0, len(lessons)):
        tmp = []
        try:
            _current = lessons.pop(0)
        except IndexError:
            break
        tmp.append(_current)
        try:
            _next = lessons.pop(0)
        except IndexError:
            lessons_final.append(tmp[:])
            break
        if __is_there(_next, 'спортзал'):
            tmp.append(_next)

        elif __is_there(_next, ' (лекция)', ' (лабораторная работа)', ' (практика)'):
            try:
                tmp.append(_next[1:])
                _next = lessons.pop(0)
                if isinstance(_next, html.HtmlElement):
                    tmp.append(_next.text)
                    tmp.append(lessons.pop(0))
                else:
                    lessons.insert(0, _next)
            except IndexError:
                lessons_final.append(tmp[:])
                break
        elif isinstance(_next, html.HtmlElement):
            try:
                tmp.append(_next.text)
                tmp.append(lessons.pop(0))
            except IndexError:
                lessons_final.append(tmp[:])
                break
        else:
            lessons.insert(0, _next)
        lessons_final.append(tmp[:])
    count_odd_even = -1  # счетчик для списка odd_even
    timetable.append("Воскресенье")  # чтобы функция знала, где конец
    timetable_final = []  # расписание, возвращаемое функцией
    tmp = []
    for i in range(0, len(timetable)):
        cur_value = timetable[i]
        if __is_there(cur_value, *constants.DAYS_WEEK):
            if cur_value != constants.DAYS_WEEK[0]:
                timetable_final.append(tmp[:])
                tmp.clear()
            tmp.append(cur_value)
            count_odd_even += 1
            continue
        if __is_there(cur_value, *constants.LESSON):
            tmp.append(cur_value)
            value_odd_even = odd_even.pop(0).xpath("./td[@width=\"40%\"]")
            lesson_odd = value_odd_even[0].find('b')  # None - занятие отсутствует
            try:
                lesson_even = value_odd_even[1].find('b')  # None - занятие отсутствует
            except IndexError:
                lesson_even = False  # False означает, что одно и тоже занятие (lesson_odd) каждую неделю
            # Если есть первое занятие
            if lesson_odd is not None:
                tmp.extend(lessons_final.pop(0)[:])
                if lesson_even is False: continue
            else:
                tmp.append(constants.EMPTY)
            # Если есть второе занятие
            if lesson_even is not None:
                tmp.extend(lessons_final.pop(0)[:])
            else:
                # Если второго занятия нет
                tmp.append(constants.EMPTY)
        else:
            timetable_final.append(cur_value)
    return timetable_final


def __get_raw_day(timetable, day=datetime.datetime.today().weekday(), week=get_week()):
    # 0 - Понедельник, 5 - Суббота
    if not (0 <= day <= 5):
        return None
    timetable_day = []
    j = -1

    for i in range(0, len(timetable)):
        if timetable[i][0] == constants.DAYS_WEEK[day]:
            j = i
    tt = timetable[j][1:]  # расписание на день без дня недели
    tmp_table = []
    # нечетный день
    if week == constants.ODD:
        for i in range(0, len(tt)):
            try:
                cur = tt.pop(0)
            except IndexError:
                break
            if __is_there(cur, *constants.LESSON):
                tmp_table.append(cur)
                try:
                    cur = tt.pop(0)
                except IndexError:
                    break
                tmp_table.append(cur)
                if __is_there(cur, constants.EMPTY, constants.ARMY, *constants.SPORT_TYPES) is False:
                    for m in range(0, 2):
                        try:
                            cur = tt.pop(0)
                        except IndexError:
                            break
                        tmp_table.append(cur)
                timetable_day.append(tmp_table[:])
                tmp_table.clear()
            else:
                continue
    # четный
    if week == constants.EVEN:
        for i in range(0, len(tt)):
            try:
                cur = tt.pop(0)
            except IndexError:
                break
            if __is_there(cur, *constants.LESSON):
                tmp_table.append(cur)
                try:
                    cur = tt.pop(0)
                except IndexError:
                    break
                tmp_table.append(cur)
                if __is_there(cur, constants.EMPTY, constants.ARMY, *constants.SPORT_TYPES) is False:
                    for m in range(0, 2):
                        try:
                            cur = tt.pop(0)
                        except IndexError:
                            break
                        tmp_table.append(cur)
                try:
                    cur = tt.pop(0)
                except IndexError:
                    timetable_day.append(tmp_table[:])
                    break
                if __is_there(cur, *constants.LESSON):
                    timetable_day.append(tmp_table[:])
                    tmp_table.clear()
                    tt.insert(0, cur)
                    continue
                tmp_table = tmp_table[:1]
                while __is_there(cur, *constants.LESSON) is False:
                    tmp_table.append(cur)
                    try:
                        cur = tt.pop(0)
                    except IndexError:
                        break
                tt.insert(0, cur)
                timetable_day.append(tmp_table[:])
                tmp_table.clear()
            else:
                continue

    tmp_table.clear()
    for i in timetable_day:
        if i[1] != constants.EMPTY:
            tmp_table.append(i)

    """    
    # возвращает словарь {'НОМЕР_ЛЕНТЫ': [лента1, имя, ауд]}
    tmp_table = {}
    for i in timetable_day:
        if i[1] != constants.EMPTY:
            tmp_table[i[0]] = [i[x] for x in range(1, len(i))]
        print(i)"""

    if len(tmp_table) > 0:
        return tmp_table
    else:
        return constants.DAYOFF


def __get_request(group):
    request = constants.TIMETABLE_REQUEST + group[0].replace('/', '%2F')

    try:
        """
        
        Сайт СФУ самый лучший. Непонятно откуда у некоторых групп взялись плюсики.
        Поэтому в первом if обрабатываем исключительные группы
        
        """
        if (group[0] == "ВЦ16-03РТВ" and group[1] == "1 подгруппа") or \
                (group[0] == "ВЦ15-03РТВ" and group[1] == "1 подгруппа"):
            request += '+%28+1+подгруппа%29'
            return request

        if group[1] != "":
            request += '+%28' + group[1].replace(' ', '+') + '%29'  # пробуем добавить подгруппу к запросу, если есть
    except IndexError:
        pass
    return request


def __is_there(value, *args):
    """
    
    Возвращает True\False, если элемент есть\нет в списке
    
    """
    
    for i in args:
        if str(i) == str(value):
            return True

    return False

groups = get_groups()
tt = __get_raw_timetable(groups[0])
print(tt)
print(__get_raw_day(tt, day=2, week=constants.EVEN))

"""
groups = get_groups()
#print(__get_raw_day(__get_raw_timetable(groups[0]), day=0, week=constants.ODD))
#print(groups[0])

tt = __get_raw_timetable(groups[0])
print(tt)
tt = __get_raw_day(tt, day=0, week=constants.ODD)
print(tt)

print(get_timetable(groups[0]))
os.system("sleep 10")



write(groups, 'GROUPS')
count = 0
progress_from = 0
progress_cur = 0
progress_to = len(groups) / 100

for i in groups:
    print(str(progress_cur) + '%       (' + str(count) + '/' + str(len(groups)) + ')')
    write(get_timetable(i), i)
    count += 1
    if count >= (progress_to*progress_cur + 1):
        progress_cur += 1
"""