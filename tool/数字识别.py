import sensor, image, time, lcd
from maix import KPU
import gc
lcd.init()
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_windowing((224,224))
sensor.skip_frames(time = 1000)
clock = time.clock()
od_img = image.Image(size=(224,224))

obj_name = ('2', '0', '3', '4', '5', '6', '7', '1', '8', '9')
anchor = (1.2984, 1.6594, 1.3778, 1.8665, 1.683, 1.858, 1.7373, 1.6094, 2.0576, 1.7039)
kpu = KPU()
print("ready load model")
kpu.load_kmodel("/sd/KPU/detect0-9/nums.kmodel")
kpu.init_yolo2(anchor, anchor_num=10, img_w=224, img_h=224, net_w=224 , net_h=224 ,layer_w=7 ,layer_h=7, threshold=0.5, nms_value=0.2, classes=10)
i = 0
while True:
    i += 1
    print("cnt :", i)
    clock.tick()
    img = sensor.snapshot()
    a = od_img.draw_image(img, 0,0)
    od_img.pix_to_ai()
    kpu.run_with_output(od_img)
    dect = kpu.regionlayer_yolo2()
    fps = clock.fps()
    if len(dect) > 0:
        print("dect:",dect)
        for l in dect :
            a = img.draw_rectangle(l[0],l[1],l[2],l[3], color=(0, 255, 0))
            a = img.draw_string(l[0],l[1], obj_name[l[4]], color=(0, 255, 0), scale=1.5)
    a = img.draw_string(0, 0, "%2.1ffps" %(fps), color=(0, 60, 128), scale=1.0)
    lcd.display(img)
    gc.collect()
kpu.deinit()
