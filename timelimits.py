from time import localtime, sleep, asctime
from functools import total_ordering


@total_ordering
class Time:
    def __init__(self, hour, min):
        self.hour = hour
        self.min = min

    def __eq__(self, other):
        return (self.hour, self.min) == (other.hour, other.min)

    def __lt__(self, other):
        return (self.hour, self.min) < (other.hour, other.min)


class TimeRange:
    def __init__(self, s_hour: int, s_min: int, e_hour: int, e_min: int):
        """
        Class constructor.
        """
        self.start_time = Time(s_hour, s_min)
        self.end_time = Time(e_hour, e_min)
        self.passes_night = False
        if self.end_time < self.start_time:
            self.passes_night = True

    def inside_window(self):
        tn = localtime()
        current_time = Time(tn.tm_hour, tn.tm_min)

        if self.passes_night:
            # make a section checking for before midnight and for after midnight
            if current_time <= Time(23, 59) and current_time >= self.start_time:
                return True
            else:
                if current_time >= Time(00, 00) and current_time <= self.end_time:
                    return True

            return False
        else:
            if current_time <= self.end_time and current_time >= self.start_time:
                return True
            else:
                return False

        return False  # should never reach this
