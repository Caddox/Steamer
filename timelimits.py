from time import localtime, sleep, asctime

class TimeRange():
    '''
    Class: TimeRange
    Purpose: Given a start time and an endtime, find if the system time is within the window.
    '''
    def __init__(self, s_hour: int , s_min: int, e_hour: int, e_min: int):
        '''
        Class constructor.
        '''
        self.start_hour = s_hour
        self.end_hour = e_hour
        self.start_min = s_min
        self.end_min = e_min 

        self.running = False 
        self.passes_day = self._check_if_passes_day()

    def inside_window(self) -> bool:
        '''
        Class method. Report if the current time falls within the given window.
        '''
        if self.running:
            return not self._has_stopped()

        return self._has_started()
        
    def _check_if_passes_day(self) -> bool:
        '''
        Class method (Private). Returns true if the window's duration will go past midnight into a new day
        '''
        if self.start_hour > self.end_hour:
            return True
        return False
    
    def _has_started(self) -> bool:
        '''
        Class method (Private). Returns True if the current time has entered the window.
        '''
        tn = localtime()

        if tn.tm_hour >= self.start_hour and \
            tn.tm_min >= self.start_min:
            self.running = True
            return True
        
        return False

    def _has_stopped(self) -> bool:
        '''
        Class method (private): Returns True if the current time is outside of the window
        '''
        tn = localtime()

        if self.passes_day and tn.tm_hour + 23 < self.start_hour + self.end_hour:
            return False

        if tn.tm_hour >= self.end_hour and \
            tn.tm_min >= self.end_min:
            self.running = False
            return True

        return False
