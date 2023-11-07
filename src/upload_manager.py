from datetime import datetime


class UploadManager:




    def upload(self, force_multithread=False, force_singlethread=True):

        start = datetime.now()

        if force_multithread and force_singlethread:
            raise