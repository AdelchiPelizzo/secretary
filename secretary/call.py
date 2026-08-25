class Call:

    def __init__(self, call_id, caller_number=None, called_number=None):
        self.call_id = call_id
        self.caller_number = caller_number
        self.called_number = called_number
        self.language = None
        self.messages = []

        self.appointment = {
            "title": None,
            "date": None,
            "time": None,
            "duration_minutes": None
        }

        self.appointment_status = "NONE"