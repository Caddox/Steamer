from re import I
from time import localtime, sleep, asctime
import subprocess as sub

class TimeRange():
    def __init__(self, s_hour, s_min, e_hour, e_min):
        self.start_hour = s_hour
        self.end_hour = e_hour
        self.start_min = s_min
        self.end_min = e_min 

        self.running = False 
        self.passes_day = self.check_if_passes_day()

    def inside_window(self):
        if self.running:
            return not self.has_stopped()

        return self.has_started()
        
    def check_if_passes_day(self):
        if self.start_hour > self.end_hour:
            return True
        return False
    
    def has_started(self):
        tn = localtime()

        if tn.tm_hour >= self.start_hour and \
            tn.tm_min >= self.start_min:
            self.running = True
            return True
        
        return False

    def has_stopped(self):
        tn = localtime()

        if self.passes_day and tn.tm_hour + 23 < self.start_hour + self.end_hour:
            return False

        if tn.tm_hour >= self.end_hour and \
            tn.tm_min >= self.end_min:
            self.running = False
            return True

        return False


class Sentinal():
    def __init__(self):
        self.funcs = {}
        self.times = {}
        self.processess = {}

    def update_state(self):
        for i in self.funcs.keys():
            if self.times[i].inside_window() and i not in self.processess.keys():
                print("[{}] Starting process: {}".format(asctime(), self.funcs[i]))
                s = sub.Popen(self.funcs[i], stdout=sub.PIPE)
                self.processess[i] = s

            if not self.times[i].inside_window() and i in self.processess.keys():
                print("[{}] Terminating process: {}".format(asctime(), self.funcs[i]))
                self.processess[i].terminate()
                del self.processess[i]

    def run_forever(self):
        # Loop over update_state every five seconds forever.
        while 1:
            try:
                sleep(60)
                self.update_state()
            except KeyboardInterrupt:
                print("Shutting Sentinal down. . .")
                self.clear()
                return

    def clear(self):
        for i in self.processess.keys():
            self.processess[i].terminate()

    def tell_running(self):
        for i in self.processess.keys():
            print("`{}` is running".format(self.funcs[i]))

    def delay_subprocess(self, id, time_range, args):
        self.times[id] = time_range
        self.funcs[id] = args
