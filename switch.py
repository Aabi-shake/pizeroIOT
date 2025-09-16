#!/usr/bin/env python3
"""
Simple Tkinter GUI for controlling TP-Link Kasa smart home devices.
Requires: pip install python-kasa
"""

import asyncio
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import os
from kasa import Discover


class KasaDeviceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🏠 Kasa Smart Home Controller")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')

        # Modern color scheme
        self.colors = {
            'primary': '#2c3e50',
            'secondary': '#3498db',
            'success': '#27ae60',
            'danger': '#e74c3c',
            'warning': '#f39c12',
            'light': '#ecf0f1',
            'dark': '#34495e',
            'background': '#f8f9fa'
        }

        # Configure modern styling
        self._configure_styles()
        
        # Store discovered devices
        self.devices = {}
        self.credentials = self._load_credentials_from_env()
        
        # Create a persistent event loop for async operations
        self.loop = None
        self.loop_thread = None
        self._start_event_loop()
        
        # Create GUI elements
        self.setup_gui()

    def _configure_styles(self):
        """Configure modern TTK styles"""
        style = ttk.Style()

        # Use default button styling for better visibility

        # Configure frame styles
        style.configure('Card.TFrame',
                       background='white',
                       relief='solid',
                       borderwidth=1)

        # Configure labels with proper contrast
        style.configure('Title.TLabel',
                       background='white',
                       foreground=self.colors['primary'],
                       font=('Segoe UI', 18, 'bold'))

        style.configure('Stats.TLabel',
                       background='white',
                       font=('Segoe UI', 10, 'bold'))

        style.configure('StatsValue.TLabel',
                       background='white',
                       font=('Segoe UI', 16, 'bold'))

        style.configure('Status.TLabel',
                       background='white',
                       foreground=self.colors['dark'],
                       font=('Segoe UI', 10))

        # Configure treeview with better contrast
        style.configure('Modern.Treeview',
                       background='white',
                       foreground='black',
                       fieldbackground='white',
                       font=('Segoe UI', 10),
                       rowheight=25)

        style.configure('Modern.Treeview.Heading',
                       background=self.colors['light'],
                       foreground=self.colors['primary'],
                       font=('Segoe UI', 10, 'bold'),
                       relief='solid',
                       borderwidth=1)

        # Configure treeview selection colors
        style.map('Modern.Treeview',
                  background=[('selected', self.colors['secondary'])],
                  foreground=[('selected', 'white')])

        # Configure tag styles for colored rows
        self.tree_tags = {
            'online': {'foreground': self.colors['success'], 'font': ('Segoe UI', 10, 'bold')},
            'offline': {'foreground': self.colors['danger'], 'font': ('Segoe UI', 10)},
            'unknown': {'foreground': '#7f8c8d', 'font': ('Segoe UI', 10)}
        }

    def _load_credentials_from_env(self):
        """Load credentials from .env file"""
        credentials = {"username": "", "password": ""}

        env_file = ".env"
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")

                                if key == "KASA_USERNAME":
                                    credentials["username"] = value
                                elif key == "KASA_PASSWORD":
                                    credentials["password"] = value
                print(f"Loaded credentials from {env_file}: username={'*' * len(credentials['username']) if credentials['username'] else 'not set'}")
            except Exception as e:
                print(f"Error reading {env_file}: {e}")
        else:
            print(f"No {env_file} file found. Create one with KASA_USERNAME and KASA_PASSWORD if needed.")

        return credentials
    
    def setup_gui(self):
        """Setup the main GUI interface"""

        # Main frame
        main_frame = ttk.Frame(self.root, padding="20", style='Card.TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # Header with title and search
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        header_frame.columnconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(header_frame, text="⚡ Smart Devices",
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, sticky=tk.W)

        # Search frame
        search_frame = ttk.Frame(header_frame)
        search_frame.grid(row=0, column=1, sticky=tk.E, padx=(20, 0))

        ttk.Label(search_frame, text="🔎", font=('Segoe UI', 12)).grid(row=0, column=0, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20, font=('Segoe UI', 10))
        search_entry.grid(row=0, column=1)
        search_entry.insert(0, "Search devices...")
        # Add trace after GUI is fully initialized
        self.search_var.trace('w', self.on_search_changed)
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        # Primary actions (left side)
        primary_frame = ttk.Frame(control_frame)
        primary_frame.grid(row=0, column=0, sticky=tk.W)

        ttk.Button(primary_frame, text="🔄 Discover",
                  command=self.discover_devices).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(primary_frame, text="➕ Add Device",
                  command=self.manual_add_device).grid(row=0, column=1, padx=(0, 20))

        # Device controls (right side)
        device_control_frame = ttk.Frame(control_frame)
        device_control_frame.grid(row=0, column=1, sticky=tk.E)

        ttk.Button(device_control_frame, text="🟢 All ON",
                  command=self.turn_all_on).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(device_control_frame, text="⚫ All OFF",
                  command=self.turn_all_off).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(device_control_frame, text="↻ Refresh",
                  command=self.refresh_status).grid(row=0, column=2)

        # Configure grid weights for button alignment
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=0)
        
        # Statistics frame
        stats_frame = ttk.Frame(main_frame)
        stats_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        self.stats_labels = {}
        stats_data = [
            ("📱 Total", "total", self.colors['primary']),
            ("🟢 Online", "online", self.colors['success']),
            ("⚫ Offline", "offline", self.colors['danger']),
            ("⚡ Active", "active", self.colors['warning'])
        ]

        for i, (text, key, color) in enumerate(stats_data):
            frame = ttk.Frame(stats_frame)
            frame.grid(row=0, column=i, padx=(0, 20) if i < len(stats_data)-1 else 0)

            label = ttk.Label(frame, text=text, style='Stats.TLabel')
            label.configure(foreground=color)
            label.grid(row=0, column=0)

            self.stats_labels[key] = ttk.Label(frame, text="0", style='StatsValue.TLabel')
            self.stats_labels[key].configure(foreground=color)
            self.stats_labels[key].grid(row=1, column=0)

        # Devices frame with scrollbar
        devices_frame = ttk.LabelFrame(main_frame, text="📋 Devices", padding="15",
                                     style='Card.TFrame')
        devices_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        devices_frame.columnconfigure(0, weight=1)
        devices_frame.rowconfigure(0, weight=1)

        # Create simplified treeview for devices
        columns = ("Device", "Status", "Control")
        self.tree = ttk.Treeview(devices_frame, columns=columns, show="headings",
                               height=12, style='Modern.Treeview')

        # Configure column headings and widths
        self.tree.heading("Device", text="Device")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Control", text="Control")

        self.tree.column("Device", width=400)
        self.tree.column("Status", width=120, anchor=tk.CENTER)
        self.tree.column("Control", width=80, anchor=tk.CENTER)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(devices_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid the treeview and scrollbar
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Configure treeview tags for colored text
        self.tree.tag_configure('online', foreground=self.colors['success'], font=('Segoe UI', 10, 'bold'))
        self.tree.tag_configure('offline', foreground=self.colors['danger'], font=('Segoe UI', 10))
        self.tree.tag_configure('unknown', foreground='#7f8c8d', font=('Segoe UI', 10))

        # Bind double-click to toggle device
        self.tree.bind("<Double-1>", self.on_device_double_click)
        
        # Status bar with modern styling
        status_frame = ttk.Frame(main_frame, style='Card.TFrame')
        status_frame.grid(row=4, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(1, weight=1)

        ttk.Label(status_frame, text="📶", style='Status.TLabel').grid(row=0, column=0, padx=(10, 5), pady=8)
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Click 'Discover' to find your devices")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, style='Status.TLabel')
        status_label.grid(row=0, column=1, sticky=tk.W, pady=8)

    def on_search_changed(self, *args):
        """Filter devices based on search input"""
        # Check if tree widget exists yet
        if not hasattr(self, 'tree'):
            return

        search_term = self.search_var.get().lower()
        if search_term == "search devices...":
            search_term = ""

        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if values:
                device_text = ' '.join(str(v).lower() for v in values)
                if search_term in device_text:
                    self.tree.reattach(item, '', 'end')
                else:
                    self.tree.detach(item)

    def update_statistics(self):
        """Update device statistics display"""
        # Check if stats_labels exists yet
        if not hasattr(self, 'stats_labels'):
            return

        total = len(self.devices)
        online = 0
        offline = 0
        active = 0

        for device in self.devices.values():
            try:
                # Check if device is available (online)
                is_available = True  # Default to available
                if hasattr(device, 'is_available'):
                    is_available = device.is_available
                elif hasattr(device, 'available'):
                    is_available = device.available

                if is_available:
                    online += 1
                else:
                    offline += 1

                # Check if device is active (turned on)
                if hasattr(device, 'is_on') and device.is_on:
                    active += 1

            except Exception as e:
                print(f"Error checking device status: {e}")
                offline += 1  # Count as offline if we can't check status

        # If we couldn't determine online/offline status, assume all are online
        if online == 0 and offline == 0 and total > 0:
            online = total

        self.stats_labels['total'].config(text=str(total))
        self.stats_labels['online'].config(text=str(online))
        self.stats_labels['offline'].config(text=str(offline))
        self.stats_labels['active'].config(text=str(active))

    def get_device_icon(self, device):
        """Get appropriate icon for device type"""
        if hasattr(device, 'device_type'):
            device_type = str(device.device_type).lower()
            if 'plug' in device_type:
                return '🔌'
            elif 'bulb' in device_type or 'light' in device_type:
                return '💡'
            elif 'switch' in device_type:
                return '⚡'
            elif 'strip' in device_type:
                return '🔗'
        return '📱'

    def get_status_display(self, device):
        """Get visual status display for device"""
        try:
            if device.is_on:
                return "🟢 ON"
            else:
                return "⚫ OFF"
        except (AttributeError, Exception):
            return "⚪ Unknown"

    def manual_add_device(self):
        """Manually add a device by IP address"""
        ip = simpledialog.askstring("Manual Device", "Enter device IP address:")
        if ip:
            self.run_async(self._manual_add_device(ip))
    
    async def _manual_add_device(self, ip):
        """Async method to manually add a device"""
        try:
            from kasa import Discover
            self.status_var.set(f"Connecting to device at {ip}...")
            
            # Try to discover single device
            if self.credentials["username"] and self.credentials["password"]:
                device = await Discover.discover_single(
                    ip, 
                    username=self.credentials["username"],
                    password=self.credentials["password"],
                    timeout=10
                )
            else:
                device = await Discover.discover_single(ip, timeout=10)
            
            if device:
                # Test connectivity
                await asyncio.wait_for(device.update(), timeout=10)
                self.devices[ip] = device
                self.update_device_list()
                self.status_var.set(f"Successfully added device: {getattr(device, 'alias', ip)}")
            else:
                self.status_var.set(f"No device found at {ip}")
                
        except Exception as e:
            error_msg = f"Failed to add device at {ip}: {type(e).__name__} - {str(e)}"
            self.status_var.set(error_msg)
            print(error_msg)
            messagebox.showerror("Add Device Error", f"Failed to add device at {ip}:\n{str(e)}")
    
    
    def _start_event_loop(self):
        """Start a persistent event loop in a separate thread"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        self.loop_thread = threading.Thread(target=run_loop)
        self.loop_thread.daemon = True
        self.loop_thread.start()
        
        # Wait for loop to be ready
        import time
        while self.loop is None:
            time.sleep(0.01)
    
    def run_async(self, coro):
        """Run async coroutine using the persistent event loop"""
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(coro, self.loop)
        else:
            print("Event loop not available")
    
    def cleanup(self):
        """Clean up the event loop when closing"""
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.loop.stop)
    
    async def _discover_devices(self):
        """Async method to discover devices"""
        try:
            self.status_var.set("Discovering devices...")
            self.root.update()
            
            # Discover devices with timeout and error handling
            if self.credentials["username"] and self.credentials["password"]:
                devices = await Discover.discover(
                    username=self.credentials["username"],
                    password=self.credentials["password"],
                    timeout=10,
                    discovery_timeout=5
                )
            else:
                devices = await Discover.discover(
                    timeout=10,
                    discovery_timeout=5
                )
            
            # Filter out problematic devices and update them safely
            working_devices = {}
            for ip, device in devices.items():
                try:
                    # Try to update the device to test connectivity
                    await asyncio.wait_for(device.update(), timeout=15)
                    working_devices[ip] = device
                    print(f"Successfully connected to device at {ip}: {getattr(device, 'alias', 'Unknown')}")
                except Exception as e:
                    print(f"Skipping problematic device at {ip}: {type(e).__name__} - {str(e)}")
                    continue
            
            self.devices = working_devices
            self.update_device_list()
            
            if working_devices:
                self.status_var.set(f"Found {len(working_devices)} working device(s)")
            else:
                self.status_var.set("No working devices found. Check network connection or try setting credentials.")
            
        except Exception as e:
            self.status_var.set(f"Discovery failed: {str(e)}")
            print(f"Discovery error: {type(e).__name__} - {str(e)}")
            messagebox.showerror("Discovery Error", f"Failed to discover devices:\n{str(e)}")
    
    def discover_devices(self):
        """Start device discovery"""
        self.run_async(self._discover_devices())
    
    def update_device_list(self):
        """Update the device list in the treeview"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add discovered devices
        for ip, device in self.devices.items():
            try:
                name = getattr(device, 'alias', f'Device at {ip}')

                # Get visual status and device type
                status = self.get_status_display(device)
                device_icon = self.get_device_icon(device)

                # Determine color tag based on device status
                try:
                    if device.is_on:
                        tag = 'online'
                    else:
                        tag = 'offline'
                except (AttributeError, Exception):
                    tag = 'unknown'

                # Create minimal display values
                values = (
                    f"{device_icon} {name}",         # Device name with icon
                    status,                          # Status with text
                    "Toggle"                         # Toggle control text
                )

                self.tree.insert("", "end", iid=ip, values=values, tags=(tag,))

            except Exception as e:
                print(f"Error adding device {ip}: {e}")
                # Add device anyway with minimal info
                self.tree.insert("", "end", iid=ip, values=(
                    f"📱 Device {ip}", "⚪ Unknown", "Toggle"
                ), tags=('unknown',))

        # Update statistics
        self.update_statistics()
    
    async def _toggle_device(self, ip):
        """Async method to toggle a single device"""
        try:
            device = self.devices[ip]
            
            # Safely update device state with timeout
            try:
                await asyncio.wait_for(device.update(), timeout=15)
            except Exception as e:
                self.status_var.set(f"Device {ip} communication error: {type(e).__name__}")
                return
            
            # Toggle the device
            try:
                if device.is_on:
                    await asyncio.wait_for(device.turn_off(), timeout=15)
                    status = "Turned OFF"
                else:
                    await asyncio.wait_for(device.turn_on(), timeout=15)
                    status = "Turned ON"
            except Exception as e:
                self.status_var.set(f"Failed to toggle device: {type(e).__name__}")
                return
            
            self.status_var.set(f"Device {getattr(device, 'alias', ip)} {status}")
            
            # Update the display
            await asyncio.sleep(0.5)
            try:
                await asyncio.wait_for(device.update(), timeout=15)
            except Exception:
                pass
            self.update_device_list()
            
        except Exception as e:
            error_msg = f"Failed to toggle device: {type(e).__name__} - {str(e)}"
            self.status_var.set(error_msg)
            print(error_msg)
            messagebox.showerror("Toggle Error", f"Failed to toggle device:\n{str(e)}")
    
    def on_device_double_click(self, event):
        """Handle double-click on device to toggle it"""
        selection = self.tree.selection()
        if selection:
            ip = selection[0]
            if ip in self.devices:
                self.run_async(self._toggle_device(ip))
    
    async def _turn_all_devices(self, turn_on=True):
        """Async method to turn all devices on or off"""
        try:
            action = "on" if turn_on else "off"
            self.status_var.set(f"Turning all devices {action}...")
            self.root.update()
            
            # Control devices with individual error handling
            tasks = []
            for ip, device in self.devices.items():
                if turn_on:
                    task = asyncio.create_task(asyncio.wait_for(device.turn_on(), timeout=10))
                else:
                    task = asyncio.create_task(asyncio.wait_for(device.turn_off(), timeout=10))
                tasks.append((ip, task))
            
            # Wait for all control operations to complete
            successful = 0
            failed = 0
            for ip, task in tasks:
                try:
                    await task
                    successful += 1
                except Exception as e:
                    print(f"Failed to control device {ip}: {type(e).__name__} - {str(e)}")
                    failed += 1
            
            # Update device states in parallel
            await asyncio.sleep(1)
            update_tasks = []
            for ip, device in self.devices.items():
                task = asyncio.create_task(asyncio.wait_for(device.update(), timeout=10))
                update_tasks.append(task)
            
            # Wait for all updates with error handling
            await asyncio.gather(*update_tasks, return_exceptions=True)
            
            self.update_device_list()
            
            if failed == 0:
                self.status_var.set(f"All {successful} devices turned {action}")
            else:
                self.status_var.set(f"{successful} devices turned {action}, {failed} failed")
            
        except Exception as e:
            error_msg = f"Failed to control all devices: {type(e).__name__} - {str(e)}"
            self.status_var.set(error_msg)
            print(error_msg)
            messagebox.showerror("Control Error", f"Failed to control all devices:\n{str(e)}")
    
    def turn_all_on(self):
        """Turn all devices on"""
        if not self.devices:
            messagebox.showwarning("No Devices", "No devices found. Please discover devices first.")
            return
        self.run_async(self._turn_all_devices(True))
    
    def turn_all_off(self):
        """Turn all devices off"""
        if not self.devices:
            messagebox.showwarning("No Devices", "No devices found. Please discover devices first.")
            return
        self.run_async(self._turn_all_devices(False))
    
    async def _refresh_status(self):
        """Async method to refresh device status"""
        try:
            self.status_var.set("Refreshing device status...")
            self.root.update()
            
            # Update devices in parallel
            update_tasks = []
            for ip, device in self.devices.items():
                task = asyncio.create_task(asyncio.wait_for(device.update(), timeout=10))
                update_tasks.append((ip, task))
            
            # Wait for all updates with error handling
            successful = 0
            failed = 0
            for ip, task in update_tasks:
                try:
                    await task
                    successful += 1
                except Exception as e:
                    print(f"Failed to update device {ip}: {type(e).__name__} - {str(e)}")
                    failed += 1
            
            self.update_device_list()
            
            if failed == 0:
                self.status_var.set(f"Status refreshed for all {successful} devices")
            else:
                self.status_var.set(f"Status refreshed for {successful} devices, {failed} failed")
            
        except Exception as e:
            error_msg = f"Failed to refresh status: {type(e).__name__} - {str(e)}"
            self.status_var.set(error_msg)
            print(error_msg)
    
    def refresh_status(self):
        """Refresh the status of all devices"""
        if not self.devices:
            messagebox.showwarning("No Devices", "No devices found. Please discover devices first.")
            return
        self.run_async(self._refresh_status())


def main():
    """Main function to start the GUI"""
    root = tk.Tk()
    app = KasaDeviceGUI(root)
    
    # Handle window closing
    def on_closing():
        app.cleanup()
        root.quit()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()