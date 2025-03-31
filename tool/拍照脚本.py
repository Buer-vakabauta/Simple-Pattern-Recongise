import sensor, image, time, lcd
import utime
import uos
import sys
from maix import GPIO
from board import board_info
from fpioa_manager import fm

# 参数初始化
Classes_num = 10
bg = lcd.RED
text = lcd.WHITE
boot_press_flag = 1
start = time.ticks_ms()
end = time.ticks_ms()
ui_num = 0
image_save_path = "/sd/image/"
claass = 0
image_num = 0
image_data = image.Image()
shoot_flag = 0
continuous_shooting_flag = False  # 连续拍摄标志

def boot_key_irq(pin_num):
    global ui_num
    global boot_press_flag, start, end
    global claass
    global image_num
    global shoot_flag
    global continuous_shooting_flag

    if(boot_press_flag == 1):
        start = time.ticks_ms()
        boot_press_flag = 0
    elif(boot_press_flag == 0):
        end = time.ticks_ms()
        boot_press_flag = 1
        time_diff = time.ticks_diff(end, start)
        if(time_diff >120 and time_diff <500):
            # 短按，切换连续拍摄状态
            continuous_shooting_flag = not continuous_shooting_flag
            if continuous_shooting_flag:
                lcd.draw_string(10, 200, "Continuous shooting ON", text, bg)
            else:
                lcd.draw_string(10, 200, "Continuous shooting OFF", text, bg)
            utime.sleep_ms(500)

        elif(time_diff >=500 and time_diff <=2000):
            print("长按切换文件夹", time_diff)
            claass = claass + 1
            if(claass > Classes_num - 1):
                claass = 0
            lcd.draw_string(0, 224, "Folder: " + str(claass), text, bg)

        else:
            boot_press_flag = 1
            start = 0
            end = 0

# 初始化按键中断
fm.register(board_info.BOOT_KEY, fm.fpioa.GPIOHS0, force=True)
boot_key = GPIO(GPIO.GPIOHS0, GPIO.IN, GPIO.PULL_UP)
boot_key.irq(boot_key_irq, GPIO.IRQ_BOTH, GPIO.WAKEUP_NOT_SUPPORT, 7)

def draw_help_ui():
    lcd.draw_string(60, 10, "Data Collection Assistant", text, bg)
    lcd.draw_string(20, 30, "1.Short press BOOT: Start/Stop", text, bg)
    lcd.draw_string(10, 50, "continuous photo shooting.", text, bg)
    lcd.draw_string(10, 70, "2.Long press BOOT: Switch folder", text, bg)
    lcd.draw_string(10, 90, "Current folder shows at bottom.", text, bg)
    lcd.draw_string(10, 200, "--Press BOOT button to begin", text, bg)

def not_found_tf():
    lcd.clear(bg)
    lcd.draw_string(10, 90, "ERROR: ", text, bg)
    lcd.draw_string(20, 110, "No TF card found", text, bg)
    lcd.draw_string(20, 130, "The Reason:", text, bg)
    lcd.draw_string(20, 150, "1.No TF card inserted", text, bg)
    lcd.draw_string(20, 170, "2.TF card model is not supported", text, bg)
    lcd.draw_string(20, 190, "3.TF card format is not FAT", text, bg)

def init():
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)

    # ✅ 设置分辨率为 224x224（可以通过 set_windowing）
    sensor.set_framesize(sensor.QVGA)  # 先设置为QVGGA，再裁剪
    sensor.set_windowing((224, 224))  # 截取 224x224 区域

    sensor.skip_frames(time=2000)
    sensor.run(1)

    lcd.init(type=1, freq=15000000, color=bg)

    try:
        uos.mkdir("/sd/image")
        for i in range(Classes_num):
            uos.mkdir("/sd/image/" + str(i))
            print("/sd/image/" + str(i))
    except Exception as e:
        if str(e) == "[Errno 17] EEXIST":
            pass
        else:
            not_found_tf()
            sys.exit(0)

    draw_help_ui()
    lcd.draw_string(0, 224, "Folder: " + str(claass), text, bg)

def image_ui():
    global image_data
    lcd.draw_string(0, 224, "Folder: " + str(claass), text, bg)

def continuous_shooting():
    global image_num
    global image_data
    # 拍摄并保存图片
    lcd.draw_string(0, 224, "Folder: " + str(claass), text, bg)
    image_num += 1
    save_path = "/sd/image/" + str(claass) + "/" + str(utime.ticks_us()) + "_" + str(image_num) + ".jpg"
    image_data.save(save_path)
    print("Saved:", save_path)
    lcd.draw_string(160, 224, "Saved " + str(image_num), text, bg)

def main():
    init()
    global image_data
    while True:
        image_data = sensor.snapshot()
        lcd.display(image_data, oft=(0, 0))
        image_ui()
        if continuous_shooting_flag:
            continuous_shooting()
            utime.sleep_ms(1000)  # 每秒拍摄一张

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
        lcd.clear(bg)
        lcd.draw_string(10, 90, "ERROR: unknown mistake", text, bg)
        lcd.draw_string(20, 110, "Please contact sipeed for help.", text, bg)
