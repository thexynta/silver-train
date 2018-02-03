from datetime import datetime

logs_filename = 'bot' + \
                str(datetime.today().timetuple().tm_hour) + '_' + str(datetime.today().timetuple().tm_min) + '_' + \
                str(datetime.today().timetuple().tm_mday) + '_' + str(datetime.today().timetuple().tm_mon) + '_' + \
                str(datetime.today().timetuple().tm_year) + '.log'