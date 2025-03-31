from board import board_info#获取开发板信息
from fpioa_manager import fm
from maix import GPIO,KPU
import time,sensor,image,lcd,gc,math
from machine import UART
#全局变量------------------------------------
threshold = [(59, 100, -17, 127, -9, 76)]#阈值设置,用于几何图形检测
#threshold = [(65, 85, -6, 15, -2, 127)]
od_img = image.Image(size=(224,224))#用于数字识别的图像
obj_name = ('2', '0', '3', '4', '5', '6', '7', '1', '8', '9')#数字标签
anchor = (1.2984, 1.6594, 1.3778, 1.8665, 1.683, 1.858, 1.7373, 1.6094, 2.0576, 1.7039)#anchor列表
img=None
current_test = 1#任务标志位
num=None
#------------------------------------------
#引脚配置------------------------------------
fm.register(1, fm.fpioa.UART1_TX)
fm.register(0, fm.fpioa.UART1_RX)
#------------------------------------------

#初始化-------------------------------------
# 构造UART对象
uart1 = UART(UART.UART1, 115200)
#屏幕初始化
lcd.init()
#摄像头
sensor.reset(dual_buff=True)        # 重置
sensor.set_pixformat(sensor.RGB565) # 色彩设置
sensor.set_framesize(sensor.QVGA)   # 分辨率设置
#sensor.set_auto_gain(False)           # 固定增益，避免亮度变化
#sensor.set_auto_whitebal(False)       # 固定白平衡
sensor.set_windowing((224, 224))    #
sensor.skip_frames(time = 2000)     #等待,避免bug
#中断初始化
fm.register(board_info.BOOT_KEY, fm.fpioa.GPIOHS0, force=True)
boot_key = GPIO(GPIO.GPIOHS0, GPIO.IN, GPIO.PULL_UP)
last_press_time=0
#kpu初始化
kpu=None
#kpu.load_kmodel("/sd/KPU/detect0-9/nums.kmodel")
#kpu.init_yolo2(anchor, anchor_num=10, img_w=224, img_h=224, net_w=224 , net_h=224 ,layer_w=7 ,layer_h=7, threshold=0.5, nms_value=0.2, classes=10)
#类定义-------------------------------------

class Shape:
    def __init__(self, shape_type: str=None, number: int = None, area: float = None):
        """
        :param shape_type: 形状类型 ("triangle", "square", "circle", "rectangle")
        :param number: 数字 (0-9 或 None)
        :param area: 图形面积
        """
        if shape_type not in {"Triangle", "Square", "Circle", "Rectangle","num"}:
            raise ValueError("Invalid shape type")

        self.shape_type = shape_type
        self.number = number
        self.area = area

    def __str__(self):
        if self.shape_type=='Triangle':
            self.area=self.area*1.53
        else:
            self.area=self.area*1.43
        return "{} {} {}".format(self.shape_type,self.number,self.area)

    def __repr__(self):
        return self.__str__()





#函数---------------------------------------
#数字识别:
#中断
def boot_key_irq(pin_num):
    global current_test, last_press_time
    if boot_key.value() == 0:  # 按下时记录时间
        last_press_time = time.ticks_ms()
    else:  # 释放时计算按下时长
        press_duration = time.ticks_ms() - last_press_time
        if press_duration > 500:  # 长按切换到 test3
            current_test = 3
        else:  # 短按在 test1 和 test2 之间切换
            current_test = 2 if current_test == 1 else 1
        lcd.draw_string(10, 200, "Switched to test{}".format(current_test), lcd.WHITE, lcd.RED)
        time.sleep_ms(300)
#kpu初始化
def kpu_init():
    global kpu
    kpu = KPU()
    kpu.load_kmodel("/sd/KPU/detect0-9/nums.kmodel")
    kpu.init_yolo2(anchor, anchor_num=10, img_w=224, img_h=224, net_w=224 , net_h=224 ,layer_w=7 ,layer_h=7, threshold=0.5, nms_value=0.2, classes=10)
#kpu取消
def kpu_del():
    kpu.deinit()
#识别数字
def get_num():
    try:
        global img
        global num
        img = sensor.snapshot()
        od_img.draw_image(img, 0, 0)
        od_img.pix_to_ai()
        kpu.run_with_output(od_img)
        dect = kpu.regionlayer_yolo2()

        if len(dect) > 0:
            for l in dect:
                # 画矩形框
                img.draw_rectangle(l[0], l[1], l[2], l[3], color=(0, 255, 0))
                # 显示识别结果
                num=obj_name[l[4]]
                img.draw_string(l[0], l[1], num, color=(0, 255, 0), scale=1.5)
                gc.collect()
                return dect#返回结果
    except Exception as e:
        # 打印错误信息到串口
        pass
        # 把错误信息显示到 LCD 屏幕（最多显示 2 行）
        #img.draw_string(10, 10, "ERROR!", color=(255, 0, 0), scale=2)
        #img.draw_string(10, 40, str(e), color=(255, 0, 0), scale=1)

        # 为避免错误影响其他流程，可以选择暂停或继续
        #time.sleep(1)  # 等待 1 秒（可选）
#距离计算
def distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
#图形识别:
def get_shape(masked_img):
    try:
        global num
        global img
        result=None
        # 查找符合条件的黑色块（就是矩形框）
        orgin_img=masked_img.copy()
        blobs = masked_img.find_blobs(threshold, area_threshold=5000)  # area_threshold 防止检测噪点
        del masked_img
        for blob in blobs:
            shape=None
            #去除边框(根据面积和位置判断边框)
            if(blob.cy()<=15 or blob.pixels()>10000 or blob.pixels()<100):
                continue
            #进一步识别
            ratio = blob.w() / blob.h()#定义长宽比
            area_rate=(blob.w()*blob.h())/blob.pixels()#定义面积比
            #面积比接近1时,只能是长方形或矩形,根据长宽比得到具体形状
            if 0.9<area_rate<1.2:
                if 0.9<ratio<1.1:
                    shape="Square"
                    img.draw_rectangle(blob.rect(), color=127)
                    img.draw_string(blob.x(),blob.y(),shape,color=(255,0,0),scale=1)
                    if not result:
                        result=''
                    img.draw_rectangle(blob.rect(), color=127)
                    img.draw_string(blob.x(),blob.y(),shape,color=(255,0,0),scale=1)
                    result+=str(Shape(shape,num,blob.pixels()))
                    continue
                elif ratio>1.1 or ratio<0.9:
                    shape="Rectangle"
                    img.draw_rectangle(blob.rect(), color=127)
                    img.draw_string(blob.x(),blob.y(),shape,color=(255,0,0),scale=1)
                    if not result:
                        result=''
                    img.draw_rectangle(blob.rect(), color=127)
                    img.draw_string(blob.x(),blob.y(),shape,color=(255,0,0),scale=1)
                    result+=str(Shape(shape,num,blob.pixels()))
                    continue

            #查找直线
            lines = orgin_img.find_lines(roi=(blob.x(),blob.y(),blob.w(),blob.h()),threshold=1000, theta_margin=25, rho_margin=25)
            #del orgin_img
            line_count=len(lines)
            line_theta=[0]#直线夹角集合初始化防止空数字报错
            for l in lines:
                #img.draw_line(l.line(),color=(0,0,255))#绘制找到的直线
                #print(l.x1(),l.y1(),l.x2(),l.y2())
                line_theta.append(min(abs(lines[0].theta() - l.theta()), 180 - abs(lines[0].theta() - l.theta())))#计算直线夹角(0~90)
            if line_count>=4 and max(line_theta)>80:
                points = []
                for line in lines[:4]:
                    points.append((line.x1(), line.y1()))
                    points.append((line.x2(), line.y2()))
                # 简单求下边长，理论上要做排序+拟合，这里简化了
                if len(points) >= 4:
                    dists = []
                    for i in range(0, len(points), 2):
                        d = distance(points[i], points[i+1])
                        dists.append(d)

                    # 计算边长均值
                    avg_len = sum(dists)/len(dists)

                    # 判断边长差异
                    max_len = max(dists)
                    min_len = min(dists)

                    ratio = max_len / min_len if min_len != 0 else 9999
                    # 判断正方形 or 矩形
                    if ratio < 1.2:
                        shape = "Square"
                    elif ratio>1.3:
                        shape = "Rectangle"
            elif line_count==3 and 10<=max(line_theta)<=80:
                shape="Triangle"
            elif line_count==0:
                shape="Circle"
            if shape:
                if not result:
                    result=''
                img.draw_rectangle(blob.rect(), color=127)
                img.draw_string(blob.x(),blob.y(),shape,color=(255,0,0),scale=1)
                result+=str(Shape(shape,num,blob.pixels()))
        if result:
            uart1.write(result)
        return result
        gc.collect()
    except Exception as e:
        img.draw_string(10, 40, str(e), color=(255, 0, 0), scale=1)
#数字蒙版
def mask_num_area(dect):
    global img
    masked_img=img.copy()
    if not dect:
        return img
    for l in dect:
        x = l[0]
        y = l[1]
        w = l[2]
        h = l[3]
        # 填充矩形区域为白色 (255, 255, 255)
        masked_img.draw_rectangle(x+10, y+15, w-15, h-30, color=(255, 255, 255), fill=True)
    return masked_img

def test1():
    img.draw_string(1,1,"test1")
    get_shape(img)
def test2():
    global num
    get_num()
    uart1.write(str(Shape('num',num,0)))
    img.draw_string(1,1,"test2")
    num=None
def test3():
    global img
    kpu_init()
    while not num:
        r_rect=get_num()
    kpu_del()
    gc.collect()
    while not get_shape(img):
        print(1)
        img=sensor.snapshot()

#主程序-------------------------------------
#kpu_init()
#get_shape(mask_num_area(get_num()))
boot_key.irq(boot_key_irq, GPIO.IRQ_BOTH, GPIO.WAKEUP_NOT_SUPPORT, 7)#初始化中断
while True:
    if current_test == 1:
        img=sensor.snapshot()
        test1()
    elif current_test == 3:
        test3()
        while current_test==3:
            pass
        num=None
    elif current_test == 2:
        kpu_init()
        while current_test==2:
            test2()
            lcd.display(img)
        kpu_del()
        gc.collect()
    lcd.display(img)
    time.sleep(0.1)
    gc.collect()
kpu_del()
