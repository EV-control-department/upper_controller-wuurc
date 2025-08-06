from PyQt5.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- 全局常量 ---
PWM_MID = 3000


# --- Matplotlib 可拖拽点交互式画布 ---
class DraggablePointPlot(FigureCanvas):
    point_dragged = pyqtSignal()
    point_selected = pyqtSignal(str)

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.points_artists = []
        self.lines = []
        self._drag_point_info = None
        self.comparison_lines = []  # 用于存储比较曲线的线条
        self.is_dual_view = False  # 是否处于双曲线视图模式
        self.comparison_artists = []  # 用于存储比较曲线的点
        self.update_interval = 10  # 刷新间隔（毫秒），较小的值使UI更响应

    def plot_curve(self, curve_params, pwm_end_p, pwm_end_n):
        """绘制单条曲线"""
        self.axes.clear()
        self.is_dual_view = False
        self.point_params = curve_params

        self.points_data = {
            'nt_end': (curve_params['nt_end'], pwm_end_n),
            'nt_mid': (curve_params['nt_mid'], curve_params['np_mid']),
            'np_ini': (0, curve_params['np_ini']),
            'pp_ini': (0, curve_params['pp_ini']),
            'pt_mid': (curve_params['pt_mid'], curve_params['pp_mid']),
            'pt_end': (curve_params['pt_end'], pwm_end_p),
        }

        neg_x = [self.points_data['nt_end'][0], self.points_data['nt_mid'][0], self.points_data['np_ini'][0]]
        neg_y = [self.points_data['nt_end'][1], self.points_data['nt_mid'][1], self.points_data['np_ini'][1]]
        pos_x = [self.points_data['pp_ini'][0], self.points_data['pt_mid'][0], self.points_data['pt_end'][0]]
        pos_y = [self.points_data['pp_ini'][1], self.points_data['pt_mid'][1], self.points_data['pt_end'][1]]

        self.lines = [];
        self.lines.extend(self.axes.plot(neg_x, neg_y, 'b-', linewidth=2));
        self.lines.extend(self.axes.plot(pos_x, pos_y, 'g-', linewidth=2))
        self.points_artists = []
        for name, (x, y) in self.points_data.items():
            artist = self.axes.plot(x, y, 'ro', markersize=8)[0]
            artist.set_gid(name);
            self.points_artists.append(artist)

        self._setup_plot_style();
        self.draw()

    def plot_dual_curves(self, primary_params, comparison_params, pwm_end_p, pwm_end_n, primary_name, comparison_name):
        """绘制双曲线对比视图"""
        self.axes.clear()
        self.is_dual_view = True
        self.point_params = primary_params
        self.comparison_params = comparison_params  # 保存比较参数

        # 主曲线数据点
        self.points_data = {
            'nt_end': (primary_params['nt_end'], pwm_end_n),
            'nt_mid': (primary_params['nt_mid'], primary_params['np_mid']),
            'np_ini': (0, primary_params['np_ini']),
            'pp_ini': (0, primary_params['pp_ini']),
            'pt_mid': (primary_params['pt_mid'], primary_params['pp_mid']),
            'pt_end': (primary_params['pt_end'], pwm_end_p),
        }

        # 比较曲线数据点
        self.comparison_points = {
            'nt_end_comp': (comparison_params['nt_end'], pwm_end_n),
            'nt_mid_comp': (comparison_params['nt_mid'], comparison_params['np_mid']),
            'np_ini_comp': (0, comparison_params['np_ini']),
            'pp_ini_comp': (0, comparison_params['pp_ini']),
            'pt_mid_comp': (comparison_params['pt_mid'], comparison_params['pp_mid']),
            'pt_end_comp': (comparison_params['pt_end'], pwm_end_p),
        }

        # 主曲线坐标
        primary_neg_x = [self.points_data['nt_end'][0], self.points_data['nt_mid'][0], self.points_data['np_ini'][0]]
        primary_neg_y = [self.points_data['nt_end'][1], self.points_data['nt_mid'][1], self.points_data['np_ini'][1]]
        primary_pos_x = [self.points_data['pp_ini'][0], self.points_data['pt_mid'][0], self.points_data['pt_end'][0]]
        primary_pos_y = [self.points_data['pp_ini'][1], self.points_data['pt_mid'][1], self.points_data['pt_end'][1]]

        # 比较曲线坐标
        comp_neg_x = [self.comparison_points['nt_end_comp'][0], self.comparison_points['nt_mid_comp'][0],
                      self.comparison_points['np_ini_comp'][0]]
        comp_neg_y = [self.comparison_points['nt_end_comp'][1], self.comparison_points['nt_mid_comp'][1],
                      self.comparison_points['np_ini_comp'][1]]
        comp_pos_x = [self.comparison_points['pp_ini_comp'][0], self.comparison_points['pt_mid_comp'][0],
                      self.comparison_points['pt_end_comp'][0]]
        comp_pos_y = [self.comparison_points['pp_ini_comp'][1], self.comparison_points['pt_mid_comp'][1],
                      self.comparison_points['pt_end_comp'][1]]

        # 绘制主曲线 (实线)
        self.lines = []
        self.lines.extend(
            self.axes.plot(primary_neg_x, primary_neg_y, 'b-', linewidth=2.5, label=f"{primary_name} 负向"))
        self.lines.extend(
            self.axes.plot(primary_pos_x, primary_pos_y, 'g-', linewidth=2.5, label=f"{primary_name} 正向"))

        # 绘制比较曲线 (虚线)
        self.comparison_lines = []
        self.comparison_lines.extend(
            self.axes.plot(comp_neg_x, comp_neg_y, 'b--', linewidth=1.5, alpha=0.8, label=f"{comparison_name} 负向"))
        self.comparison_lines.extend(
            self.axes.plot(comp_pos_x, comp_pos_y, 'g--', linewidth=1.5, alpha=0.8, label=f"{comparison_name} 正向"))

        # 绘制主曲线的可拖动点
        self.points_artists = []
        for name, (x, y) in self.points_data.items():
            artist = self.axes.plot(x, y, 'ro', markersize=8)[0]
            artist.set_gid(name)
            self.points_artists.append(artist)

        # 绘制比较曲线的可拖动点
        self.comparison_artists = []
        for name, (x, y) in self.comparison_points.items():
            artist = self.axes.plot(x, y, 'bo', markersize=8)[0]
            artist.set_gid(name)
            self.comparison_artists.append(artist)
            self.points_artists.append(artist)  # 添加到总的可拖动点列表中

        # 设置图表样式
        self._setup_plot_style(is_dual=True)
        self.draw()

    def _setup_plot_style(self, is_dual=False):
        """设置推力曲线图表样式"""
        if is_dual:
            self.axes.set_title("双曲线对比视图");
        else:
            self.axes.set_title("推力曲线 (Thrust-PWM)");

        self.axes.set_xlabel("推力 (g)");
        self.axes.set_ylabel("PWM")
        self.axes.grid(True, linestyle='--', alpha=0.7);
        self.axes.axhline(PWM_MID, color='grey', linestyle='--', linewidth=0.8)
        self.axes.axvline(0, color='black', linewidth=0.8);

        # 设置图例
        if is_dual:
            # 双曲线模式下使用自动生成的图例
            self.axes.legend(loc='upper right', fontsize=9)
        else:
            # 单曲线模式下使用简单图例
            self.axes.legend(self.lines, ['负向推力', '正向推力'])

        # 设置坐标轴范围
        self.axes.set_xlim([-2000, 2000])  # 适当设置推力范围
        self.axes.set_ylim([PWM_MID - 800, PWM_MID + 800])  # 适当设置PWM范围

    def connect_events(self):
        """连接鼠标事件"""
        self.mpl_connect('button_press_event', self.on_press);
        self.mpl_connect('motion_notify_event', self.on_motion)
        self.mpl_connect('button_release_event', self.on_release)

    def on_press(self, event):
        if event.inaxes != self.axes: return
        for artist in self.points_artists:
            contains, _ = artist.contains(event)
            if contains:
                name = artist.get_gid()
                self._drag_point_info = (artist, name)
                self.point_selected.emit(name);
                return

    def on_motion(self, event):
        if self._drag_point_info is None or event.xdata is None or event.ydata is None: return
        artist, name = self._drag_point_info
        x, y = event.xdata, event.ydata

        # 检查是否是比较曲线的点
        is_comparison_point = name.endswith('_comp')

        # 处理固定点和端点的特殊情况
        if name in ['np_ini', 'pp_ini'] or name in ['np_ini_comp', 'pp_ini_comp']:
            # 这些点的x坐标固定为0
            x = 0
            if is_comparison_point:
                y = self.comparison_points[name][1]
            else:
                y = self.points_data[name][1]
        elif name in ['nt_end', 'pt_end'] or name in ['nt_end_comp', 'pt_end_comp']:
            # 这些点的y坐标固定
            if is_comparison_point:
                y = self.comparison_points[name][1]
            else:
                y = self.points_data[name][1]

        # 更新点的位置
        artist.set_data([x], [y])

        # 根据是否是比较点更新相应的数据
        if is_comparison_point:
            self.comparison_points[name] = (x, y)

            # 更新比较参数
            base_name = name[:-5]  # 移除 '_comp' 后缀
            if base_name == 'nt_end':
                self.comparison_params['nt_end'] = x
            elif base_name == 'nt_mid':
                self.comparison_params['nt_mid'] = x
                self.comparison_params['np_mid'] = y
            elif base_name == 'pt_mid':
                self.comparison_params['pt_mid'] = x
                self.comparison_params['pp_mid'] = y
            elif base_name == 'pt_end':
                self.comparison_params['pt_end'] = x
            elif base_name == 'np_ini':
                self.comparison_params['np_ini'] = y
            elif base_name == 'pp_ini':
                self.comparison_params['pp_ini'] = y

            # 更新比较曲线
            self._update_comparison_lines()
        else:
            self.points_data[name] = (x, y)

            # 更新主参数
            if name == 'nt_end':
                self.point_params['nt_end'] = x
            elif name == 'nt_mid':
                self.point_params['nt_mid'] = x
                self.point_params['np_mid'] = y
            elif name == 'pt_mid':
                self.point_params['pt_mid'] = x
                self.point_params['pp_mid'] = y
            elif name == 'pt_end':
                self.point_params['pt_end'] = x
            elif name == 'np_ini':
                self.point_params['np_ini'] = y
            elif name == 'pp_ini':
                self.point_params['pp_ini'] = y

            # 更新主曲线
            self._update_lines()

        self.draw()
        # 发送信号通知UI实时更新
        self.point_dragged.emit()

    def on_release(self, event):
        if self._drag_point_info is None: return
        artist, name = self._drag_point_info

        if name in ['np_ini', 'pp_ini']:
            self._drag_point_info = None
            return

        # Parameters are already updated in on_motion
        # Just release the drag point info
        self._drag_point_info = None

    def _update_lines(self):
        neg_x = [self.points_data['nt_end'][0], self.points_data['nt_mid'][0], self.points_data['np_ini'][0]]
        neg_y = [self.points_data['nt_end'][1], self.points_data['nt_mid'][1], self.points_data['np_ini'][1]]
        pos_x = [self.points_data['pp_ini'][0], self.points_data['pt_mid'][0], self.points_data['pt_end'][0]]
        pos_y = [self.points_data['pp_ini'][1], self.points_data['pt_mid'][1], self.points_data['pt_end'][1]]
        self.lines[0].set_data(neg_x, neg_y);
        self.lines[1].set_data(pos_x, pos_y)

    def _update_comparison_lines(self):
        """更新比较曲线"""
        if not self.is_dual_view or not hasattr(self, 'comparison_lines') or len(self.comparison_lines) < 2:
            return

        neg_x = [self.comparison_points['nt_end_comp'][0], self.comparison_points['nt_mid_comp'][0],
                 self.comparison_points['np_ini_comp'][0]]
        neg_y = [self.comparison_points['nt_end_comp'][1], self.comparison_points['nt_mid_comp'][1],
                 self.comparison_points['np_ini_comp'][1]]
        pos_x = [self.comparison_points['pp_ini_comp'][0], self.comparison_points['pt_mid_comp'][0],
                 self.comparison_points['pt_end_comp'][0]]
        pos_y = [self.comparison_points['pp_ini_comp'][1], self.comparison_points['pt_mid_comp'][1],
                 self.comparison_points['pt_end_comp'][1]]

        self.comparison_lines[0].set_data(neg_x, neg_y)
        self.comparison_lines[1].set_data(pos_x, pos_y)
