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
        tmp = [[], []]
        try:
            tmp[0], tmp[1] = i.replace('\xa0', ' ').replace(' (', ' ((').split(' (', maxsplit=1)
        except ValueError:
            tmp[0], tmp[1] = i.replace('\xa0', ' '), ''
        groups.append(tmp[:])

    return groups


def get_week():
    week_number = datetime.datetime.today().isocalendar()[1]
    return constants.EVEN if week_number % 2 == 0 else constants.ODD


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
    filename = ""
    for i in group:
        filename += i

    return filename.replace(' ', '').replace('/', '').replace('-', '').replace(')', '').replace('(', '').upper()


def __is_there(value, *args):
    """

    Возвращает True\False, если элемент есть\нет в списке

    """

    for i in args:
        if str(i) == str(value):
            return True

    return False


def __get_request(group):

    """

    Принимает список в виде [str: ГРУППА, str: ПОДГРУППА]

    Сайт СФУ самый лучший. Непонятно откуда у некоторых групп взялись плюсики.
    Поэтому в первом if обрабатываем исключительные группы

    """
    # ВЦ16-03РТВ (1 подгруппа)
    # ВЦ15-03РТВ (1 подгруппа)
    # +1+подгруппа

    if not isinstance(group, list):
        return None

    exceptions = ['ВЦ16-03РТВ (1 подгруппа)', 'ВЦ15-03РТВ (1 подгруппа)']
    request = constants.TIMETABLE_REQUEST + group[0].replace('/', '%2F')

    tmp = group[0]
    try:
        tmp += ' ' + group[1]
    except IndexError:
        pass
    group = tmp

    if __is_there(group, *exceptions):
        if group in exceptions[0]:  # ВЦ16-03РТВ (1 подгруппа)
            return constants.TIMETABLE_REQUEST + 'ВЦ16-03РТВ+%28+1+подгруппа%29'
        elif group in exceptions[0]:  # ВЦ15-03РТВ (1 подгруппа)
            return constants.TIMETABLE_REQUEST + 'ВЦ15-03РТВ+%28+1+подгруппа%29'

    return constants.TIMETABLE_REQUEST +\
           group.replace('/', '%2F').replace('(', '%28').replace(' ', '+').replace(')', '%29')


def __get_raw_timetable(group):
    """

    timetable[i][0] - День недели,'№', номер занятия
    timetable[N][2][i] - (нечетная) Название, тип, преподаватель, кабинет,
                            где N такой, что timetable[N][0] - номер занятия.
    timetable[N][3][i] - (четная) Название, тип, преподаватель, кабинет, где N такой,
                            что timetable[N][0] - номер занятия.
                            Если IndexError, то одно и тоже занятие каждую неделю.

    Возвращает список, в котором можно получить любой элемент по индексу.
    timetable[Нечетная/Четная неделя(0-1)][День недели, пн-сб(0-5)][лента(0-6)]

    """
    page = requests.get(__get_request(group))
    tree = html.fromstring(page.content)
    raw_timetable = tree.xpath("//table[@class=\"table timetable\"]/*")
    raw_timetable.append('Воскресенье')  # Для правильной работы алгоритма
    timetable_final = [[], []]
    tmp_tt_odd = []
    tmp_tt_even = []
    tmp = [[], []]
    for i in raw_timetable:
        try:
            current = i[0].text_content()
        except AttributeError:
            current = i
        if __is_there(current, *constants.DAYS_WEEK) and current != 'Понедельник':
            # Нечетная неделя
            if len(tmp_tt_odd) == 0:
                timetable_final[0].append(constants.DAYOFF)
            else:
                timetable_final[0].append(tmp[0][:])
            # Четная неделя
            if len(tmp_tt_even) == 0:
                timetable_final[1].append(constants.DAYOFF)
            else:
                timetable_final[1].append(tmp[1][:])

            tmp = [[], []]
            continue

        if __is_there(current, *constants.LESSON):
            tmp_tt_odd = []
            tmp_tt_even = []
            tmp_tt_odd.append(current)  # добавляем номер занятия в начало
            tmp_tt_even.append(current) #

            if i[2].text_content() != '':  # занятие на нечетной неделе
                for j in i[2]:
                    if j.text_content() != '':
                        tmp_tt_odd.append(j.text_content())
                    if j.tail is not None:  # в tail хранится тип занятия или None
                        tmp_tt_odd.append(j.tail[1:])  # первый символ пробел
            else:
                tmp_tt_odd.append(constants.EMPTY)

            try:
                if i[3].text_content() != '': # занятие на четной неделе
                    for j in i[3]:
                        if j.text_content() != '':
                            tmp_tt_even.append(j.text_content())
                        if j.tail is not None:  # в tail хранится тип занятия или None
                            tmp_tt_even.append(j.tail[1:])  # первый символ пробел
                else:
                    tmp_tt_even.append(constants.EMPTY)
            except IndexError: # если i[3] не существует, значит занятие на четной такое же, как и на нечетной
                for j in i[2]:
                    if j.text_content() != '':
                        tmp_tt_even.append(j.text_content())
                    if j.tail is not None:  # в tail хранится тип занятия или None
                        tmp_tt_even.append(j.tail[1:])  # первый символ пробел
            tmp[0].append(tmp_tt_odd[:])
            tmp[1].append(tmp_tt_even[:])

    return timetable_final


def get_raw_day(group, day=datetime.datetime.today().weekday(), week=get_week(), local=True):
    if local:
        timetable = read(group)
    elif local is False:
        timetable = __get_raw_timetable(group)
    else:
        return None

    try:
        return timetable[week][day]
    except IndexError:
        return None


def __save_timetables_local():
    """

    Моя функция личная. Что хочу, то и делаю

    """
    groups = get_groups()
    write(groups, 'GROUPS')
    count = 0
    progress_cur = 0
    progress_to = len(groups) / 100

    try:
        for i in groups:
            write(__get_raw_timetable(i), i)
            count += 1
            if count > (progress_to*progress_cur + 1):
                progress_cur += 1
            print(str(progress_cur) + '%       (' + str(count) + '/' + str(len(groups)) + ')')
    except Exception:
        return False

    return True
