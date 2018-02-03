#!/usr/bin/python3

import constants
import SibFUTimetableParser as tt
import sqlite3
import os
from crontab import CronTab

groups = tt.read(constants.GROUPS_FILENAME)

conn = sqlite3.connect(constants.SQLITE_FILENAME)
cursor = conn.cursor()

cursor.execute("SELECT `user_id`, `group`, `time` FROM users WHERE `user_id` != '' AND `group` != ''")
jobs = cursor.fetchall()  # job[][0] - user_id, job[][1] - group
for i in jobs:
    time = int(i[2])
    if time == -1:
        try:
            cursor.execute("UPDATE users SET `alarm` = :time WHERE `user_id` = :user_id",
                           {"user_id": i[0],
                            "time": time})
        except Exception as e:
            print(e)
            pass
    else:
        first_lesson = tt.get_raw_day(i[1])[0][0]
        first_lesson_time = {'hours': constants.LESSON_TIME.get(first_lesson)[0:2],
                             'minutes': constants.LESSON_TIME.get(first_lesson)[3:5]}
        first_lesson_time['hours'] = int(first_lesson_time['hours']) - (time // 60)
        time -= (time // 60) * 60
        if int(first_lesson_time['minutes']) < time:
            first_lesson_time['hours'] = int(first_lesson_time['hours']) - 1
            first_lesson_time['minutes'] = 60 - (time - int(first_lesson_time['minutes']))
        else:
            first_lesson_time['minutes'] = int(first_lesson_time['minutes']) - time
        try:
            cursor.execute("UPDATE users SET `alarm` = :time WHERE `user_id` = :user_id",
                           {"user_id": i[0],
                            "time": str(first_lesson_time['hours']) + ':' + str(first_lesson_time['minutes'])})
        except Exception as e:
            print(e)
            pass
    conn.commit()

cursor.execute("SELECT `alarm` FROM users GROUP BY (`alarm`)")
jobs = cursor.fetchall()
cron = CronTab(user=True)
# удаляем старые задачи
old_jobs = cron.find_command('cron_exec.sh')
for i in old_jobs:
    cron.remove(i)
# добавляем новые
for i in jobs:
    i = i[0]
    if i != '-1':
        job = cron.new(command=os.getcwd() + '/cron_exec.sh ' + i.split(':')[0] + ' ' + i.split(':')[1])
        job.hours.on(i.split(':')[0])
        job.minutes.on(i.split(':')[1])
cron.write()
