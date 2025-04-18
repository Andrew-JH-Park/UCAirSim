
class UTM:
    def __init__(self, network):
        self.network = network

    def check_airspace_capacity(self, origin, destination):
        self.network.airspaces[origin, destination] # check
        return 0

    def check_space_separation(self):
        return 0

    def check_vertiport_viscinity_capacity(self):
        return 0
