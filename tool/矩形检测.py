import sensor, image, time, lcd,math

sensor.reset()

#sensor.set_pixformat(sensor.GRAYSCALE)  # 灰度模式
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)
sensor.set_windowing((224, 224))
#sensor.set_auto_gain(False)     # 关闭自动增益
#sensor.set_auto_whitebal(False) # 关闭自动白平衡

lcd.init()

# 阈值设置 → 黑色区域
threshold = [(84, 51, -86, 100, -28, 127)]  #
def distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
while True:
    img = sensor.snapshot()
    # 查找符合条件的黑色块（就是矩形框）
    blobs = img.find_blobs(threshold, area_threshold=5000)  # area_threshold 防止检测噪点
    shape="unknow"
    for blob in blobs:
        #去除边框(根据面积和位置判断边框)
        if(blob.cy()<=15 or blob.pixels()>10000):
            continue
        #进一步识别
        ratio = blob.w() / blob.h()#定义长宽比
        area_rate=(blob.w()*blob.h())/blob.pixels()#定义面积比
        #面积比接近1时,只能是长方形或矩形,根据长宽比得到具体形状
        if 0.9<area_rate<1.2:
            if 0.9<ratio<1.1:
                shape="Square"
                img.draw_rectangle(blob.rect(), color=127)
                img.draw_string(1,1,shape,color=(255,0,0),scale=1)
                continue
            elif ratio>1.1 or ratio<0.9:
                shape="Rectangle"
                img.draw_rectangle(blob.rect(), color=127)
                img.draw_string(1,1,shape,color=(255,0,0),scale=1)
                continue
        #查找直线
        lines = img.find_lines(roi=(blob.x(),blob.y(),blob.w(),blob.h()),threshold=1000, theta_margin=25, rho_margin=25)
        line_count=len(lines)
        for l in lines:
            img.draw_line(l.line(),color=(0,0,255))
        if line_count>=4:
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
                else:
                    shape = "Rectangle"
        elif 2<=line_count<=3:
            shape="Triangle"
        elif line_count<=1:
            shape="Circle"
        img.draw_rectangle(blob.rect(), color=127)
        img.draw_string(1,1,shape,color=(255,0,0),scale=1)
    lcd.display(img)
