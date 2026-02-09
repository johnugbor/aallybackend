import obd

class VehicleInterface:
    def __init__(self, demo_mode=True):
        self.demo_mode = demo_mode
        self.connection = None if demo_mode else obd.OBD()

    def get_data(self):
        if self.demo_mode:
            return {"dtc": "P0303", "desc": "Cylinder 3 Misfire", "make": "Ford", "model": "Mustang"}
        
        # Real OBD Logic
        if self.connection and self.connection.is_connected():
            dtc = self.connection.query(obd.commands.GET_DTC).value
            return {"dtc": dtc[0][0] if dtc else "None", "make": "Unknown", "model": "Unknown"}
        return {"error": "Not Connected"}

vehicle_bridge = VehicleInterface(demo_mode=True)