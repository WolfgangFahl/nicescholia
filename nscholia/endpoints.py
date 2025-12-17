from snapquery.snapquery_core import NamedQueryManager


class Endpoints:
    def __init__(self):
        self.nqm = NamedQueryManager.from_samples()

    def get_endpoints(self):
        """
        list all endpoints
        """
        endpoints = self.nqm.endpoints
        return endpoints
