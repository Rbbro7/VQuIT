# Change formatting of warnings
class WarningFormat:
    @staticmethod
    def SetCustom(msg, *args, **kwargs):
        # ignore everything except the message
        return "\n\nWarning: " + str(msg) + '\n\n'
