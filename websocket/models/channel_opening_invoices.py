
class ChannelOpeningInvoices(object):
    def __init__(self):
        # Todo: populate invoice packages from disk as well
        self.packages = {}

    def add_invoice_package(self, r_hash: str, package):
        self.packages[r_hash] = package

    def get_invoice_package(self, r_hash: str):
        channel_opening_data = self.packages.get(r_hash, None)
        return channel_opening_data
