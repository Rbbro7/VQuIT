# Change formatting of warnings
class WarningFormat:
    @staticmethod
    def SetCustom(msg, *args, **kwargs):
        # ignore everything except the message
        return "\n\nWarning: " + str(msg) + '\n\n'


class OpenFile:
    subprocess = None
    sys = None

    def ImportSubprocess(self):
        if self.subprocess is None:
            import subprocess
            self.subprocess = subprocess
        return self.subprocess

    def ImportSys(self):
        if self.sys is None:
            import sys
            self.sys = sys
        return self.sys

    # Copied from the internet to open files in default program
    def DefaultProgram(self, file):
        subprocess = self.ImportSubprocess()
        ret_code = subprocess.call(['start', file], shell=True)
        return ret_code

    # Copied from the internet to open image in default program
    def openImage(self, path):
        subprocess = self.ImportSubprocess()
        sys = self.ImportSys()

        imageViewerFromCommandLine = {'linux': 'xdg-open',
                                      'win32': 'explorer',
                                      'darwin': 'open'}[sys.platform]
        subprocess.run([imageViewerFromCommandLine, path])
