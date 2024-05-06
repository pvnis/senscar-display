import subprocess

class Statistics:
    
    def __init__(self, interface: str):
        self.interface = interface
        # self.modem_name = modem_name

    def get_ip_address(self):
        cmd_query_ip = f"ip -4 a | grep {self.interface}"
        cmd_query_ip += "| sort | head -n 1 | awk '{ print $2 }' | sed 's/\/..//g'"
        ip_addr = subprocess.check_output(cmd_query_ip, shell=True).decode('ascii')

        # Reset if no IP addr found
        if not "." in ip_addr:
           ip_addr = "n/a" 

        return ip_addr

    def get_modem_state(self):
        modem_state_cmd= "mmcli -m any | grep 'state:' | head -n 1 | awk '{ print $3 }'"
        modem_state = subprocess.check_output(modem_state_cmd, shell=True).decode('ascii').strip()

        if "connected" in modem_state:
            modem_state = "connect."
        elif "attached" in modem_state:
            modem_state = "attatch."
        else:
            print(modem_state, "undefied modem state")
            modem_state = "n/a"
            
        return modem_state

    def get_signal_strength(self):
        connected_state_query="mmcli -m any | grep 'signal' | awk '{ print $4 }' | sed 's/\%//g'"
        signal_strength = subprocess.check_output(connected_state_query, shell=True).decode('ascii').strip()
        
        # Set to 0 if no signal strength found
        if len(signal_strength) == 0:
            signal_strength = "0"

        return signal_strength

    def get_connection_state(self):
        pdu_connection_query="mmcli -m any | grep 'packet' | awk '{ print $5 }' | sed 's/\%//g'"
        pdu_state = subprocess.check_output(pdu_connection_query, shell=True).decode('ascii').strip()
        if pdu_state != "enabled":
            pdu_state = "disabled"

        return pdu_state
        
