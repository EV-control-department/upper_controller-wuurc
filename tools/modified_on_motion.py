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
