import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading

class ProtocolTesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("云卓 TOP Protocol V1.1.6 交互测试工具")
        self.root.geometry("850x780")
        self.root.resizable(False, False)

        # Initialize UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', 0))
        self.sock.settimeout(0.5)
        
        self.running = True
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self._build_ui()

        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self.rx_thread.start()

    def _on_closing(self):
        self.running = False
        self.root.destroy()

    def _build_ui(self):
        # ==================== 1. 网络配置区 ====================
        net_frame = ttk.LabelFrame(self.root, text="网络配置 (UDP / 端口默认 5000)")
        net_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(net_frame, text="设备 IP:").pack(side="left", padx=5, pady=5)
        self.ip_var = tk.StringVar(value="192.168.55.12")
        ttk.Entry(net_frame, textvariable=self.ip_var, width=15).pack(side="left", padx=5)
        
        ttk.Label(net_frame, text="设备端口:").pack(side="left", padx=5)
        self.port_var = tk.IntVar(value=5000)
        ttk.Entry(net_frame, textvariable=self.port_var, width=8).pack(side="left", padx=5)
        
        # ==================== 2. 快捷指令区 ====================
        # (G类) 云台基础控制 
        ptz_frame = ttk.LabelFrame(self.root, text="云台基础控制 (G类 - 目标G - PTZ)")
        ptz_frame.pack(fill="x", padx=10, pady=5)
        
        ptz_btns = [
            ("向上", "01"), ("向下", "02"), ("向左", "03"), ("向右", "04"),
            ("一键回中", "05"), ("跟随模式", "06"), ("锁头模式", "07"), ("停止", "00")
        ]
        for text, data in ptz_btns:
            btn = ttk.Button(ptz_frame, text=text, width=8, 
                             command=lambda d=data: self.send_preset("UG", "w", "PTZ", d))
            btn.pack(side="left", padx=2, pady=5)
            
        # (G类) 单轴恒速转动
        speed_frame = ttk.LabelFrame(self.root, text="云台单轴速度控制 (G类 - 目标G - GSP/GSY)")
        speed_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(speed_frame, text="航向左转 (-30)", command=lambda: self.send_preset("UG", "w", "GSY", "E2")).pack(side="left", padx=4, pady=5)
        ttk.Button(speed_frame, text="航向右转 (+30)", command=lambda: self.send_preset("UG", "w", "GSY", "1E")).pack(side="left", padx=4)
        ttk.Button(speed_frame, text="俯仰上抬 (+20)", command=lambda: self.send_preset("UG", "w", "GSP", "14")).pack(side="left", padx=4)
        ttk.Button(speed_frame, text="停止转动", command=lambda: self.send_preset("UG", "w", "GSY", "00")).pack(side="left", padx=4)

        # (D类) 图像与载荷控制 
        cam_frame = ttk.LabelFrame(self.root, text="图像与载荷控制 (D类 - 目标D)")
        cam_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(cam_frame, text="单张拍照 (CAP)", command=lambda: self.send_preset("UD", "w", "CAP", "01")).pack(side="left", padx=4, pady=5)
        ttk.Button(cam_frame, text="开始录像 (REC)", command=lambda: self.send_preset("UD", "w", "REC", "01")).pack(side="left", padx=4)
        ttk.Button(cam_frame, text="停止录像 (REC)", command=lambda: self.send_preset("UD", "w", "REC", "00")).pack(side="left", padx=4)
        ttk.Button(cam_frame, text="白热模式 (IMG)", command=lambda: self.send_preset("UD", "w", "IMG", "01")).pack(side="left", padx=4)
        ttk.Button(cam_frame, text="2x变焦 (DZM)", command=lambda: self.send_preset("UD", "w", "DZM", "02")).pack(side="left", padx=4)

        # ==================== 5. 姿态数据区 ====================
        rx_frame = ttk.LabelFrame(self.root, text="姿态数据反馈 (RX) (G类 - GAC)")
        rx_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(rx_frame, text="开启姿态回传(10Hz)", command=lambda: self.send_preset("UG", "w", "GAA", "0A")).pack(side="left", padx=5, pady=5)
        ttk.Button(rx_frame, text="开启姿态回传(50Hz)", command=lambda: self.send_preset("UG", "w", "GAA", "32")).pack(side="left", padx=5)
        ttk.Button(rx_frame, text="关闭姿态回传", command=lambda: self.send_preset("UG", "w", "GAA", "00")).pack(side="left", padx=5)
        
        ttk.Label(rx_frame, text="Yaw (航向):").pack(side="left", padx=5)
        self.yaw_var = tk.StringVar(value="0.0")
        ttk.Entry(rx_frame, textvariable=self.yaw_var, width=8, state="readonly").pack(side="left", padx=2)
        
        ttk.Label(rx_frame, text="Pitch (俯仰):").pack(side="left", padx=5)
        self.pitch_var = tk.StringVar(value="0.0")
        ttk.Entry(rx_frame, textvariable=self.pitch_var, width=8, state="readonly").pack(side="left", padx=2)
        
        ttk.Label(rx_frame, text="Roll (横滚):").pack(side="left", padx=5)
        self.roll_var = tk.StringVar(value="0.0")
        ttk.Entry(rx_frame, textvariable=self.roll_var, width=8, state="readonly").pack(side="left", padx=2)

        # ==================== 3. 自定义指令生成区 ====================
        custom_frame = ttk.LabelFrame(self.root, text="自定义指令生成与发送")
        custom_frame.pack(fill="x", padx=10, pady=5)
        
        grid_f = ttk.Frame(custom_frame)
        grid_f.pack(fill="x", padx=5, pady=5)
        
        # Row 0
        ttk.Label(grid_f, text="帧头:").grid(row=0, column=0, padx=2)
        self.header_var = tk.StringVar(value="#TP")
        ttk.Combobox(grid_f, textvariable=self.header_var, values=["#TP", "#tp"], width=4).grid(row=0, column=1)

        ttk.Label(grid_f, text="源(SRC):").grid(row=0, column=2, padx=2)
        self.src_var = tk.StringVar(value="U")
        ttk.Entry(grid_f, textvariable=self.src_var, width=3).grid(row=0, column=3)

        ttk.Label(grid_f, text="目的(DST):").grid(row=0, column=4, padx=2)
        self.dst_var = tk.StringVar(value="G")
        ttk.Combobox(grid_f, textvariable=self.dst_var, values=["G", "D", "M", "E"], width=3).grid(row=0, column=5)

        ttk.Label(grid_f, text="读写(R/W):").grid(row=0, column=6, padx=2)
        self.rw_var = tk.StringVar(value="w")
        ttk.Combobox(grid_f, textvariable=self.rw_var, values=["w", "r"], width=3).grid(row=0, column=7)

        ttk.Label(grid_f, text="指令(CMD):").grid(row=0, column=8, padx=2)
        self.cmd_var = tk.StringVar(value="PTZ")
        ttk.Entry(grid_f, textvariable=self.cmd_var, width=5).grid(row=0, column=9)

        # Row 1
        ttk.Label(grid_f, text="数据(Data):").grid(row=1, column=0, padx=2, pady=10)
        self.data_var = tk.StringVar(value="01")
        ttk.Entry(grid_f, textvariable=self.data_var, width=25).grid(row=1, column=1, columnspan=7, sticky="w")

        btn_generate = ttk.Button(grid_f, text="生成并预览 ->", command=self.generate_custom)
        btn_generate.grid(row=1, column=8, columnspan=2, padx=5)

        # Row 2 (Result)
        res_frame = ttk.Frame(custom_frame)
        res_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(res_frame, text="完整报文(含CRC):").pack(side="left")
        self.res_var = tk.StringVar()
        ttk.Entry(res_frame, textvariable=self.res_var, state="readonly", font=("Courier", 13, "bold"), width=30).pack(side="left", padx=5)
        
        ttk.Button(res_frame, text="立刻发送", command=self.send_custom, style="Accent.TButton").pack(side="left", padx=10)
        
        # ==================== 4. 日志区 ====================
        log_frame = ttk.LabelFrame(self.root, text="通信日志 (TX)")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, font=("Courier", 10), state="disabled", bg="#f4f4f4")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Style override for highlight button
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Sans", 9, "bold"), foreground="blue")


    # ------------------- 核心协议与网络算法 -------------------

    def log(self, msg):
        """Append text to the readonly text widget."""
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def calculate_crc(self, payload: str) -> str:
        """
        根据云卓协议：从起始符到数据末尾计算ASCII特征累加和。
        取一个字节后转为2位大写十六进制。
        """
        crc_sum = sum(ord(c) for c in payload)
        return f"{(crc_sum & 0xFF):02X}"

    def build_packet(self, header, src, dst, rw, cmd, data) -> str:
        """组装完整数据包，自动推算LEN和CRC"""
        data_len = len(data)
        # 长度转化为1位hex（如长度6为'6'，12为'C'）
        len_char = f"{data_len:X}"[-1].upper() 
        
        payload = f"{header}{src}{dst}{len_char}{rw}{cmd}{data}"
        crc_hex = self.calculate_crc(payload)
        return payload + crc_hex

    def _udp_send(self, packet_str: str):
        """通过UDP Socket 发送 ASCII 字符串数据包"""
        ip = self.ip_var.get()
        port = self.port_var.get()
        try:
            self.sock.sendto(packet_str.encode('ascii'), (ip, port))
            self.log(f"[TX 成功] 目标: {ip}:{port} | 报文: {packet_str}")
        except Exception as e:
            self.log(f"[TX 错误] 网络异常: {e}")
            messagebox.showerror("网络发送失败", str(e))

    # ------------------- UI 动作回调 -------------------

    def send_preset(self, target, rw, cmd, data):
        """点击预设按钮时直接组装+发送快捷指令"""
        src = target[0] # U
        dst = target[1] # G, D, etc.
        packet = self.build_packet("#TP", src, dst, rw, cmd, data)
        self._udp_send(packet)

    def generate_custom(self):
        """点击生成自定义报文 (仅预览不发送)"""
        try:
            packet = self.build_packet(
                self.header_var.get(),
                self.src_var.get(),
                self.dst_var.get(),
                self.rw_var.get(),
                self.cmd_var.get(),
                self.data_var.get()
            )
            self.res_var.set(packet)
            self.log(f"[生成校验] 组装结果: {packet}")
        except Exception as e:
            messagebox.showerror("生成失败", str(e))

    def send_custom(self):
        """发送自定义报文"""
        packet = self.res_var.get()
        if not packet:
            messagebox.showwarning("提示", "请先点击[生成并预览]按钮！")
            return
        self._udp_send(packet)

    def parse_angle(self, hex_str):
        try:
            val = int(hex_str, 16)
            # 16-bit signed integer
            if val >= 0x8000:
                val -= 0x10000
            return val / 100.0
        except ValueError:
            return 0.0

    def _rx_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                data_str = data.decode('ascii', errors='ignore')
                
                # Format: #TPUGCrGACY0Y1Y2Y3P0P1P2P3R0R1R2R3CC
                idx = data_str.find("rGAC")
                if idx != -1 and len(data_str) >= idx + 4 + 12:
                    payload = data_str[idx+4 : idx+4+12]
                    yaw_hex = payload[0:4]
                    pitch_hex = payload[4:8]
                    roll_hex = payload[8:12]
                    
                    yaw = self.parse_angle(yaw_hex)
                    pitch = self.parse_angle(pitch_hex)
                    roll = self.parse_angle(roll_hex)
                    
                    # Update UI in thread-safe way
                    self.root.after(0, self.yaw_var.set, f"{yaw:.2f}")
                    self.root.after(0, self.pitch_var.set, f"{pitch:.2f}")
                    self.root.after(0, self.roll_var.set, f"{roll:.2f}")
                    
                else:
                    self.root.after(0, self.log, f"[RX 数据] {addr}: {data_str}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.root.after(0, self.log, f"[RX 错误] {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ProtocolTesterApp(root)
    root.mainloop()
