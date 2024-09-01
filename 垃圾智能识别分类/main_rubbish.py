# 导入必要的库
import sensor, image, lcd, time
import KPU as kpu
import gc, sys
from machine import Timer,PWM
import time

#PWM通过定时器配置，接到IO22引脚
tim = Timer(Timer.TIMER0, Timer.CHANNEL0, mode=Timer.MODE_PWM)
S1 = PWM(tim, freq=50, duty=0, pin=22)

'''
说明：舵机控制函数
功能：angle:-90至90 表示相应的角度
    【duty】占空比值：0-100
'''
def Servo(servo,angle):
    S1.duty((angle+90)/180*10+2.5)


# 设置模型输入图像的大小
input_size = (224, 224)
# 定义垃圾分类的标签
labels = ['可回收垃圾', '厨余垃圾', '其他垃圾', '有害垃圾']

# 定义函数，用于在LCD上显示异常信息
def lcd_show_except(e):
    import uio
    err_str = uio.StringIO()
    sys.print_exception(e, err_str)
    err_str = err_str.getvalue()
    img = image.Image(size=input_size)
    img.draw_string(0, 10, err_str, scale=1, color=(0xff,0x00,0x00))
    lcd.display(img)

# 定义主函数，用于运行垃圾分类模型
def main(labels=None, model_addr="/sd/m.kmodel", sensor_window=input_size, lcd_rotation=0, sensor_hmirror=False, sensor_vflip=False):
    # 重置传感器
    sensor.reset()
    # 设置传感器像素格式为RGB565
    sensor.set_pixformat(sensor.RGB565)
    # 设置传感器帧大小为QVGA（320x240）
    sensor.set_framesize(sensor.QVGA)
    # 设置传感器窗口为输入图像大小
    sensor.set_windowing(sensor_window)
    # 设置水平镜像
    sensor.set_hmirror(sensor_hmirror)
    # 设置垂直镜像
    sensor.set_vflip(sensor_vflip)
    # 启动传感器
    sensor.run(1)

    # 初始化LCD显示屏
    lcd.init(type=1)
    # 设置LCD旋转角度
    lcd.rotation(lcd_rotation)
    # 清除LCD显示，背景为白色
    lcd.clear(lcd.WHITE)

    # 如果未提供标签，则尝试从文件中加载
    if not labels:
        with open('labels.txt','r') as f:
            exec(f.read())
    # 如果仍然没有标签，则显示错误并退出
    if not labels:
        print("no labels.txt")
        img = image.Image(size=(320, 240))
        img.draw_string(90, 110, "no labels.txt", color=(255, 0, 0), scale=2)
        lcd.display(img)
        return 1
    # 尝试显示启动图片
    try:
        img = image.Image("startup.jpg")
        lcd.display(img)
    except Exception:
        # 如果启动图片加载失败，则显示加载模型中的文本
        img = image.Image(size=(320, 240))
        img.draw_string(90, 110, "loading model...", color=(255, 255, 255), scale=2)
        lcd.display(img)

    # 加载模型并运行
    try:
        task = None
        task = kpu.load(model_addr)
        while(True):
            img = sensor.snapshot()
            t = time.ticks_ms()
            fmap = kpu.forward(task, img)
            t = time.ticks_ms() - t
            plist=fmap[:]
            pmax=max(plist)
            max_index=plist.index(pmax)
            result=labels[max_index].strip()
            # 显示判断为垃圾的概率
            img.draw_string(0,0, "%.2f" %(pmax), scale=2, color=(255, 0, 0))
            lcd.display(img)
            # 概率大于0.85时根据垃圾类型来转动舵机
            if pmax > 0.85 :
                # 在图像上显示分类结果和耗时
                img.draw_string(0,0, "%.2f : %s" %(pmax, labels[max_index].strip()), scale=2, color=(255, 0, 0))
                img.draw_string(0, 200, "t:%dms" %(t), scale=2, color=(255, 0, 0))
                # 先转动舵机打开垃圾桶，维持一会后复位关闭垃圾桶
                if result == labels[0]:
                    Servo(S1,-20)
                    time.sleep(1)
                    Servo(S1,20)
                elif result == labels[1]:
                    Servo(S1,-40)
                    time.sleep(1)
                    Servo(S1,40)
                elif result == labels[2]:
                    Servo(S1,-60)
                    time.sleep(1)
                    Servo(S1,60)
                elif result == labels[3]:
                    Servo(S1,-80)
                    time.sleep(1)
                    Servo(S1,80)

    except Exception as e:
        raise e
    finally:
        # 卸载模型
        if task is not None:
            kpu.deinit(task)

# 如果直接运行此脚本，则调用main函数
if __name__ == "__main__":
    try:
        # 调用main函数，使用指定的模型文件
        main(labels=labels, model_addr="/sd/model-17881.kmodel")
    except Exception as e:
        # 捕获异常并显示
        sys.print_exception(e)
        lcd_show_except(e)
    finally:
        # 回收内存
        gc.collect()



