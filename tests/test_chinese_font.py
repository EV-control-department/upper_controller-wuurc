#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试中文字体渲染
这个脚本用于测试pygame中文字体渲染是否正常
"""

import time

import pygame


def test_chinese_font():
    """测试中文字体渲染"""
    # 初始化pygame
    pygame.init()

    # 创建窗口
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("中文字体测试")

    # 背景颜色
    background_color = (0, 0, 0)

    # 测试文本
    test_texts = [
        "ROV控制上位机软件",
        "舵机: 0.75",
        "深度: 10.5 m",
        "温度: 25.3 °C",
        "速度模式: 高速",
        "锁定模式: 已锁定",
        "抓取模式: 模式1"
    ]

    # 尝试使用配置中指定的字体
    try:
        # 首先尝试使用SimHei
        font = pygame.font.SysFont("SimHei", 30)
        print("使用字体: SimHei")
    except:
        try:
            # 尝试使用系统中支持中文的字体
            system_fonts = pygame.font.get_fonts()
            chinese_fonts = [f for f in system_fonts if
                             f in ['simsun', 'simhei', 'microsoftyahei', 'dengxian', 'fangsong', 'kaiti']]

            if chinese_fonts:
                font = pygame.font.SysFont(chinese_fonts[0], 30)
                print(f"使用中文字体: {chinese_fonts[0]}")
            else:
                # 如果没有找到中文字体，使用默认字体
                font = pygame.font.Font(None, 30)
                print("警告: 未找到支持中文的字体，可能导致中文显示异常")
        except:
            font = pygame.font.Font(None, 30)
            print("警告: 字体初始化失败，使用默认字体")

    # 显示可用的系统字体
    print("\n可用的系统字体:")
    system_fonts = pygame.font.get_fonts()
    chinese_fonts = [f for f in system_fonts if
                     f in ['simsun', 'simhei', 'microsoftyahei', 'dengxian', 'fangsong', 'kaiti']]
    print(f"找到的中文字体: {chinese_fonts}")

    # 主循环
    running = True
    while running:
        # 处理事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # 清空屏幕
        screen.fill(background_color)

        # 渲染测试文本
        y_offset = 50
        for text in test_texts:
            # 渲染文本
            text_surface = font.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (50, y_offset))
            y_offset += 50

        # 更新显示
        pygame.display.flip()

        # 等待一段时间
        time.sleep(0.1)

    # 退出pygame
    pygame.quit()


if __name__ == "__main__":
    test_chinese_font()
