# 视频线程监控机制

## 概述

为了提高系统稳定性，我们在主控制器中实现了一个视频线程监控机制。该机制会每10秒检查一次视频线程的状态，如果发现线程已停止，则会自动重新启动线程。

## 实现细节

### 1. 初始化监控变量

在 `MainController` 类的 `__init__` 方法中，我们添加了以下代码来初始化视频线程监控变量：

```python
# 视频线程监控变量
self.last_video_check_time = time.time()
self.video_check_interval = 10  # 每10秒检查一次视频线程状态
```

### 2. 定期检查视频线程状态

在 `run` 方法中，我们添加了以下代码来定期检查视频线程的状态：

```python
# 检查视频线程状态（每10秒检查一次）
current_time = time.time()
if current_time - self.last_video_check_time >= self.video_check_interval:
    self.last_video_check_time = current_time
    
    # 添加调试日志
    print(f"[DEBUG] 检查视频线程状态: {'运行中' if self.video_thread.is_alive() else '已停止'}")
    
    # 检查视频线程是否还在运行
    if not self.video_thread.is_alive():
        print("视频线程已停止，正在重新启动...")
        # 重新初始化视频线程
        rtsp_url = self.config_manager.get_rtsp_url()
        base_width, base_height = self.config_manager.get_camera_dimensions()
        buffer_size = self.config_manager.config["camera"].getint("buffer")
        
        # 尝试停止旧线程（如果还存在）
        try:
            if hasattr(self.video_thread, 'stop'):
                self.video_thread.stop()
        except Exception as e:
            print(f"停止旧视频线程时出错: {str(e)}")
        
        # 创建并启动新线程
        self.video_thread = VideoThread(rtsp_url, base_width, base_height, buffer_size)
        self.video_thread.start()
        print("视频线程已重新启动")
```

## 工作原理

1. 系统在初始化时记录当前时间作为上次检查时间
2. 在主循环中，系统会检查当前时间与上次检查时间的差值
3. 如果差值大于或等于设定的检查间隔（10秒），则执行检查
4. 检查视频线程是否还在运行（使用 `is_alive()` 方法）
5. 如果线程已停止，则尝试停止旧线程（如果还存在），然后创建并启动新线程
6. 更新上次检查时间为当前时间

## 调试信息

为了便于调试，系统会在每次检查时输出视频线程的状态信息。这些信息可以帮助开发人员了解视频线程的运行情况，以及是否有重启操作发生。

## 注意事项

- 检查间隔设置为10秒，可以根据需要进行调整
- 重启视频线程时会使用与初始化时相同的参数
- 在尝试重启前，系统会先尝试停止旧线程，以避免资源泄漏