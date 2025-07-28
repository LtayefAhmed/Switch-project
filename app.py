# app.py
from flask import Flask, render_template, request, jsonify
import json
import time
import logging
from datetime import datetime
import os
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cisco_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Keep your original route for backward compatibility
@app.route('/connect', methods=['POST'])
def connect_original():
    """Original connect route for backward compatibility"""
    ip = request.form['ip']
    username = request.form['username']
    password = request.form['password']
    
    # Mock output for testing
    output = f"""
    Switch connection to {ip} was successful!
    
    Port    Name       Status       Vlan
    Gi0/1   AdminPC    connected    10
    Gi0/2   HR-PC      notconnect   20
    Gi0/3   Camera     connected    30
    Gi0/4              err-disabled 1
    """
    
    return f"<h2>Switch Output:</h2><pre>{output}</pre><a href='/'>Back</a>"

@app.route('/test')
def test():
    """Test route"""
    return "Test route is working!"

class Config:
    """Application configuration"""
    def __init__(self):
        self.mock_mode = os.getenv('MOCK_MODE', 'true').lower() == 'true'
        self.switch_ip = os.getenv('SWITCH_IP', '192.168.1.1')
        self.switch_username = os.getenv('SWITCH_USERNAME', 'admin')
        self.switch_password = os.getenv('SWITCH_PASSWORD', 'admin')
        self.ssh_port = int(os.getenv('SSH_PORT', '22'))
        self.connection_timeout = int(os.getenv('CONNECTION_TIMEOUT', '30'))

config = Config()

class MockCiscoSwitch:
    """Mock Cisco switch for testing purposes"""
    
    def __init__(self):
        self.interfaces = {
            'GigabitEthernet0/1': {
                'port_security': True,
                'max_mac_addresses': 2,
                'violation_action': 'shutdown',
                'learned_mac_addresses': ['00:11:22:33:44:55'],
                'status': 'up'
            },
            'GigabitEthernet0/2': {
                'port_security': False,
                'max_mac_addresses': 1,
                'violation_action': 'restrict',
                'learned_mac_addresses': [],
                'status': 'down'
            },
            'GigabitEthernet0/3': {
                'port_security': True,
                'max_mac_addresses': 3,
                'violation_action': 'protect',
                'learned_mac_addresses': ['00:AA:BB:CC:DD:EE', '00:FF:FF:FF:FF:FF'],
                'status': 'up'
            },
            'GigabitEthernet0/4': {
                'port_security': False,
                'max_mac_addresses': 1,
                'violation_action': 'shutdown',
                'learned_mac_addresses': [],
                'status': 'up'
            },
            'GigabitEthernet0/5': {
                'port_security': True,
                'max_mac_addresses': 1,
                'violation_action': 'restrict',
                'learned_mac_addresses': ['00:12:34:56:78:90'],
                'status': 'up'
            }
        }
        self.device_info = {
            'hostname': 'MOCK-CISCO-SWITCH',
            'model': 'WS-C2960-24TT-L',
            'ios_version': '15.0(2)SE11',
            'uptime': '1 day, 2 hours, 30 minutes'
        }
        self.connected = False
    
    def connect(self) -> bool:
        """Simulate connection to switch"""
        time.sleep(1)  # Simulate connection delay
        self.connected = True
        return True
    
    def disconnect(self):
        """Simulate disconnection"""
        time.sleep(0.5)
        self.connected = False
        
    def get_interface_status(self, interface: str) -> Dict:
        """Get port security status for an interface"""
        if interface in self.interfaces:
            return self.interfaces[interface]
        else:
            raise ValueError(f"Interface {interface} not found")
    
    def enable_port_security(self, interface: str, max_mac: int = 1, violation_action: str = 'shutdown') -> str:
        """Enable port security on an interface"""
        if interface not in self.interfaces:
            raise ValueError(f"Interface {interface} not found")
        
        self.interfaces[interface]['port_security'] = True
        self.interfaces[interface]['max_mac_addresses'] = max_mac
        self.interfaces[interface]['violation_action'] = violation_action
        
        return f"Port security enabled on {interface} with max MAC addresses: {max_mac}, violation action: {violation_action}"
    
    def disable_port_security(self, interface: str) -> str:
        """Disable port security on an interface"""
        if interface not in self.interfaces:
            raise ValueError(f"Interface {interface} not found")
        
        self.interfaces[interface]['port_security'] = False
        self.interfaces[interface]['learned_mac_addresses'] = []
        
        return f"Port security disabled on {interface}"
    
    def clear_port_security(self, interface: str) -> str:
        """Clear port security violations"""
        if interface not in self.interfaces:
            raise ValueError(f"Interface {interface} not found")
        
        self.interfaces[interface]['learned_mac_addresses'] = []
        self.interfaces[interface]['status'] = 'up'
        
        return f"Port security cleared on {interface}"
    
    def get_all_interfaces(self) -> List[str]:
        """Get list of all interfaces"""
        return list(self.interfaces.keys())
    
    def get_device_info(self) -> Dict:
        """Get device information"""
        return self.device_info

class CiscoSwitch:
    """Real Cisco switch connection handler"""
    
    def __init__(self, ip: str, username: str, password: str, port: int = 22):
        self.ip = ip
        self.username = username
        self.password = password
        self.port = port
        self.connection = None
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to real Cisco switch via SSH"""
        try:
            from netmiko import ConnectHandler
            
            device = {
                'device_type': 'cisco_ios',
                'ip': self.ip,
                'username': self.username,
                'password': self.password,
                'port': self.port,
                'timeout': config.connection_timeout
            }
            
            self.connection = ConnectHandler(**device)
            self.connected = True
            return True
            
        except ImportError:
            logger.error("netmiko library not installed. Install with: pip install netmiko")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to switch: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from switch"""
        if self.connection:
            self.connection.disconnect()
            self.connection = None
            self.connected = False
    
    def execute_command(self, command: str) -> str:
        """Execute command on switch"""
        if not self.connection:
            raise ConnectionError("Not connected to switch")
        
        try:
            output = self.connection.send_command(command)
            return output
        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            raise
    
    def get_interface_status(self, interface: str) -> Dict:
        """Get port security status for an interface"""
        try:
            command = f"show port-security interface {interface}"
            output = self.execute_command(command)
            
            # Parse the output (simplified parsing - would need more robust parsing in production)
            status = {
                'port_security': 'enabled' in output.lower(),
                'max_mac_addresses': 1,  # Default, would parse from output
                'violation_action': 'shutdown',  # Default, would parse from output
                'learned_mac_addresses': [],  # Would parse from output
                'status': 'up' if 'up' in output.lower() else 'down'
            }
            
            return status
        except Exception as e:
            logger.error(f"Failed to get interface status: {str(e)}")
            raise
    
    def enable_port_security(self, interface: str, max_mac: int = 1, violation_action: str = 'shutdown') -> str:
        """Enable port security on an interface"""
        try:
            commands = [
                f"interface {interface}",
                "switchport port-security",
                f"switchport port-security maximum {max_mac}",
                f"switchport port-security violation {violation_action}",
                "exit"
            ]
            
            config_commands = self.connection.send_config_set(commands)
            return f"Port security enabled on {interface}"
        except Exception as e:
            logger.error(f"Failed to enable port security: {str(e)}")
            raise
    
    def disable_port_security(self, interface: str) -> str:
        """Disable port security on an interface"""
        try:
            commands = [
                f"interface {interface}",
                "no switchport port-security",
                "exit"
            ]
            
            config_commands = self.connection.send_config_set(commands)
            return f"Port security disabled on {interface}"
        except Exception as e:
            logger.error(f"Failed to disable port security: {str(e)}")
            raise
    
    def clear_port_security(self, interface: str) -> str:
        """Clear port security violations"""
        try:
            command = f"clear port-security sticky interface {interface}"
            self.execute_command(command)
            return f"Port security cleared on {interface}"
        except Exception as e:
            logger.error(f"Failed to clear port security: {str(e)}")
            raise
    
    def get_all_interfaces(self) -> List[str]:
        """Get list of all interfaces from real switch"""
        try:
            command = "show interfaces status"
            output = self.execute_command(command)
            
            # Parse interface names from output
            interfaces = []
            lines = output.split('\n')
            for line in lines:
                if 'GigabitEthernet' in line or 'FastEthernet' in line:
                    interface_name = line.split()[0]
                    interfaces.append(interface_name)
            
            return interfaces if interfaces else ['GigabitEthernet0/1', 'GigabitEthernet0/2', 'GigabitEthernet0/3']
        except Exception as e:
            logger.error(f"Failed to get interfaces: {str(e)}")
            # Return default interfaces on error
            return ['GigabitEthernet0/1', 'GigabitEthernet0/2', 'GigabitEthernet0/3']

class SwitchManager:
    """Manager class to handle both mock and real switch operations"""
    
    def __init__(self):
        self.switch = None
        self.connected = False
        self.logs = []
        self.current_credentials = None
    
    def add_log(self, message: str, level: str = "INFO"):
        """Add log entry"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message
        }
        self.logs.append(log_entry)
        logger.info(f"[{level}] {message}")
        
        # Keep only last 100 logs
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]
    
    def connect(self, ip: str = None, username: str = None, password: str = None) -> Tuple[bool, str]:
        """Connect to switch (mock or real)"""
        try:
            # Use provided credentials or fall back to config
            switch_ip = ip or config.switch_ip
            switch_username = username or config.switch_username
            switch_password = password or config.switch_password
            
            if config.mock_mode:
                self.switch = MockCiscoSwitch()
                self.add_log("Using mock mode for testing")
            else:
                self.switch = CiscoSwitch(
                    switch_ip,
                    switch_username,
                    switch_password,
                    config.ssh_port
                )
                self.add_log(f"Connecting to real switch at {switch_ip}")
            
            if self.switch.connect():
                self.connected = True
                self.current_credentials = {
                    'ip': switch_ip,
                    'username': switch_username,
                    'password': switch_password
                }
                self.add_log("Successfully connected to switch")
                return True, "Connected successfully"
            else:
                self.add_log("Failed to connect to switch", "ERROR")
                return False, "Connection failed"
                
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            self.add_log(error_msg, "ERROR")
            return False, error_msg
    
    def disconnect(self):
        """Disconnect from switch"""
        if self.switch:
            self.switch.disconnect()
            self.connected = False
            self.current_credentials = None
            self.add_log("Disconnected from switch")
    
    def execute_port_security_action(self, interface: str, action: str, **kwargs) -> Tuple[bool, str]:
        """Execute port security action"""
        if not self.connected:
            return False, "Not connected to switch"
        
        try:
            if action == "enable":
                max_mac = kwargs.get('max_mac', 1)
                violation_action = kwargs.get('violation_action', 'shutdown')
                result = self.switch.enable_port_security(interface, max_mac, violation_action)
                self.add_log(f"Enabled port security on {interface}")
                
            elif action == "disable":
                result = self.switch.disable_port_security(interface)
                self.add_log(f"Disabled port security on {interface}")
                
            elif action == "clear":
                result = self.switch.clear_port_security(interface)
                self.add_log(f"Cleared port security on {interface}")
                
            elif action == "status":
                status = self.switch.get_interface_status(interface)
                result = f"Port security status for {interface}:\n{json.dumps(status, indent=2)}"
                self.add_log(f"Retrieved status for {interface}")
                
            else:
                return False, f"Unknown action: {action}"
            
            return True, result
            
        except Exception as e:
            error_msg = f"Action failed: {str(e)}"
            self.add_log(error_msg, "ERROR")
            return False, error_msg

# Global switch manager instance
switch_manager = SwitchManager()

@app.route('/')
def index():
    """Main page - serve the HTML file directly"""
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify({
        'mock_mode': config.mock_mode,
        'switch_ip': config.switch_ip,
        'connected': switch_manager.connected
    })

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    data = request.json
    
    if 'mock_mode' in data:
        config.mock_mode = data['mock_mode']
        switch_manager.add_log(f"Switched to {'mock' if config.mock_mode else 'real'} mode")
        # Disconnect if mode changed
        if switch_manager.connected:
            switch_manager.disconnect()
    
    if 'switch_ip' in data:
        config.switch_ip = data['switch_ip']
        switch_manager.add_log(f"Updated switch IP to {config.switch_ip}")
    
    return jsonify({'status': 'success'})

@app.route('/api/connect', methods=['POST'])
def connect():
    """Connect to switch using config settings"""
    success, message = switch_manager.connect()
    return jsonify({
        'success': success,
        'message': message,
        'connected': switch_manager.connected
    })

@app.route('/api/legacy-connect', methods=['POST'])
def legacy_connect():
    """Connect to switch using provided credentials (Legacy Form)"""
    data = request.json
    
    ip = data.get('ip')
    username = data.get('username')
    password = data.get('password')
    
    if not ip or not username or not password:
        return jsonify({
            'success': False,
            'message': 'IP, username, and password are required'
        }), 400
    
    # Temporarily store original mode
    original_mode = config.mock_mode
    
    # For legacy connection, force real mode
    config.mock_mode = False
    
    success, message = switch_manager.connect(ip, username, password)
    
    if success:
        # Generate a detailed output for legacy form
        try:
            if hasattr(switch_manager.switch, 'get_all_interfaces'):
                interfaces = switch_manager.switch.get_all_interfaces()
                interface_status = []
                
                for interface in interfaces[:5]:  # Limit to first 5 interfaces
                    try:
                        status = switch_manager.switch.get_interface_status(interface)
                        interface_status.append(f"{interface}: {'Enabled' if status['port_security'] else 'Disabled'}")
                    except:
                        interface_status.append(f"{interface}: Status unknown")
                
                output = f"""Connection to {ip} successful!

Switch Information:
- IP Address: {ip}
- Username: {username}
- Mode: {'Mock' if config.mock_mode else 'Real'}

Port Security Status:
{chr(10).join(interface_status)}

Connection established successfully. You can now use the port security actions above."""
            else:
                output = f"Connection to {ip} successful!\n\nSwitch is ready for port security management."
                
        except Exception as e:
            output = f"Connection to {ip} successful!\n\nNote: Could not retrieve detailed status: {str(e)}"
        
        return jsonify({
            'success': True,
            'message': message,
            'output': output,
            'connected': switch_manager.connected
        })
    else:
        # Restore original mode on failure
        config.mock_mode = original_mode
        return jsonify({
            'success': False,
            'message': message
        })

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from switch"""
    switch_manager.disconnect()
    return jsonify({
        'success': True,
        'message': 'Disconnected',
        'connected': switch_manager.connected
    })

@app.route('/api/interfaces', methods=['GET'])
def get_interfaces():
    """Get available interfaces"""
    if not switch_manager.connected:
        return jsonify({'error': 'Not connected to switch'}), 400
    
    try:
        if hasattr(switch_manager.switch, 'get_all_interfaces'):
            interfaces = switch_manager.switch.get_all_interfaces()
        else:
            # Default interfaces for real switch
            interfaces = ['GigabitEthernet0/1', 'GigabitEthernet0/2', 'GigabitEthernet0/3']
        
        return jsonify({'interfaces': interfaces})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/port-security', methods=['POST'])
def port_security_action():
    """Execute port security action"""
    data = request.json
    
    interface = data.get('interface')
    action = data.get('action')
    
    if not interface or not action:
        return jsonify({'error': 'Interface and action are required'}), 400
    
    # Additional parameters for enable action
    kwargs = {}
    if action == 'enable':
        kwargs['max_mac'] = data.get('max_mac', 1)
        kwargs['violation_action'] = data.get('violation_action', 'shutdown')
    
    success, result = switch_manager.execute_port_security_action(interface, action, **kwargs)
    
    return jsonify({
        'success': success,
        'result': result,
        'interface': interface,
        'action': action
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get application logs"""
    return jsonify({'logs': switch_manager.logs[-50:]})  # Return last 50 logs

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    """Clear application logs"""
    switch_manager.logs = []
    switch_manager.add_log("Logs cleared")
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)