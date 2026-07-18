#include "protocol_process.h"
#include "comm.h"
#include "RS485_process.h"
#include "main.h"

#include "usart.h"
#include "tim.h"

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#pragma pack(push, 1) // 确保 1 字节对齐
#pragma pack(pop)      // 恢复默认对齐

extern int threadmonitor_uart8;
Protocol_Command_t command = {0};
extern float realdepth;
extern float temperature;
extern uint8_t transbuf[256];

extern float servo0angle;

/* 私有函数 */
static void process_motion_ctrl(uint8_t *pdata);
static void process_thrust_config(uint8_t *pdata);
static void apply_motor_control(void);

/*
 * 函数名: Protocol_Process_Data
 * 描述  : 处理接收到的二进制协议帧数据
 *          帧格式: [CMD (1B)] [DATA (N B)] [CHECK_XOR (1B)]
 * 输入  : pdata  - 指向数据区首字节 (CMD) 的指针
 *          length - 数据区长度 (含 CMD 和 CHECK_XOR)
 * 输出  : 无
 * 备注  :
 */
void Protocol_Process_Data(uint8_t *pdata, uint16_t length)
{
    if (length < 1) return;          // 至少需要 CMD

    uint8_t cmd = pdata[0];
    // XOR 校验已在 comm.c 完成，此处不再重复验证

    /* 根据命令字派发 */
    switch (cmd) {
        case CMD_MOTION_CTRL:
            process_motion_ctrl(pdata);
            break;

        case CMD_THRUST_CONFIG:
            process_thrust_config(pdata);
            break;

        default:
            // 未知命令
            break;
    }

    HAL_GPIO_TogglePin(led2_GPIO_Port, led2_Pin); // 切换 LED 状态
}

/*
 * 函数名: process_motion_ctrl
 * 描述  : 解析运动控制帧 (CMD 0x01)
 *          帧格式:
 *            [0]     CMD = 0x01
 *            [1 - 4]  x       (float, 小端)
 *            [5 - 8]  y       (float, 小端)
 *            [9 -12]  z       (float, 小端)
 *            [13-16]  roll    (float, 小端)
 *            [17-20]  pitch   (float, 小端)
 *            [21-24]  yaw     (float, 小端)
 *            [25-28]  servo0  (float, 小端)
 *            [29]     CHECK_XOR
 *          帧总长度: 34 字节 (含帧头帧尾)
 * 输入  : pdata - 协议数据区指针
 * 输出  : 无
 * 备注  : 解析后将内部转发到 INTER_COMM，并设置 servo0angle
 */
static void process_motion_ctrl(uint8_t *pdata)
{
    float temp_float;

    /* 准备转发帧头 (INTER_COMM 保持原有 38 字节格式) */
    memset(transbuf, 0, 40);
    transbuf[0]  = 0xFA;
    transbuf[1]  = 0xAF;
    transbuf[2]  = 0x01;
    transbuf[36] = 0xFB;
    transbuf[37] = 0xBF;

    /* x (offset 1) */
    memcpy(&temp_float, pdata + 5, 4);
    memcpy(transbuf + 3, &temp_float, 4);

    /* y (offset 5) */
    memcpy(&temp_float, pdata + 1, 4);
    memcpy(transbuf + 7, &temp_float, 4);

    /* z (offset 9) */
    memcpy(&temp_float, pdata + 9, 4);
    memcpy(transbuf + 11, &temp_float, 4);

    /* roll (offset 13) */
    memcpy(&temp_float, pdata + 13, 4);
    memcpy(transbuf + 15, &temp_float, 4);

    /* pitch (offset 17) */
    memcpy(&temp_float, pdata + 17, 4);
    memcpy(transbuf + 19, &temp_float, 4);

    /* yaw (offset 21) */
    memcpy(&temp_float, pdata + 21, 4);
    memcpy(transbuf + 23, &temp_float, 4);

    /* servo0 (offset 25) — 解析舵机角度，设置全局变量并转发 */
    memcpy(&temp_float, pdata + 25, 4);
    if (temp_float > 0.01f) {
        memcpy(transbuf + 27, &temp_float, 4);
    }
    servo0angle = temp_float;

    transbuf[35] = Check_Data(transbuf + 2, 33); // 计算校验和 (字节 2~34)
    HAL_UART_Transmit(&INTER_COMM, transbuf, 38, 32); // 发送数据包到内部总线
}

/*
 * 函数名: process_thrust_config
 * 描述  : 解析推力参数配置帧 (CMD 0x02)
 *          帧格式:
 *            [0]     CMD = 0x02
 *            [1]     motor_num (uint8_t, 0-5)
 *            [2 - 5] np_mid   (float, 小端)
 *            [6 - 9] np_ini   (float, 小端)
 *            [10-13] pp_ini   (float, 小端)
 *            [14-17] pp_mid   (float, 小端)
 *            [18-21] nt_end   (float, 小端)
 *            [22-25] nt_mid   (float, 小端)
 *            [26-29] pt_mid   (float, 小端)
 *            [30-33] pt_end   (float, 小端)
 *            [34]    CHECK_XOR
 *            (共 35 字节数据区, 加帧头帧尾 = 40 字节)
 * 输入  : pdata - 协议数据区指针
 * 输出  : 无
 * 备注  : 转发到 INTER_COMM
 */
static void process_thrust_config(uint8_t *pdata)
{
    /* 准备转发帧头 */
    memset(transbuf, 0, 40);
    transbuf[0]  = 0xFA;
    transbuf[1]  = 0xAF;
    transbuf[2]  = 0x02;
    transbuf[37] = 0xFB;
    transbuf[38] = 0xBF;

    /* motor_num */
    transbuf[3] = pdata[1];

    /* np_mid (offset 2) */
    memcpy(transbuf + 4,  pdata + 2,  4);

    /* np_ini (offset 6) */
    memcpy(transbuf + 8,  pdata + 6,  4);

    /* pp_ini (offset 10) */
    memcpy(transbuf + 12, pdata + 10, 4);

    /* pp_mid (offset 14) */
    memcpy(transbuf + 16, pdata + 14, 4);

    /* nt_end (offset 18) */
    memcpy(transbuf + 20, pdata + 18, 4);

    /* nt_mid (offset 22) */
    memcpy(transbuf + 24, pdata + 22, 4);

    /* pt_mid (offset 26) */
    memcpy(transbuf + 28, pdata + 26, 4);

    /* pt_end (offset 30) */
    memcpy(transbuf + 32, pdata + 30, 4);

    transbuf[36] = Check_Data(transbuf + 2, 34); // 计算校验和
    HAL_UART_Transmit(&INTER_COMM, transbuf, 39, 16); // 发送数据包到内部总线

    /* 回传当前处理的电机 ID 到上位机 (CMD 0x04, 无校验位) */
    uint8_t ack_buf[6];
    ack_buf[0] = FRAME_HEADER1;     // 0xFA
    ack_buf[1] = FRAME_HEADER2;     // 0xAF
    ack_buf[2] = CMD_THRUST_ACK;    // 0x04
    ack_buf[3] = pdata[1];          // motor_num
    ack_buf[4] = FRAME_FOOTER1;     // 0xFB
    ack_buf[5] = FRAME_FOOTER2;     // 0xBF
    HAL_UART_Transmit(&EXTER_COMM, ack_buf, 6, 16);
}

/*
 * 函数名: send_depth_temperature
 * 描述  : 将实时深度和温度值使用二进制帧上报到上位机
 *          帧格式 (CMD 0x03):
 *            FRAME_HEADER: 0xFA 0xAF
 *            [2]  CMD = 0x03
 *            [3-6]  depth      (float, 小端)
 *            [7-10] temperature (float, 小端)
 *            [11]  CHECK_XOR
 *            FRAME_FOOTER: 0xFB 0xBF
 *            总长度: 14 字节
 * 输入  : 无
 * 输出  : 无
 * 备注  : 由定时器中断周期性调用
 */
void send_depth_temperature(void)
{
    uint8_t send_buf[16]; // 14 字节 + 2 余量
    memset(send_buf, 0, sizeof(send_buf));

    send_buf[0]  = FRAME_HEADER1;      // 0xFA
    send_buf[1]  = FRAME_HEADER2;      // 0xAF
    send_buf[2]  = CMD_DEPTH_TEMP;     // 0x03

    /* depth (float, 小端) */
    float d = realdepth;
    memcpy(send_buf + 3, &d, 4);

    /* temperature (float, 小端) */
    float t = temperature;
    memcpy(send_buf + 7, &t, 4);

    /* XOR 校验 (从 CMD 到 temp 末尾, 共 9 字节) */
    send_buf[11] = Check_Data(send_buf + 2, 9);

    send_buf[12] = FRAME_FOOTER1;     // 0xFB
    send_buf[13] = FRAME_FOOTER2;     // 0xBF

    HAL_UART_Transmit(&EXTER_COMM, send_buf, 14, 100);
}